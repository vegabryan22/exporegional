from datetime import datetime

from app.extensions import db


class ProjectStatusHistory(db.Model):
    __tablename__ = "project_status_history"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    from_status = db.Column(db.String(40), nullable=True)
    to_status = db.Column(db.String(40), nullable=False, index=True)
    changed_by_id = db.Column(db.Integer, db.ForeignKey("judges.id", ondelete="SET NULL"), nullable=True, index=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    project = db.relationship("Project", back_populates="status_history")
    changed_by = db.relationship("Judge", foreign_keys=[changed_by_id])
