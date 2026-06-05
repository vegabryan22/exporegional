from datetime import datetime

from app.extensions import db


class Project(db.Model):
    __tablename__ = "projects"
    GENERIC_LOGO_PATH = "placeholders/project-logo-generic.svg"

    id = db.Column(db.Integer, primary_key=True)
    registration_date = db.Column(db.Date, nullable=True)
    title = db.Column(db.String(180), nullable=False)
    team_name = db.Column(db.String(180), nullable=False)
    representative_name = db.Column(db.String(120), nullable=False)
    representative_email = db.Column(db.String(120), nullable=False)
    representative_phone = db.Column(db.String(40), nullable=True)
    institution_name = db.Column(db.String(180), nullable=True)
    grade_level = db.Column(db.String(60), nullable=True)
    specialty = db.Column(db.String(120), nullable=True)
    section_id = db.Column(db.Integer, db.ForeignKey("sections.id"), nullable=True, index=True)
    specialty_id = db.Column(db.Integer, db.ForeignKey("specialties.id"), nullable=True, index=True)
    workshop_id = db.Column(db.Integer, db.ForeignKey("workshops.id"), nullable=True, index=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("campaigns.id"), nullable=True, index=True)
    advisor_name = db.Column(db.String(120), nullable=True)
    advisor_identity = db.Column(db.String(40), nullable=True)
    advisor_birth_date = db.Column(db.Date, nullable=True)
    advisor_gender = db.Column(db.String(20), nullable=True)
    advisor_email = db.Column(db.String(120), nullable=True)
    advisor_phone = db.Column(db.String(40), nullable=True)
    mentor_name = db.Column(db.String(120), nullable=True)
    mentor_identity = db.Column(db.String(40), nullable=True)
    mentor_birth_date = db.Column(db.Date, nullable=True)
    mentor_gender = db.Column(db.String(20), nullable=True)
    mentor_specialty = db.Column(db.String(140), nullable=True)
    mentor_email = db.Column(db.String(120), nullable=True)
    mentor_phone = db.Column(db.String(40), nullable=True)
    category = db.Column(db.String(60), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    project_objective = db.Column(db.Text, nullable=True)
    expected_impact = db.Column(db.Text, nullable=True)
    required_resources = db.Column(db.Text, nullable=True)
    requirements_summary = db.Column(db.Text, nullable=True)
    requirements_other = db.Column(db.String(255), nullable=True)
    project_document_path = db.Column(db.String(300), nullable=True)
    project_logo_path = db.Column(db.String(300), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    logistics_status = db.Column(db.String(40), nullable=False, default="pendiente_revision", index=True)
    logistics_notes = db.Column(db.Text, nullable=True)
    logistics_document_ok = db.Column(db.Boolean, nullable=False, default=False)
    logistics_logo_ok = db.Column(db.Boolean, nullable=False, default=False)
    logistics_photos_ok = db.Column(db.Boolean, nullable=False, default=False)
    logistics_registration_form_signed_ok = db.Column(db.Boolean, nullable=False, default=False)
    logistics_student_consents_signed_ok = db.Column(db.Boolean, nullable=False, default=False)
    logistics_requirements_reviewed_ok = db.Column(db.Boolean, nullable=False, default=False)
    consent_terms = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    assignments = db.relationship("Assignment", back_populates="project", cascade="all, delete-orphan")
    evaluations = db.relationship("Evaluation", back_populates="project")
    members = db.relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    member_changes = db.relationship("ProjectMemberChange", back_populates="project", cascade="all, delete-orphan")
    section = db.relationship("Section")
    specialty_ref = db.relationship("Specialty")
    workshop_ref = db.relationship("Workshop")
    campaign = db.relationship("Campaign", back_populates="projects")

    @property
    def has_real_logo(self) -> bool:
        return bool(self.project_logo_path) and self.project_logo_path != self.GENERIC_LOGO_PATH

    @property
    def display_logo_path(self) -> str:
        return self.project_logo_path if self.has_real_logo else self.GENERIC_LOGO_PATH

    @property
    def logistics_requirements_complete(self) -> bool:
        return all(
            [
                bool(self.project_document_path),
                self.logistics_document_ok,
                self.has_real_logo,
                self.logistics_logo_ok,
                self.logistics_photos_ok,
                self.logistics_registration_form_signed_ok,
                self.logistics_student_consents_signed_ok,
                self.logistics_requirements_reviewed_ok,
            ]
        )
