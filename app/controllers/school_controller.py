import json
import os
import uuid
from functools import wraps

from flask import current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, logout_user
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models.category import Category
from app.models.judge import Judge
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.project_status_history import ProjectStatusHistory
from app.services.audit_service import log_event
from app.services.regional_project_service import RegionalTransitionError, transition_project


def school_coordinator_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapped(*args, **kwargs):
        if current_user.effective_role != Judge.ROLE_SCHOOL_COORDINATOR or not current_user.institution_id:
            flash("Acceso exclusivo para coordinaciones de colegios participantes.", "error")
            return redirect(url_for("auth.login"))
        if not current_user.institution_ref or not current_user.institution_ref.is_active:
            flash("El colegio asociado no está habilitado.", "error")
            logout_user()
            return redirect(url_for("auth.login"))
        return view_func(*args, **kwargs)

    return wrapped


def _owned_project(project_id: int) -> Project:
    project = db.session.get(Project, project_id)
    if not project or project.institution_id != current_user.institution_id:
        return None
    return project


def _save_project_file(project: Project, uploaded_file, kind: str) -> str | None:
    if not uploaded_file or not uploaded_file.filename:
        return None
    extension = os.path.splitext(secure_filename(uploaded_file.filename))[1].lower()
    allowed = {
        "document": {".pdf"},
        "logo": {".png", ".jpg", ".jpeg", ".webp"},
        "member_photo": {".png", ".jpg", ".jpeg", ".webp"},
    }[kind]
    if extension not in allowed:
        raise ValueError("El documento debe ser PDF; logos y fotografías deben ser PNG, JPG, JPEG o WEBP.")
    relative_dir = os.path.join("uploads", "regional_projects", str(project.id))
    absolute_dir = os.path.join(current_app.static_folder, relative_dir)
    os.makedirs(absolute_dir, exist_ok=True)
    filename = f"{kind}-{uuid.uuid4().hex}{extension}"
    uploaded_file.save(os.path.join(absolute_dir, filename))
    return os.path.join(relative_dir, filename).replace("\\", "/")


def _save_school_shield(uploaded_file) -> str | None:
    if not uploaded_file or not uploaded_file.filename:
        return None
    extension = os.path.splitext(secure_filename(uploaded_file.filename))[1].lower()
    if extension not in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
        raise ValueError("El escudo debe ser PNG, JPG, JPEG, WEBP o GIF.")
    relative_dir = os.path.join("uploads", "institution")
    absolute_dir = os.path.join(current_app.static_folder, relative_dir)
    os.makedirs(absolute_dir, exist_ok=True)
    filename = f"shield-{uuid.uuid4().hex}{extension}"
    uploaded_file.save(os.path.join(absolute_dir, filename))
    return os.path.join(relative_dir, filename).replace("\\", "/")


def _delete_school_shield(relative_path: str | None):
    if not relative_path or relative_path.startswith(("http://", "https://")):
        return
    static_root = os.path.realpath(current_app.static_folder)
    target = os.path.realpath(os.path.join(static_root, relative_path.replace("/", os.sep)))
    if os.path.commonpath([static_root, target]) == static_root and os.path.isfile(target):
        os.remove(target)


def _delete_project_asset(relative_path: str | None):
    if not relative_path or relative_path == Project.GENERIC_LOGO_PATH or relative_path.startswith(("http://", "https://")):
        return
    static_root = os.path.realpath(current_app.static_folder)
    target = os.path.realpath(os.path.join(static_root, relative_path.replace("/", os.sep)))
    if os.path.commonpath([static_root, target]) == static_root and os.path.isfile(target):
        os.remove(target)


def _return_project_to_regional_review(project: Project, reason: str):
    previous_status = project.regional_status
    if previous_status != Project.STATUS_UNDER_REVIEW:
        db.session.add(ProjectStatusHistory(
            project=project,
            from_status=previous_status,
            to_status=Project.STATUS_UNDER_REVIEW,
            changed_by_id=current_user.id,
            notes=reason,
        ))
    project.regional_status = Project.STATUS_UNDER_REVIEW
    project.approved_at = None
    project.approved_by_id = None
    project.regional_notes = reason


def dashboard():
    projects = (
        Project.query.filter_by(institution_id=current_user.institution_id)
        .order_by(Project.created_at.desc())
        .all()
    )
    return render_template("school/dashboard.html", projects=projects, school=current_user.institution_ref)


