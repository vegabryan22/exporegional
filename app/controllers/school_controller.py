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


def dashboard():
    projects = (
        Project.query.filter_by(institution_id=current_user.institution_id)
        .order_by(Project.created_at.desc())
        .all()
    )
    return render_template("school/dashboard.html", projects=projects, school=current_user.institution_ref)


def project_form(project_id: int | None = None):
    project = _owned_project(project_id) if project_id else None
    if project_id and not project:
        flash("Proyecto no encontrado.", "error")
        return redirect(url_for("school.dashboard"))
    if project and project.regional_status not in {Project.STATUS_DRAFT, Project.STATUS_RETURNED}:
        flash("El proyecto ya fue enviado y no admite edición en este estado.", "error")
        return redirect(url_for("school.dashboard"))

    categories = Category.query.filter_by(is_active=True).order_by(Category.sort_order, Category.name).all()
    if request.method == "POST":
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
                advisor_email=(request.form.get("advisor_email") or "").strip().lower() or current_user.email,
                advisor_phone=(request.form.get("advisor_phone") or "").strip() or None,
            )
            db.session.add(project)
            db.session.flush()
            event_action = "school.project.create"
        else:
            project.members.clear()
            event_action = "school.project.update"

        project.title = title
        project.team_name = team_name
        project.description = description
        project.category = category.code
        project.category_id = category.id
        project.representative_name = student_names[0]
        project.representative_email = student_emails[0] or current_user.email
        project.advisor_name = (request.form.get("advisor_name") or "").strip() or current_user.full_name
        project.advisor_email = (request.form.get("advisor_email") or "").strip().lower() or current_user.email
        project.advisor_phone = (request.form.get("advisor_phone") or "").strip() or None
        project.regional_notes = (request.form.get("school_notes") or "").strip() or None

        for index, (name, email) in enumerate(zip(student_names, student_emails), start=1):
            if name:
                project.members.append(ProjectMember(student_number=index, full_name=name, email=email or None))

        try:
            document_path = _save_project_file(project, request.files.get("project_document"), "document")
            logo_path = _save_project_file(project, request.files.get("project_logo"), "logo")
        except ValueError as error:
            db.session.rollback()
            flash(str(error), "error")
            return redirect(request.url)
        if document_path:
            project.project_document_path = document_path
        if logo_path:
            project.project_logo_path = logo_path

        log_event(event_action, "project", project.id, f"Proyecto manual regional del colegio {current_user.institution_ref.code}")
        db.session.commit()
        flash("Borrador guardado correctamente.", "success")
        return redirect(url_for("school.dashboard"))

    return render_template("school/project_form.html", project=project, categories=categories, school=current_user.institution_ref)


def submit_project(project_id: int):
    project = _owned_project(project_id)
    if not project:
        flash("Proyecto no encontrado.", "error")
        return redirect(url_for("school.dashboard"))
    if not project.members or not project.project_document_path:
        flash("Debes registrar estudiantes y adjuntar el documento antes de enviar.", "error")
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
