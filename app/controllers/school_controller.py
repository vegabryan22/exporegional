import json
import os
import secrets
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
from app.models.system_setting import SystemSetting
from app.services.audit_service import log_event
from app.services.evaluation_service import project_evaluation_count_summary, project_evaluation_target_summary
from app.services.regional_readiness_service import approval_missing_requirements
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
    school = current_user.institution_ref
    project_rows = []
    completed_files = 0
    completed_evaluations = 0
    expected_evaluations = 0
    attention_projects = 0
    for project in projects:
        missing = approval_missing_requirements(project)
        evaluation_counts = project_evaluation_count_summary(project)
        evaluation_targets = project_evaluation_target_summary(project)
        members = list(project.members or [])
        file_checks = [
            bool((project.title or "").strip()),
            bool((project.team_name or "").strip()),
            bool(project.category_id),
            bool((project.advisor_name or "").strip()),
            bool(members),
            bool(project.project_document_path),
            bool(project.has_real_logo),
            bool(project.logistics_registration_form_signed_ok),
        ]
        file_checks.extend(bool((member.photo_url or "").strip()) for member in members)
        file_checks.extend(bool(member.consent_signed_ok) for member in members)
        project_completed = evaluation_counts["completed_evaluations"] + evaluation_counts["completed_english_evaluations"]
        project_expected = evaluation_targets["expected_evaluations"] + evaluation_targets["expected_english_evaluations"]
        completed_evaluations += project_completed
        expected_evaluations += project_expected
        if not missing:
            completed_files += 1
        if missing or project.regional_status == Project.STATUS_RETURNED:
            attention_projects += 1
        project_rows.append({
            "project": project,
            "missing": missing,
            "file_progress": round((sum(file_checks) / len(file_checks)) * 100),
            "evaluation_completed": project_completed,
            "evaluation_expected": project_expected,
        })

    minimum_judges = _minimum_school_judges()
    active_judges = Judge.query.filter_by(
        institution_id=school.id,
        role=Judge.ROLE_JUDGE,
        is_active_user=True,
    ).count()
    metrics = {
        "projects": len(projects),
        "files_complete": completed_files,
        "files_percent": round((completed_files / len(projects)) * 100) if projects else 0,
        "attention_projects": attention_projects,
        "judges": active_judges,
        "minimum_judges": minimum_judges,
        "judges_pending": max(0, minimum_judges - active_judges),
        "evaluations_completed": completed_evaluations,
        "evaluations_expected": expected_evaluations,
        "evaluations_percent": round((completed_evaluations / expected_evaluations) * 100) if expected_evaluations else 0,
    }
    return render_template(
        "school/dashboard.html",
        projects=projects,
        project_rows=project_rows,
        metrics=metrics,
        school=school,
    )


def _minimum_school_judges() -> int:
    try:
        return max(1, min(50, int(SystemSetting.get_value("regional_minimum_judges_per_school", "2"))))
    except (TypeError, ValueError):
        return 2


