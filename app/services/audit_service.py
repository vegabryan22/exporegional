from flask import request
from flask_login import current_user

from app.extensions import db
from app.models.system_audit_log import SystemAuditLog


def _safe_request_value(getter):
    try:
        return getter()
    except RuntimeError:
        return None


def log_event(action: str, entity: str, entity_id=None, detail: str = ""):
    actor_name = "Sistema"
    actor_email = None
    actor_role = "system"

    if getattr(current_user, "is_authenticated", False):
        actor_name = current_user.full_name or "Usuario"
        actor_email = current_user.email
        actor_role = getattr(current_user, "effective_role", None) or ("admin" if getattr(current_user, "is_admin", False) else (getattr(current_user, "department", None) or "usuario"))

    ip_address = _safe_request_value(lambda: request.headers.get("X-Forwarded-For", request.remote_addr))
    user_agent = _safe_request_value(lambda: request.user_agent.string[:255] if request.user_agent else None)

    db.session.add(
        SystemAuditLog(
            actor_name=actor_name,
            actor_email=actor_email,
            actor_role=actor_role,
            action=(action or "").strip()[:120],
            entity=(entity or "").strip()[:80],
            entity_id=entity_id,
            detail=(detail or "").strip(),
            ip_address=ip_address,
            user_agent=user_agent,
        )
    )
