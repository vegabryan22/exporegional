from datetime import datetime

from app.extensions import db


class ProjectDocumentRevision(db.Model):
    __tablename__ = "project_document_revisions"

    STATUS_PENDING = "pendiente"
    STATUS_APPROVED = "aprobado"
    STATUS_REJECTED = "rechazado"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    document_path = db.Column(db.String(300), nullable=False)
    justification = db.Column(db.Text, nullable=False)
    submitted_by_name = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pendiente", index=True)
    admin_notes = db.Column(db.Text, nullable=True)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey("judges.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    replaced_document_path = db.Column(db.String(300), nullable=True)
    notification_sent = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    project = db.relationship("Project", back_populates="document_revisions")
    reviewed_by = db.relationship("Judge")
