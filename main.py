from flask import Flask, render_template, request, redirect, url_for, session
from controller.config import Config
from controller.database import db
from controller.models import (
    User,
    PatientProfile,
    DoctorProfile,
    QueueEntry
)
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = "supersecretkey"

db.init_app(app)


# HOME PAGE
@app.route("/")
def home():
    return render_template("home.html")


# ===============================
# REGISTER (GET + POST)
# ===============================
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        full_name = request.form.get("full_name")
        username = request.form.get("username")
        email = request.form.get("email")
        mobile = request.form.get("mobile")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        role = request.form.get("role")

        if password != confirm_password:
            return "Passwords do not match"

        existing_user = User.query.filter(
            (User.username == username) |
            (User.mobile == mobile)
        ).first()

        if existing_user:
            return "Username or Mobile already exists"

        new_user = User(
            full_name=full_name,
            username=username,
            email=email,
            mobile=mobile,
            password=password,
            role=role
        )

        db.session.add(new_user)
        db.session.commit()

        if role == "patient":
            patient_profile = PatientProfile(
                user_id=new_user.id,
                age=request.form.get("age"),
                gender=request.form.get("gender"),
                emergency_contact=request.form.get("emergency_contact")
            )
            db.session.add(patient_profile)

        elif role == "doctor":
            doctor_profile = DoctorProfile(
                user_id=new_user.id,
                specialization=request.form.get("specialization"),
                available_time=request.form.get("available_time"),
                room_number=request.form.get("room_number"),
                avg_consult_time=10
            )
            db.session.add(doctor_profile)

        db.session.commit()

        return redirect(url_for("login"))

    return render_template("register.html")


# ===============================
# LOGIN
# ===============================
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        identifier = request.form.get("identifier")
        password = request.form.get("password")

        # Hardcoded Admin
        if identifier == "mediflow_admin" and password == "admin123":
            session["role"] = "admin"
            return redirect(url_for("admin_dashboard"))

        user = User.query.filter(
            (User.username == identifier) |
            (User.mobile == identifier)
        ).first()

        if user and user.password == password:

            session["role"] = user.role
            session["user_id"] = user.id

            if user.role == "patient":
                return redirect(url_for("patient_dashboard"))

            elif user.role == "doctor":
                return redirect(url_for("doctor_dashboard"))

        return "Invalid Credentials"

    return render_template("login.html")


# ===============================
# PATIENT DASHBOARD
# ===============================
# ===============================
# PATIENT DASHBOARD
# ===============================
@app.route("/patient_dashboard")
def patient_dashboard():

    if session.get("role") != "patient":
        return redirect(url_for("login"))

    user_id = session.get("user_id")
    user = User.query.get(user_id)
    profile = PatientProfile.query.filter_by(user_id=user_id).first()

    doctors = DoctorProfile.query.all()

    # Get currently serving tokens (for all doctors)
    serving_entries = QueueEntry.query.filter_by(status="serving").all()

    return render_template(
        "patient_dashboard.html",
        user=user,
        profile=profile,
        doctors=doctors,
        serving_entries=serving_entries
    )



# ===============================
# BOOK CONSULTATION
# ===============================
@app.route("/book_consultation/<int:doctor_id>")
def book_consultation(doctor_id):

    if session.get("role") != "patient":
        return redirect(url_for("login"))

    user_id = session.get("user_id")

    last_entry = QueueEntry.query.filter_by(
        doctor_id=doctor_id
    ).order_by(QueueEntry.token_number.desc()).first()

    next_token = 1 if not last_entry else last_entry.token_number + 1

    entry = QueueEntry(
        patient_id=user_id,
        doctor_id=doctor_id,
        token_number=next_token
    )

    db.session.add(entry)
    db.session.commit()

    return redirect(url_for("view_queue_status", entry_id=entry.id))


# ===============================
# VIEW QUEUE STATUS (Predictive Engine)
# ===============================
@app.route("/queue_status/<int:entry_id>")
def view_queue_status(entry_id):

    entry = QueueEntry.query.get_or_404(entry_id)

    patients_before = QueueEntry.query.filter(
        QueueEntry.doctor_id == entry.doctor_id,
        QueueEntry.token_number < entry.token_number,
        QueueEntry.status == "waiting"
    ).count()

    completed_entries = QueueEntry.query.filter(
        QueueEntry.doctor_id == entry.doctor_id,
        QueueEntry.status == "completed",
        QueueEntry.start_time != None,
        QueueEntry.end_time != None
    ).all()

    if completed_entries:
        total_time = 0
        for e in completed_entries:
            duration = (e.end_time - e.start_time).total_seconds() / 60
            total_time += duration
        dynamic_avg = total_time / len(completed_entries)
    else:
        dynamic_avg = 10

    estimated_wait = round(patients_before * dynamic_avg)

    return render_template(
        "queue_status.html",
        entry=entry,
        patients_before=patients_before,
        estimated_wait=estimated_wait,
        dynamic_avg=round(dynamic_avg, 2)
    )


# ===============================
# DOCTOR DASHBOARD
# ===============================
@app.route("/doctor_dashboard")
def doctor_dashboard():

    if session.get("role") != "doctor":
        return redirect(url_for("login"))

    user_id = session.get("user_id")

    if not user_id:
        return redirect(url_for("login"))

    user = User.query.get(user_id)

    # Get doctor profile
    profile = DoctorProfile.query.filter_by(user_id=user_id).first()

    if not profile:
        return "Doctor profile not found. Please re-register."

    # Fetch only active queue entries (waiting + serving)
    queue_entries = QueueEntry.query.filter(
        QueueEntry.doctor_id == profile.id,
        QueueEntry.status != "completed"
    ).order_by(QueueEntry.token_number.asc()).all()

    return render_template(
        "doctor_dashboard.html",
        user=user,
        profile=profile,
        queue_entries=queue_entries
    )



# ===============================
# START CONSULTATION
# ===============================
@app.route("/start_consultation/<int:entry_id>")
def start_consultation(entry_id):

    if session.get("role") != "doctor":
        return redirect(url_for("login"))

    entry = QueueEntry.query.get_or_404(entry_id)
    entry.status = "serving"
    entry.start_time = datetime.utcnow()

    db.session.commit()

    return redirect(url_for("doctor_dashboard"))


# ===============================
# END CONSULTATION
# ===============================
@app.route("/end_consultation/<int:entry_id>")
def end_consultation(entry_id):

    if session.get("role") != "doctor":
        return redirect(url_for("login"))

    entry = QueueEntry.query.get_or_404(entry_id)
    entry.status = "completed"
    entry.end_time = datetime.utcnow()

    db.session.commit()

    return redirect(url_for("doctor_dashboard"))


# ===============================
# ADMIN DASHBOARD
# ===============================
@app.route("/admin_dashboard")
def admin_dashboard():

    if session.get("role") != "admin":
        return redirect(url_for("login"))

    total_users = User.query.count()
    total_patients = PatientProfile.query.count()
    total_doctors = DoctorProfile.query.count()

    return render_template(
        "admin_dashboard.html",
        total_users=total_users,
        total_patients=total_patients,
        total_doctors=total_doctors
    )




# ===============================
# LOGOUT
# ===============================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ===============================
# INIT DATABASE
# ===============================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)
