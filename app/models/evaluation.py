from datetime import datetime

from app.extensions import db


class Evaluation(db.Model):
    __tablename__ = "evaluations"
    __table_args__ = (
        db.UniqueConstraint(
            "judge_id",
            "project_id",
            "evaluation_type",
            "project_member_id",
            name="uq_eval_type_per_judge_project_member",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    judge_id = db.Column(db.Integer, db.ForeignKey("judges.id", ondelete="SET NULL"), nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    project_member_id = db.Column(db.Integer, db.ForeignKey("project_members.id", ondelete="SET NULL"), nullable=True)
    evaluation_type = db.Column(db.String(60), nullable=False, index=True)
    criteria_1 = db.Column(db.Integer, nullable=True)
    criteria_2 = db.Column(db.Integer, nullable=True)
    criteria_3 = db.Column(db.Integer, nullable=True)
    criteria_4 = db.Column(db.Integer, nullable=True)
    comments = db.Column(db.Text, nullable=True)
    recommendations = db.Column(db.Text, nullable=True)
    max_score = db.Column(db.Integer, nullable=True)
    percentage = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    judge = db.relationship("Judge", back_populates="evaluations")
    project = db.relationship("Project", back_populates="evaluations")
    project_member = db.relationship("ProjectMember")
    scores = db.relationship("EvaluationScore", back_populates="evaluation", cascade="all, delete-orphan")

    @property
    def total_score(self) -> int:
        if self.scores:
            return sum(item.score for item in self.scores if item.score is not None)
        values = [self.criteria_1, self.criteria_2, self.criteria_3, self.criteria_4]
        return sum(value for value in values if value is not None)
