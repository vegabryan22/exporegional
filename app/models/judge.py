from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, login_manager


class Judge(UserMixin, db.Model):
    __tablename__ = "judges"

    ROLE_JUDGE = "judge"
    ROLE_ADMIN = "admin"
    ROLE_SUPERADMIN = "superadmin"
    ROLE_SCHOOL_COORDINATOR = "school_coordinator"
    ROLE_CERTIFICATE_OPERATOR = "certificate_operator"
    ADMIN_ROLES = {ROLE_ADMIN, ROLE_SUPERADMIN}
    VALID_ROLES = {ROLE_JUDGE, ROLE_ADMIN, ROLE_SUPERADMIN, ROLE_SCHOOL_COORDINATOR, ROLE_CERTIFICATE_OPERATOR}

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False, default=ROLE_JUDGE)
    department = db.Column(db.String(40), nullable=True, index=True)
    job_title = db.Column(db.String(120), nullable=True)
    identity = db.Column(db.String(40), nullable=True)
    institution = db.Column(db.String(160), nullable=True)
    institution_id = db.Column(db.Integer, db.ForeignKey("institutions.id", ondelete="SET NULL"), nullable=True, index=True)
    previous_expo = db.Column(db.String(10), nullable=True)
    phone = db.Column(db.String(40), nullable=True)
    can_evaluate_documentation = db.Column(db.Boolean, default=True, nullable=False)
    can_evaluate_exposition = db.Column(db.Boolean, default=True, nullable=False)
    can_evaluate_english = db.Column(db.Boolean, default=False, nullable=False)
    category_scope = db.Column(db.String(40), default="ambas", nullable=False)
    registration_notes = db.Column(db.Text, nullable=True)
    registered_from_public_form = db.Column(db.Boolean, default=False, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active_user = db.Column(db.Boolean, default=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    must_change_password = db.Column(db.Boolean, default=False, nullable=False)
    last_login_at = db.Column(db.DateTime, nullable=True)

    attendance_token = db.Column(db.String(64), unique=True, nullable=True)
    attendance_confirmed = db.Column(db.Boolean, nullable=True)
    needs_parking = db.Column(db.Boolean, default=False, nullable=False)
    attendance_responded_at = db.Column(db.DateTime, nullable=True)
    attendance_invitation_sent_at = db.Column(db.DateTime, nullable=True)
    attendance_invitation_error = db.Column(db.Text, nullable=True)

    ATTENDANCE_PENDING = None
    ATTENDANCE_YES = True
    ATTENDANCE_NO = False

    @property
    def attendance_status_label(self):
        if self.attendance_confirmed is True:
            return "Confirmado"
        if self.attendance_confirmed is False:
            return "No asiste"
        return "Pendiente"

    @property
    def attendance_status_tag(self):
        if self.attendance_confirmed is True:
            return "ok"
        if self.attendance_confirmed is False:
            return "off"
        return "neutral"

    @property
    def has_invitation_error(self) -> bool:
        """Retorna True si el último envío de invitación tuvo error."""
        return bool(self.attendance_invitation_error)

    @property
    def invitation_error_short(self) -> str:
        """Retorna un resumen del error de invitación para mostrar en UI."""
        if not self.attendance_invitation_error:
            return ""
        # Limita el error a los primeros 200 caracteres
        error = self.attendance_invitation_error
        return error[:200] + "..." if len(error) > 200 else error

    assignments = db.relationship("Assignment", back_populates="judge", cascade="all, delete-orphan")
    evaluations = db.relationship("Evaluation", back_populates="judge")
    institution_ref = db.relationship("Institution", back_populates="users")

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
            self.ROLE_SCHOOL_COORDINATOR: "Coordinador de colegio",
            self.ROLE_CERTIFICATE_OPERATOR: "Encargado de certificados",
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

    @property
    def evaluation_scope_label(self) -> str:
        if self.can_evaluate_documentation and self.can_evaluate_exposition:
            return "Documento y exposición"
        if self.can_evaluate_documentation:
            return "Solo documento"
        if self.can_evaluate_exposition:
            return "Solo exposición"
        return "Sin disponibilidad"

    @property
    def category_scope_normalized(self) -> str:
        value = (self.category_scope or "ambas").strip().lower()
        if value in {"steam", "emprendimiento", "ambas"}:
            return value
        return "ambas"

    @property
    def category_scope_label(self) -> str:
        labels = {
            "steam": "STEAM",
            "emprendimiento": "Emprendimiento",
            "ambas": "Ambas categorías",
        }
        return labels.get(self.category_scope_normalized, "Ambas categorías")

    @property
    def english_scope_label(self) -> str:
        return "Evalúa inglés" if self.can_evaluate_english else "No evalúa inglés"

    def can_evaluate_category(self, category: str) -> bool:
        normalized = (category or "").strip().lower()
        scope = self.category_scope_normalized
        if scope == "ambas":
            return True
        if scope == "steam":
            return normalized == "steam"
        if scope == "emprendimiento":
            return normalized.startswith("emprend")
        return True

    def mark_login(self) -> None:
        self.last_login_at = datetime.utcnow()


@login_manager.user_loader
def load_user(user_id: str):
    return Judge.query.get(int(user_id))