def profile():
    school = current_user.institution_ref
    name = (request.form.get("name") or "").strip()
    responsible_name = (request.form.get("responsible_name") or "").strip()
    responsible_email = (request.form.get("responsible_email") or "").strip().lower()
    if not name or not responsible_name or not responsible_email:
        flash("Nombre, responsable y correo son obligatorios.", "error")
        return redirect(url_for("school.dashboard"))
    previous_shield = school.shield_path
    try:
        new_shield = _save_school_shield(request.files.get("institution_shield"))
    except ValueError as error:
        flash(str(error), "error")
        return redirect(url_for("school.dashboard"))
    school.name = name
    school.circuit = (request.form.get("circuit") or "").strip() or None
    school.regional_directorate = (request.form.get("regional_directorate") or "").strip() or None
    school.address = (request.form.get("address") or "").strip() or None
    school.responsible_name = responsible_name
    school.responsible_email = responsible_email
    school.responsible_phone = (request.form.get("responsible_phone") or "").strip() or None
    if new_shield:
        school.shield_path = new_shield
    db.session.flush()
    if new_shield:
        _delete_school_shield(previous_shield)
    log_event("school.profile.update", "institution", school.id, f"Perfil actualizado por coordinación: {school.code}")
    db.session.commit()
    flash("Información del colegio actualizada.", "success")
    return redirect(url_for("school.dashboard"))


def project_form(project_id: int | None = None):
    project = _owned_project(project_id) if project_id else None
    if project_id and not project:
        flash("Proyecto no encontrado.", "error")
        return redirect(url_for("school.dashboard"))
    if project and project.regional_status in {Project.STATUS_EVALUATED, Project.STATUS_REGIONAL_WINNER}:
        flash("Un proyecto evaluado no puede modificarse desde el colegio.", "error")
        return redirect(url_for("school.dashboard"))

    categories = Category.query.filter_by(is_active=True).order_by(Category.sort_order, Category.name).all()
    if request.method == "POST":
        before = None
        if project:
            before = {
                "title": project.title,
                "team_name": project.team_name,
                "description": project.description,
                "category_id": project.category_id,
                "advisor_name": project.advisor_name,
                "members": [{"id": member.id, "number": member.student_number, "name": member.full_name, "email": member.email} for member in project.members],
            }
        title = (request.form.get("title") or "").strip()
        team_name = (request.form.get("team_name") or "").strip()
        description = (request.form.get("description") or "").strip()
        category_id = request.form.get("category_id", type=int)
        category = db.session.get(Category, category_id) if category_id else None
        student_names = [(request.form.get(f"student_{index}_name") or "").strip() for index in range(1, 4)]
        student_emails = [(request.form.get(f"student_{index}_email") or "").strip().lower() for index in range(1, 4)]

        if not title or not team_name or not description or not category or not student_names[0]:
            flash("Título, equipo, descripción, categoría y primer estudiante son obligatorios.", "error")
            return render_template("school/project_form.html", project=project, categories=categories, school=current_user.institution_ref)

        if project is None:
            project = Project(
                institution_id=current_user.institution_id,
                institution_name=current_user.institution_ref.name,
                origin=Project.ORIGIN_REGIONAL_MANUAL,
                regional_status=Project.STATUS_DRAFT,
                title=title,
                team_name=team_name,
                representative_name=student_names[0],
                representative_email=student_emails[0] or current_user.email,
                category=category.code,
                category_id=category.id,
                description=description,
                advisor_name=(request.form.get("advisor_name") or "").strip() or current_user.full_name,
                advisor_email=None,
                advisor_phone=None,
            )
            db.session.add(project)
            db.session.flush()
            event_action = "school.project.create"
        else:
            event_action = "school.project.update"

        project.title = title
        project.team_name = team_name
        project.description = description
        project.category = category.code
        project.category_id = category.id
        project.representative_name = student_names[0]
        project.representative_email = student_emails[0] or current_user.email
        project.advisor_name = (request.form.get("advisor_name") or "").strip() or current_user.full_name
        project.advisor_email = None
        project.advisor_phone = None
        project.regional_notes = (request.form.get("school_notes") or "").strip() or None

        existing_members = {member.student_number: member for member in project.members}
        removed_member_photos = []
        for index, (name, email) in enumerate(zip(student_names, student_emails), start=1):
            member = existing_members.get(index)
            if name:
                if member is None:
                    member = ProjectMember(student_number=index)
                    project.members.append(member)
                member.full_name = name
                member.email = email or None
            elif member is not None:
                if member.photo_url:
                    removed_member_photos.append(member.photo_url)
                project.members.remove(member)

        try:
            document_path = _save_project_file(project, request.files.get("project_document"), "document")
            logo_path = _save_project_file(project, request.files.get("project_logo"), "logo")
        except ValueError as error:
            db.session.rollback()
            flash(str(error), "error")
            return redirect(request.url)
        obsolete_paths = list(removed_member_photos)
        document_changed = bool(document_path)
        if document_path:
            if project.project_document_path:
                obsolete_paths.append(project.project_document_path)
            project.project_document_path = document_path
            project.logistics_document_ok = False
        if logo_path:
            if project.has_real_logo:
                obsolete_paths.append(project.project_logo_path)
            project.project_logo_path = logo_path

        after = {
            "title": project.title,
            "team_name": project.team_name,
            "description": project.description,
            "category_id": project.category_id,
            "advisor_name": project.advisor_name,
            "members": [{"id": member.id, "number": member.student_number, "name": member.full_name, "email": member.email} for member in project.members],
        }
        information_changed = before is not None and before != after
        if (information_changed or document_changed) and project.regional_status not in {Project.STATUS_DRAFT, Project.STATUS_RETURNED}:
            _return_project_to_regional_review(project, "El colegio actualizó la información del proyecto; requiere nueva validación regional.")

        audit_change = json.dumps({"colegio": current_user.institution_ref.code, "antes": before, "después": after}, ensure_ascii=False, default=str)
        log_event(event_action, "project", project.id, audit_change)
        db.session.commit()
        for path in obsolete_paths:
            _delete_project_asset(path)
        flash("Borrador guardado correctamente.", "success")
        return redirect(url_for("school.dashboard"))

    return render_template("school/project_form.html", project=project, categories=categories, school=current_user.institution_ref)


