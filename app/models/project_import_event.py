from datetime import datetime

from app.extensions import db


class ProjectImportEvent(db.Model):
    __tablename__ = "project_import_events"

    id = db.Column(db.Integer, primary_key=True)
    institution_id = db.Column(db.Integer, db.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    request_id = db.Column(db.String(120), nullable=True, index=True)
    external_project_id = db.Column(db.String(120), nullable=True, index=True)
    result = db.Column(db.String(30), nullable=False, index=True)
    http_status = db.Column(db.Integer, nullable=False)
    detail = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    institution = db.relationship("Institution")
    project = db.relationship("Project")
