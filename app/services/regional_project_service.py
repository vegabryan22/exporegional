from datetime import datetime

from app.extensions import db
from app.models.judge import Judge
from app.models.project import Project
from app.models.project_status_history import ProjectStatusHistory


REGIONAL_TRANSITIONS = {
    Project.STATUS_DRAFT: {Project.STATUS_SUBMITTED},
    Project.STATUS_SUBMITTED: {Project.STATUS_RECEIVED},
    Project.STATUS_RECEIVED: {Project.STATUS_UNDER_REVIEW},
    Project.STATUS_UNDER_REVIEW: {Project.STATUS_APPROVED, Project.STATUS_RETURNED},
    Project.STATUS_RETURNED: {Project.STATUS_SUBMITTED},
    Project.STATUS_APPROVED: set(),
    Project.STATUS_EVALUATED: set(),
    Project.STATUS_REGIONAL_WINNER: set(),
}

SCHOOL_ALLOWED_TRANSITIONS = {
    (Project.STATUS_DRAFT, Project.STATUS_SUBMITTED),
    (Project.STATUS_RETURNED, Project.STATUS_SUBMITTED),
}


class RegionalTransitionError(ValueError):
    pass


def transition_project(project: Project, target_status: str, actor: Judge, notes: str = "") -> ProjectStatusHistory:
    source_status = project.regional_status or Project.STATUS_DRAFT
    target_status = (target_status or "").strip().lower()
    allowed_targets = REGIONAL_TRANSITIONS.get(source_status, set())
    if target_status not in allowed_targets:
        raise RegionalTransitionError(f"No se permite pasar de {source_status} a {target_status}.")

    is_school_coordinator = actor.effective_role == Judge.ROLE_SCHOOL_COORDINATOR
    if is_school_coordinator:
        if not actor.institution_id or actor.institution_id != project.institution_id:
            raise RegionalTransitionError("El proyecto no pertenece al colegio de la cuenta coordinadora.")
        if (source_status, target_status) not in SCHOOL_ALLOWED_TRANSITIONS:
            raise RegionalTransitionError("La coordinación del colegio no puede ejecutar esa transición.")
    elif not actor.has_admin_access:
        raise RegionalTransitionError("El usuario no tiene permisos regionales para cambiar el estado.")

    now = datetime.utcnow()
    project.regional_status = target_status
    if target_status == Project.STATUS_SUBMITTED:
        project.submitted_at = now
    elif target_status == Project.STATUS_RECEIVED:
        project.received_at = now
    elif target_status == Project.STATUS_APPROVED:
        project.approved_at = now
        project.approved_by_id = actor.id

    history = ProjectStatusHistory(
        project=project,
        from_status=source_status,
        to_status=target_status,
        changed_by_id=actor.id,
        notes=(notes or "").strip() or None,
    )
    db.session.add(history)
    return history
