from controller.database import db
from datetime import datetime


# =========================
# COMMON USER TABLE
# =========================
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    full_name = db.Column(db.String(150), nullable=False)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(150))
    mobile = db.Column(db.String(15), nullable=False)

    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # patient / doctor / admin

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# =========================
# PATIENT PROFILE
# =========================
class PatientProfile(db.Model):
    __tablename__ = "patient_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))
    emergency_contact = db.Column(db.String(15))


# =========================
# DOCTOR PROFILE
# =========================
class DoctorProfile(db.Model):
    __tablename__ = "doctor_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    specialization = db.Column(db.String(100))
    available_time = db.Column(db.String(100))
    room_number = db.Column(db.String(50))
    avg_consult_time = db.Column(db.Integer, default=10)
    user = db.relationship("User", backref="doctor_profile", lazy=True)

class QueueEntry(db.Model):
    __tablename__ = "queue_entries"

    id = db.Column(db.Integer, primary_key=True)

    patient_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctor_profiles.id"))

    token_number = db.Column(db.Integer)
    status = db.Column(db.String(50), default="waiting")

    checkin_time = db.Column(db.DateTime, default=datetime.utcnow)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)

    doctor = db.relationship("DoctorProfile", backref="queue_entries", lazy=True)
    patient = db.relationship("User", backref="queue_entries", lazy=True)
