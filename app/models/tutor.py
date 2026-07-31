from datetime import datetime

from app.extensions import db


class Tutor(db.Model):
    __tablename__ = "tutors"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    identity_number = db.Column(db.String(40), nullable=False, unique=True, index=True)
    birth_date = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(20), nullable=True)
    specialty = db.Column(db.String(140), nullable=True)
    email = db.Column(db.String(120), nullable=True, index=True)
    phone = db.Column(db.String(40), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    projects = db.relationship("Project", back_populates="tutor")

