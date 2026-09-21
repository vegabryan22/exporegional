from datetime import datetime

from app.extensions import db


class AssignmentProcess(db.Model):
    __tablename__ = "assignment_processes"

    TYPE_DOCUMENTATION = "documentation"
    TYPE_EXPOSITION = "exposition"
    TYPE_ENGLISH = "english"
    VALID_TYPES = {TYPE_DOCUMENTATION, TYPE_EXPOSITION, TYPE_ENGLISH}

    STATUS_DRAFT = "draft"
    STATUS_APPROVED = "approved"
    STATUS_SENT = "sent"

    id = db.Column(db.Integer, primary_key=True)
    process_type = db.Column(db.String(20), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default=STATUS_DRAFT, index=True)
    deadline = db.Column(db.DateTime, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("judges.id"), nullable=True)
    approved_by_id = db.Column(db.Integer, db.ForeignKey("judges.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    approved_at = db.Column(db.DateTime, nullable=True)
    sent_at = db.Column(db.DateTime, nullable=True)

    items = db.relationship(
        "AssignmentProcessItem",
        back_populates="process",
        cascade="all, delete-orphan",
        order_by="AssignmentProcessItem.id",
    )

    @property
    def type_label(self):
        return {
            self.TYPE_DOCUMENTATION: "Documento escrito",
            self.TYPE_EXPOSITION: "Exposición",
            self.TYPE_ENGLISH: "Inglés",
        }.get(self.process_type, self.process_type)


class AssignmentProcessItem(db.Model):
    __tablename__ = "assignment_process_items"
    __table_args__ = (
        db.UniqueConstraint("process_id", "judge_id", "project_id", name="uq_assignment_process_item"),
    )

    id = db.Column(db.Integer, primary_key=True)
    process_id = db.Column(db.Integer, db.ForeignKey("assignment_processes.id", ondelete="CASCADE"), nullable=False)
    judge_id = db.Column(db.Integer, db.ForeignKey("judges.id"), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    notification_sent_at = db.Column(db.DateTime, nullable=True)
    notification_error = db.Column(db.Text, nullable=True)

    process = db.relationship("AssignmentProcess", back_populates="items")
    judge = db.relationship("Judge")
    project = db.relationship("Project")
