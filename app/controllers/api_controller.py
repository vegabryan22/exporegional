import hashlib
import hmac
from datetime import datetime
from functools import wraps

from flask import g, jsonify, request

from app.controllers.school_controller import _save_project_file
from app.extensions import db
from app.models.category import Category
from app.models.institution_api_credential import InstitutionApiCredential
from app.models.project import Project
from app.models.project_import_event import ProjectImportEvent
from app.models.project_member import ProjectMember


def _json_error(code: str, message: str, status: int, field: str | None = None):
    payload = {"ok": False, "error": {"code": code, "message": message}}
    if field:
        payload["error"]["field"] = field
    return jsonify(payload), status


def api_credential_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        authorization = (request.headers.get("Authorization") or "").strip()
        if not authorization.startswith("Bearer "):
            return _json_error("missing_credentials", "Credencial API requerida.", 401)
        token = authorization[7:].strip()
        if not token:
            return _json_error("missing_credentials", "Credencial API requerida.", 401)
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        credential = InstitutionApiCredential.query.filter_by(token_hash=token_hash, is_active=True).first()
        if not credential or not hmac.compare_digest(credential.token_hash, token_hash):
            return _json_error("invalid_credentials", "Credencial API inválida.", 401)
        if credential.expires_at and credential.expires_at <= datetime.utcnow():
            return _json_error("expired_credentials", "La credencial API expiró.", 401)
        if not credential.institution or not credential.institution.is_active:
            return _json_error("institution_disabled", "El colegio no está habilitado.", 403)
        credential.last_used_at = datetime.utcnow()
        g.api_credential = credential
        g.api_institution = credential.institution
        return view_func(*args, **kwargs)

    return wrapped


def _record_event(result: str, http_status: int, external_id: str = "", project=None, detail: str = ""):
    event = ProjectImportEvent(
        institution_id=g.api_institution.id,
        project_id=project.id if project else None,
        request_id=(request.headers.get("Idempotency-Key") or "").strip()[:120] or None,
        external_project_id=(external_id or "")[:120] or None,
        result=result,
        http_status=http_status,
        detail=(detail or "")[:2000] or None,
    )
    db.session.add(event)