def judges():
    school = current_user.institution_ref
    if request.method == "POST":
        action = (request.form.get("action") or "").strip()
        judge_id = request.form.get("judge_id", type=int)
        judge = None
        if judge_id:
            judge = Judge.query.filter_by(
                id=judge_id,
                institution_id=school.id,
                role=Judge.ROLE_JUDGE,
            ).first()

        if action in {"update", "delete"} and not judge:
            log_event("school.judge.action_blocked", "judge", judge_id, f"Colegio={school.code}; acción={action}")
            db.session.commit()
            flash("El juez no pertenece a este colegio.", "error")
            return redirect(url_for("school.judges"))

        if action in {"create", "update"}:
            full_name = (request.form.get("full_name") or "").strip()
            email = (request.form.get("email") or "").strip().lower()
            if not full_name or not email:
                flash("Nombre y correo son obligatorios.", "error")
                return redirect(url_for("school.judges"))
            duplicate = Judge.query.filter(Judge.email == email, Judge.id != (judge.id if judge else 0)).first()
            if duplicate:
                flash("Ya existe una cuenta con ese correo.", "error")
                return redirect(url_for("school.judges"))
            before = None
            if judge:
                before = {"nombre": judge.full_name, "correo": judge.email, "activo": judge.is_active_user}
            else:
                temporary_password = secrets.token_urlsafe(10)
                judge = Judge(
                    role=Judge.ROLE_JUDGE,
                    is_admin=False,
                    institution_id=school.id,
                    institution=school.name,
                    is_active_user=True,
                    must_change_password=True,
                    registered_from_public_form=False,
                )
                judge.set_password(temporary_password)
                db.session.add(judge)
            judge.full_name = full_name
            judge.email = email
            judge.identity = (request.form.get("identity") or "").strip() or None
            judge.phone = (request.form.get("phone") or "").strip() or None
            judge.job_title = (request.form.get("job_title") or "").strip() or None
            judge.previous_expo = (request.form.get("previous_expo") or "").strip() or None
            judge.category_scope = request.form.get("category_scope") if request.form.get("category_scope") in {"steam", "emprendimiento", "ambas"} else "ambas"
            scope = request.form.get("evaluation_scope", "ambas")
            judge.can_evaluate_documentation = scope in {"documentacion", "ambas"}
            judge.can_evaluate_exposition = scope in {"exposicion", "ambas"}
            judge.can_evaluate_english = request.form.get("can_evaluate_english") == "1"
            judge.is_active_user = request.form.get("is_active_user", "1") == "1"
            judge.role = Judge.ROLE_JUDGE
            judge.is_admin = False
            judge.institution_id = school.id
            judge.institution = school.name
            db.session.flush()
            after = {"nombre": judge.full_name, "correo": judge.email, "activo": judge.is_active_user}
            log_event(
                "school.judge.create" if before is None else "school.judge.update",
                "judge", judge.id,
                json.dumps({"colegio": school.code, "antes": before, "después": after}, ensure_ascii=False),
            )
            db.session.commit()
            if before is None:
                from app.controllers.admin_controller import _send_judge_credentials_email
                _send_judge_credentials_email(judge, temporary_password)
                db.session.commit()
            flash("Juez inscrito correctamente." if before is None else "Información del juez actualizada.", "success")
        elif action == "delete":
            detail = json.dumps({"colegio": school.code, "juez": judge.full_name, "correo": judge.email}, ensure_ascii=False)
            log_event("school.judge.delete", "judge", judge.id, detail)
            db.session.delete(judge)
            db.session.commit()
            flash("Juez eliminado del registro del colegio.", "success")
        else:
            flash("Acción no válida.", "error")
        return redirect(url_for("school.judges"))

    school_judges = Judge.query.filter_by(institution_id=school.id, role=Judge.ROLE_JUDGE).order_by(Judge.full_name).all()
    minimum = _minimum_school_judges()
    active_count = sum(1 for judge in school_judges if judge.is_active_user)
    return render_template(
        "school/judges.html", school=school, judges=school_judges,
        minimum_judges=minimum, active_judges=active_count,
        missing_judges=max(0, minimum - active_count),
    )


def project_workspace(project_id: int):
    from app.controllers import admin_controller

    project = _owned_project(project_id)
    if not project:
        flash("Proyecto no encontrado.", "error")
        return redirect(url_for("school.dashboard"))

    if request.method == "POST":
        action = (request.form.get("action") or "").strip()
        allowed_actions = {
            "update_project", "update_project_logistics", "replace_project_document",
            "upload_project_logo", "upload_member_photo", "delete_member_photo",
            "create_project_member", "update_project_member", "delete_project_member", "delete_project",
        }
        target_project_id = request.form.get("project_id", type=int)
        member_id = request.form.get("member_id", type=int)
        if member_id:
            member = db.session.get(ProjectMember, member_id)
            target_project_id = member.project_id if member else None
        if action not in allowed_actions or target_project_id != project.id:
            log_event("school.project.action_blocked", "project", project.id, f"Acción fuera de alcance: {action or 'vacía'}")
            db.session.commit()
            flash("La acción solicitada no pertenece a este proyecto o no está permitida.", "error")
            return redirect(url_for("school.project_workspace", project_id=project.id))
        admin_controller._handle_action(action)
        if action == "delete_project" and db.session.get(Project, project_id) is None:
            return redirect(url_for("school.dashboard"))
        return redirect(url_for("school.project_workspace", project_id=project.id))

    context = admin_controller._base_context("projects")
    context["projects"] = [project]
    context["advisor_stats"] = admin_controller._build_advisor_stats([project])
    context["project_logistics_summary"] = admin_controller._build_project_logistics_summary([project])
    context["pending_document_revisions"] = []
    context["pending_member_edit_requests"] = []
    context["action_url"] = url_for("school.project_workspace", project_id=project.id)
    context["next_url"] = request.path
    context["school_mode"] = True
    context["school"] = current_user.institution_ref
    return render_template("admin/projects.html", **context)


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
