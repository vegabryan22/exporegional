from datetime import datetime

from app.extensions import db


class Institution(db.Model):
    __tablename__ = "institutions"

    STATUS_INVITED = "invited"
    STATUS_REGISTERED = "registered"
    STATUS_ENABLED = "enabled"
    STATUS_SUSPENDED = "suspended"
    STATUS_CLOSED = "closed"
    VALID_STATUSES = {
        STATUS_INVITED,
        STATUS_REGISTERED,
        STATUS_ENABLED,
        STATUS_SUSPENDED,
        STATUS_CLOSED,
    }

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), unique=True, nullable=False, index=True)
    name = db.Column(db.String(180), nullable=False, index=True)
    circuit = db.Column(db.String(80), nullable=True, index=True)
    regional_directorate = db.Column(db.String(160), nullable=True, index=True)
    address = db.Column(db.String(300), nullable=True)
    responsible_name = db.Column(db.String(160), nullable=False)
    responsible_email = db.Column(db.String(160), nullable=False, index=True)
    responsible_phone = db.Column(db.String(40), nullable=True)
    shield_path = db.Column(db.String(300), nullable=True)
    uses_institutional_platform = db.Column(db.Boolean, nullable=False, default=False)
    participation_status = db.Column(db.String(30), nullable=False, default=STATUS_INVITED, index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    projects = db.relationship("Project", back_populates="institution")
    users = db.relationship("Judge", back_populates="institution_ref")
    api_credentials = db.relationship("InstitutionApiCredential", back_populates="institution", cascade="all, delete-orphan")

    @property
    def project_count(self) -> int:
        return len(self.projects)

    @property
    def participation_status_label(self) -> str:
        return {
            self.STATUS_INVITED: "Invitado",
            self.STATUS_REGISTERED: "Registrado",
            self.STATUS_ENABLED: "Habilitado",
            self.STATUS_SUSPENDED: "Suspendido",
            self.STATUS_CLOSED: "Participación cerrada",
        }.get(self.participation_status, self.participation_status)
