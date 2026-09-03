from datetime import datetime

from app.extensions import db


class ProjectMemberEditRequest(db.Model):
    __tablename__ = "project_member_edit_requests"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    member_id = db.Column(db.Integer, db.ForeignKey("project_members.id", ondelete="SET NULL"), nullable=True, index=True)
    submitted_by_name = db.Column(db.String(120), nullable=False)
    justification = db.Column(db.Text, nullable=True)
    # JSON dict of {field: new_value} for all editable fields
    changes_json = db.Column(db.Text, nullable=False)
    # JSON snapshot of member values at submission time for diff display
    snapshot_json = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pendiente")
    admin_notes = db.Column(db.Text, nullable=True)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey("judges.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    STATUS_PENDING = "pendiente"
    STATUS_APPROVED = "aprobado"
    STATUS_REJECTED = "rechazado"

    project = db.relationship("Project", back_populates="member_edit_requests")
    member = db.relationship("ProjectMember", back_populates="edit_requests")
    reviewed_by = db.relationship("Judge")

    EDITABLE_FIELDS = [
        ("full_name",                "Nombre completo"),
        ("identity_number",          "Número de cédula"),
        ("birth_date",               "Fecha de nacimiento"),
        ("gender",                   "Género"),
        ("specialty",                "Especialidad"),
        ("section_name",             "Sección"),
        ("participates_in_english",  "Expone en inglés"),
        ("phone",                    "Teléfono"),
        ("email",                    "Correo electrónico"),
        ("role",                     "Rol en el proyecto"),
    ]
