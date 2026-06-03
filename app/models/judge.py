from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, login_manager


class Judge(UserMixin, db.Model):
    __tablename__ = "judges"

    ROLE_JUDGE = "judge"
    ROLE_ADMIN = "admin"
    ROLE_SUPERADMIN = "superadmin"
    ADMIN_ROLES = {ROLE_ADMIN, ROLE_SUPERADMIN}
    VALID_ROLES = {ROLE_JUDGE, ROLE_ADMIN, ROLE_SUPERADMIN}

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False, default=ROLE_JUDGE)
    department = db.Column(db.String(40), nullable=True, index=True)
    job_title = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(40), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active_user = db.Column(db.Boolean, default=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    must_change_password = db.Column(db.Boolean, default=False, nullable=False)
    last_login_at = db.Column(db.DateTime, nullable=True)

    assignments = db.relationship("Assignment", back_populates="judge", cascade="all, delete-orphan")
    evaluations = db.relationship("Evaluation", back_populates="judge")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self) -> bool:
        return self.is_active_user

    @property
    def effective_role(self) -> str:
        normalized = (self.role or "").strip().lower()
        if normalized in self.VALID_ROLES:
            return normalized
        return self.ROLE_ADMIN if self.is_admin else self.ROLE_JUDGE

    @property
    def has_admin_access(self) -> bool:
        return self.effective_role in self.ADMIN_ROLES or bool(self.is_admin)

    @property
    def is_superadmin(self) -> bool:
        return self.effective_role == self.ROLE_SUPERADMIN

    @property
    def role_label(self) -> str:
        labels = {
            self.ROLE_JUDGE: "Juez",
            self.ROLE_ADMIN: "Administrador",
            self.ROLE_SUPERADMIN: "Superadministrador",
        }
        return labels.get(self.effective_role, "Juez")

    @property
    def department_label(self) -> str:
        labels = {
            "logistica": "Logistica",
            "datos": "Datos",
            "diseno": "Diseno",
            "qa": "QA",
        }
        return labels.get((self.department or "").strip().lower(), "Sin departamento")

    def mark_login(self) -> None:
        self.last_login_at = datetime.utcnow()


@login_manager.user_loader
def load_user(user_id: str):
    return Judge.query.get(int(user_id))