@api_credential_required
def upsert_regional_project():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        _record_event("rejected", 400, detail="El cuerpo no es JSON.")
        db.session.commit()
        return _json_error("invalid_json", "El cuerpo debe ser un objeto JSON.", 400)

    external_id = str(payload.get("external_project_id") or "").strip()
    required = {
        "external_project_id": external_id,
        "title": str(payload.get("title") or "").strip(),
        "team_name": str(payload.get("team_name") or "").strip(),
        "category_code": str(payload.get("category_code") or "").strip().lower(),
        "description": str(payload.get("description") or "").strip(),
    }
    missing = next((field for field, value in required.items() if not value), None)
    if missing:
        _record_event("rejected", 422, external_id, detail=f"Campo requerido ausente: {missing}")
        db.session.commit()
        return _json_error("missing_field", "Falta un campo obligatorio.", 422, missing)

    category = Category.query.filter_by(code=required["category_code"], is_active=True).first()
    if not category:
        _record_event("rejected", 422, external_id, detail="Categoría regional inválida.")
        db.session.commit()
        return _json_error("invalid_category", "La categoría regional indicada no existe.", 422, "category_code")

    students = payload.get("students")
    if not isinstance(students, list) or not students or len(students) > 3:
        _record_event("rejected", 422, external_id, detail="La lista de estudiantes debe contener entre 1 y 3 elementos.")
        db.session.commit()
        return _json_error("invalid_students", "Debes enviar entre uno y tres estudiantes.", 422, "students")
    if any(not isinstance(row, dict) or not str(row.get("name") or "").strip() for row in students):
        _record_event("rejected", 422, external_id, detail="Estudiante sin nombre.")
        db.session.commit()
        return _json_error("invalid_students", "Cada estudiante debe tener nombre.", 422, "students")

    project = Project.query.filter_by(institution_id=g.api_institution.id, external_project_id=external_id).first()
    created = project is None
    if project and project.regional_status not in {Project.STATUS_RECEIVED, Project.STATUS_RETURNED}:
        _record_event("conflict", 409, external_id, project, "El proyecto ya avanzó en el flujo regional.")
        db.session.commit()
        return _json_error("project_locked", "El proyecto ya avanzó en el flujo regional y no admite reemplazo.", 409)

    tutor = payload.get("tutor") if isinstance(payload.get("tutor"), dict) else {}
    if created:
        project = Project(
            institution_id=g.api_institution.id,
            external_project_id=external_id,
            origin=Project.ORIGIN_INSTITUTIONAL_API,
            regional_status=Project.STATUS_RECEIVED,
            institution_name=g.api_institution.name,
            title=required["title"],
            team_name=required["team_name"],
            representative_name=str(students[0].get("name") or "").strip(),
            representative_email=str(students[0].get("email") or g.api_institution.responsible_email).strip().lower(),
            category=category.code,
            category_id=category.id,
            description=required["description"],
            received_at=datetime.utcnow(),
        )
        db.session.add(project)
        db.session.flush()
    else:
        project.members.clear()

    project.title = required["title"]
    project.team_name = required["team_name"]
    project.description = required["description"]
    project.category = category.code
    project.category_id = category.id
    project.representative_name = str(students[0].get("name") or "").strip()
    project.representative_email = str(students[0].get("email") or g.api_institution.responsible_email).strip().lower()
    project.advisor_name = str(tutor.get("name") or g.api_institution.responsible_name).strip()
    project.advisor_email = str(tutor.get("email") or g.api_institution.responsible_email).strip().lower()
    project.advisor_phone = str(tutor.get("phone") or "").strip() or None
    project.external_source = str(payload.get("external_source") or g.api_institution.code).strip()[:160]
    project.payload_version = str(payload.get("payload_version") or "1.0").strip()[:20]
    project.source_updated_at = datetime.utcnow()
    project.regional_status = Project.STATUS_RECEIVED

    for index, student in enumerate(students, start=1):
        project.members.append(
            ProjectMember(
                student_number=index,
                full_name=str(student.get("name") or "").strip(),
                identity_number=str(student.get("identity_number") or "").strip() or None,
                email=str(student.get("email") or "").strip().lower() or None,
                phone=str(student.get("phone") or "").strip() or None,
                section_name=str(student.get("section") or "").strip() or None,
                specialty=str(student.get("specialty") or "").strip() or None,
            )
        )

    result = "created" if created else "updated"
    status = 201 if created else 200
    _record_event(result, status, external_id, project, "Proyecto institucional recibido.")
    db.session.commit()
    return jsonify({"ok": True, "result": result, "regional_project_id": project.id, "external_project_id": external_id, "regional_status": project.regional_status}), status


@api_credential_required
def upload_regional_project_files(external_project_id: str):
    project = Project.query.filter_by(institution_id=g.api_institution.id, external_project_id=external_project_id).first()
    if not project:
        return _json_error("project_not_found", "Proyecto regional no encontrado.", 404)
    if project.regional_status not in {Project.STATUS_RECEIVED, Project.STATUS_RETURNED}:
        return _json_error("project_locked", "El proyecto ya no admite archivos.", 409)
    try:
        document_path = _save_project_file(project, request.files.get("project_document"), "document")
        logo_path = _save_project_file(project, request.files.get("project_logo"), "logo")
        received_photos = 0
        for member in project.members:
            photo_path = _save_project_file(project, request.files.get(f"member_photo_{member.student_number}"), "member_photo")
            if photo_path:
                member.photo_url = photo_path
                received_photos += 1
    except ValueError as error:
        return _json_error("invalid_file", str(error), 422)
    if not document_path and not logo_path and not received_photos:
        return _json_error("missing_files", "Debes adjuntar al menos un archivo.", 422)
    if document_path:
        project.project_document_path = document_path
    if logo_path:
        project.project_logo_path = logo_path
    _record_event("files_updated", 200, external_project_id, project, "Archivos institucionales recibidos.")
    db.session.commit()
    return jsonify({"ok": True, "result": "files_updated", "regional_project_id": project.id, "document_received": bool(document_path), "logo_received": bool(logo_path), "member_photos_received": received_photos})


@api_credential_required
def get_regional_project_status(external_project_id: str):
    project = Project.query.filter_by(institution_id=g.api_institution.id, external_project_id=external_project_id).first()
    if not project:
        return _json_error("project_not_found", "Proyecto regional no encontrado.", 404)
    db.session.commit()
    return jsonify({"ok": True, "regional_project_id": project.id, "external_project_id": external_project_id, "regional_status": project.regional_status, "regional_status_label": project.regional_status_label, "regional_notes": project.regional_notes})
