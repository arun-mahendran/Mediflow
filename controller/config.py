import os

class Config:
    SECRET_KEY = "supersecretkey123"

    # SQLite inside instance folder
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = "sqlite:///mediflow.db"

    SQLALCHEMY_TRACK_MODIFICATIONS = False
