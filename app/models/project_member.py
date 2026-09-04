from datetime import datetime

from app.extensions import db


class ProjectMember(db.Model):
    __tablename__ = "project_members"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True)
    student_number = db.Column(db.Integer, nullable=False, default=1)
    full_name = db.Column(db.String(120), nullable=False)
    identity_number = db.Column(db.String(40), nullable=True)
    birth_date = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(20), nullable=True)
    level_id = db.Column(db.Integer, db.ForeignKey("levels.id", ondelete="RESTRICT"), nullable=True, index=True)
    specialty_id = db.Column(db.Integer, db.ForeignKey("specialties.id"), nullable=True, index=True)
    specialty = db.Column(db.String(140), nullable=True)
    section_name = db.Column(db.String(30), nullable=True)
    has_dining_scholarship = db.Column(db.Boolean, default=False, nullable=False)
    participates_in_english = db.Column(db.Boolean, default=False, nullable=False)
    consent_signed_ok = db.Column(db.Boolean, default=False, nullable=False)
    cedula_copies_ok = db.Column(db.Boolean, default=False, nullable=False)
    cedula_encargado_ok = db.Column(db.Boolean, default=False, nullable=False)
    cedula_estudiante_ok = db.Column(db.Boolean, default=False, nullable=False)
    certificate_name_verified = db.Column(db.Boolean, default=False, nullable=False)
    phone = db.Column(db.String(40), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    role = db.Column(db.String(120), nullable=True)
    photo_url = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    project = db.relationship("Project", back_populates="members")
    level = db.relationship("Level")
    specialty_ref = db.relationship("Specialty")
    changes = db.relationship("ProjectMemberChange", back_populates="member", passive_deletes=True)
    edit_requests = db.relationship("ProjectMemberEditRequest", back_populates="member", passive_deletes=True)

    @property
    def academic_level_label(self):
        if self.level:
            return self.level.code
        return self.section_name or ""
