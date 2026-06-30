from app.extensions import db


class Assignment(db.Model):
    __tablename__ = "assignments"
    __table_args__ = (
        db.UniqueConstraint("judge_id", "project_id", name="uq_assignment_judge_project"),
    )

    STATUS_DRAFT = "draft"
    STATUS_CONFIRMED = "confirmed"

    id = db.Column(db.Integer, primary_key=True)
    judge_id = db.Column(db.Integer, db.ForeignKey("judges.id"), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    can_evaluate_documentation = db.Column(db.Boolean, nullable=False, default=True)
    can_evaluate_exposition = db.Column(db.Boolean, nullable=False, default=True)
    status = db.Column(db.String(20), nullable=False, default=STATUS_CONFIRMED, index=True)

    judge = db.relationship("Judge", back_populates="assignments")
    project = db.relationship("Project", back_populates="assignments")

    @property
    def is_draft(self) -> bool:
        return self.status == self.STATUS_DRAFT

    @property
    def scope_label(self):
        if self.can_evaluate_documentation and self.can_evaluate_exposition:
            return "Documento y exposición"
        if self.can_evaluate_documentation:
            return "Solo documento"
        if self.can_evaluate_exposition:
            return "Solo exposición"
        return "Sin alcance"