def project_maintenance(project_id: int):
    project = _owned_project(project_id)
    if not project:
        flash("Proyecto no encontrado.", "error")
        return redirect(url_for("school.dashboard"))

    try:
        document_path = _save_project_file(project, request.files.get("project_document"), "document")
        logo_path = _save_project_file(project, request.files.get("project_logo"), "logo")
        previous_member_photos = {member.id: member.photo_url for member in project.members}
        received_member_photos = {}
        received_photos = 0
        for member in project.members:
            photo_path = _save_project_file(project, request.files.get(f"member_photo_{member.id}"), "member_photo")
            if photo_path:
                received_member_photos[member.id] = photo_path
                received_photos += 1
    except ValueError as error:
        db.session.rollback()
        flash(str(error), "error")
        return redirect(url_for("school.dashboard", _anchor=f"maintenance-project-{project.id}"))

    obsolete_paths = []
    document_changed = bool(document_path)
    if document_path:
        if project.project_document_path:
            obsolete_paths.append(project.project_document_path)
        project.project_document_path = document_path
        project.logistics_document_ok = False
    elif request.form.get("remove_project_document") == "1" and project.project_document_path:
        obsolete_paths.append(project.project_document_path)
        project.project_document_path = None
        project.logistics_document_ok = False
        document_changed = True
    if logo_path:
        if project.has_real_logo:
            obsolete_paths.append(project.project_logo_path)
        project.project_logo_path = logo_path
    elif request.form.get("remove_project_logo") == "1" and project.has_real_logo:
        obsolete_paths.append(project.project_logo_path)
        project.project_logo_path = None
    removed_photos = 0
    for member in project.members:
        new_photo = received_member_photos.get(member.id)
        previous_photo = previous_member_photos.get(member.id)
        if new_photo:
            if previous_photo:
                obsolete_paths.append(previous_photo)
            member.photo_url = new_photo
        elif request.form.get(f"remove_member_photo_{member.id}") == "1" and previous_photo:
            obsolete_paths.append(previous_photo)
            member.photo_url = None
            removed_photos += 1
    if document_changed and project.regional_status not in {Project.STATUS_DRAFT, Project.STATUS_RETURNED, Project.STATUS_SUBMITTED, Project.STATUS_RECEIVED}:
        _return_project_to_regional_review(project, "El colegio actualizó el documento; requiere nueva validación regional.")
    project.logistics_logo_ok = bool(project.has_real_logo)
    project.logistics_photos_ok = bool(project.members) and all(member.photo_url for member in project.members)
    project.required_resources = (request.form.get("required_resources") or "").strip() or None
    project.requirements_other = (request.form.get("requirements_other") or "").strip() or None
    project.logistics_notes = (request.form.get("school_logistics_notes") or "").strip() or None
    log_event(
        "school.project.maintenance.update",
        "project",
        project.id,
        f"Colegio {current_user.institution_ref.code}: documento={'actualizado' if document_changed else 'sin cambio'}, logo={'reemplazado' if logo_path else 'sin cambio'}, fotos_nuevas={received_photos}, fotos_retiradas={removed_photos}",
    )
    db.session.commit()
    for path in obsolete_paths:
        _delete_project_asset(path)
    flash("Mantenimiento del proyecto guardado correctamente.", "success")
    return redirect(url_for("school.dashboard"))


def submit_project(project_id: int):
    project = _owned_project(project_id)
    if not project:
        flash("Proyecto no encontrado.", "error")
        return redirect(url_for("school.dashboard"))
    if not project.members or not project.project_document_path or not project.has_real_logo or any(not member.photo_url for member in project.members):
        flash("Antes de enviar debes completar estudiantes, documento PDF, logo del proyecto y fotografía de cada integrante.", "error")
        return redirect(url_for("school.project_edit", project_id=project.id))
    try:
        transition_project(project, Project.STATUS_SUBMITTED, current_user, request.form.get("notes", ""))
        log_event("school.project.submit", "project", project.id, "Proyecto enviado a coordinación regional")
        db.session.commit()
        flash("Proyecto enviado a la coordinación regional.", "success")
    except RegionalTransitionError as error:
        db.session.rollback()
        flash(str(error), "error")
    return redirect(url_for("school.dashboard"))
