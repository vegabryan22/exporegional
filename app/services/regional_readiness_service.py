from app.models.project import Project


def approval_missing_requirements(project: Project) -> list[str]:
    """Return every mandatory item that prevents regional evaluation approval."""
    missing = []
    members = list(project.members or [])

    if not (project.title or "").strip():
        missing.append("título del proyecto")
    if not (project.team_name or "").strip():
        missing.append("nombre del equipo")
    if not project.category_id:
        missing.append("categoría regional")
    if not (project.advisor_name or "").strip():
        missing.append("nombre del tutor")
    if not members:
        missing.append("al menos una persona estudiante")
    if not project.project_document_path:
        missing.append("documento escrito del proyecto")
    if (project.category or "").strip().lower() == "steam" and not project.project_logbook_path:
        missing.append("bitácora del proyecto STEAM")
    if not project.has_real_logo:
        missing.append("logo del proyecto")

    members_without_photo = [member.full_name for member in members if not (member.photo_url or "").strip()]
    if members_without_photo:
        missing.append("fotografía de: " + ", ".join(members_without_photo))
    if not project.logistics_registration_form_signed_ok:
        missing.append("formulario de inscripción firmado")

    members_without_consent = [member.full_name for member in members if not member.consent_signed_ok]
    if members_without_consent:
        missing.append("consentimiento firmado de: " + ", ".join(members_without_consent))

    return missing


def is_ready_for_evaluation(project: Project) -> bool:
    return not approval_missing_requirements(project)
