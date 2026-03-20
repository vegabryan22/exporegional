import os
import uuid
from datetime import date, datetime

from flask import current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user
from sqlalchemy.orm import joinedload
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models.category import Category
from app.models.campaign import Campaign
from app.models.level import Level
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.assignment import Assignment
from app.models.section import Section
from app.models.specialty import Specialty
from app.models.system_setting import SystemSetting
from app.models.workshop import Workshop
from app.services.audit_service import log_event
from app.services.parameter_service import get_active_evaluation_types

ALLOWED_DOC_EXTENSIONS = {"pdf", "doc", "docx", "ppt", "pptx", "zip", "rar"}
REGISTRATION_DRAFT_SESSION_KEY = "project_registration_draft"
REQUIREMENTS_OPTIONS = [
    ("corriente", "Conexion a corriente"),
    ("internet", "Internet"),
    ("agua", "Agua"),
    ("otros", "Otros"),
]


def _setting_as_bool(key: str, default: str = "0"):
    return SystemSetting.get_value(key, default) == "1"


def _parse_date(raw_value):
    try:
        return datetime.strptime((raw_value or "").strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def _get_extension(filename):
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def _save_project_document(document_file):
    original_name = secure_filename(document_file.filename or "")
    extension = _get_extension(original_name)
    if extension not in ALLOWED_DOC_EXTENSIONS:
        raise ValueError("Formato de documento invalido. Usa PDF, DOC, DOCX, PPT, PPTX, ZIP o RAR.")

    relative_dir = os.path.join("uploads", "projects", "documents")
    absolute_dir = os.path.join(current_app.static_folder, relative_dir)
    os.makedirs(absolute_dir, exist_ok=True)

    unique_name = f"{uuid.uuid4().hex}.{extension}"
    absolute_path = os.path.join(absolute_dir, unique_name)
    document_file.save(absolute_path)
    return f"{relative_dir}/{unique_name}".replace("\\", "/")


def _save_temp_project_document(document_file):
    original_name = secure_filename(document_file.filename or "")
    extension = _get_extension(original_name)
    if extension not in ALLOWED_DOC_EXTENSIONS:
        raise ValueError("Formato de documento invalido. Usa PDF, DOC, DOCX, PPT, PPTX, ZIP o RAR.")

    relative_dir = os.path.join("uploads", "projects", "temp_documents")
    absolute_dir = os.path.join(current_app.static_folder, relative_dir)
    os.makedirs(absolute_dir, exist_ok=True)

    unique_name = f"{uuid.uuid4().hex}_{original_name or ('documento.' + extension)}"
    absolute_path = os.path.join(absolute_dir, unique_name)
    document_file.save(absolute_path)
    return f"{relative_dir}/{unique_name}".replace("\\", "/")


def _promote_temp_project_document(temp_relative_path):
    if not temp_relative_path:
        return ""

    temp_absolute_path = os.path.join(current_app.static_folder, temp_relative_path.replace("/", os.sep))
    if not os.path.exists(temp_absolute_path):
        raise ValueError("El documento temporal ya no esta disponible. Adjuntalo nuevamente.")

    _, filename = os.path.split(temp_absolute_path)
    extension = _get_extension(filename)
    relative_dir = os.path.join("uploads", "projects", "documents")
    absolute_dir = os.path.join(current_app.static_folder, relative_dir)
    os.makedirs(absolute_dir, exist_ok=True)

    final_name = f"{uuid.uuid4().hex}.{extension}"
    final_absolute_path = os.path.join(absolute_dir, final_name)
    os.replace(temp_absolute_path, final_absolute_path)
    return f"{relative_dir}/{final_name}".replace("\\", "/")


def _delete_uploaded_file(relative_path):
    if not relative_path:
        return
    try:
        absolute_path = os.path.join(current_app.static_folder, relative_path.replace("/", os.sep))
        if os.path.exists(absolute_path):
            os.remove(absolute_path)
    except OSError:
        return


def _serialize_form_data(form_data):
    if hasattr(form_data, "lists"):
        data = {}
        for key, values in form_data.lists():
            data[key] = values if len(values) > 1 else (values[0] if values else "")
        return data
    return dict(form_data)


def _draft_form_value(form_data, key, default=""):
    value = form_data.get(key, default)
    if isinstance(value, list):
        return value[-1] if value else default
    return value


def _draft_form_list(form_data, key):
    value = form_data.get(key, [])
    if isinstance(value, list):
        return value
    return [value] if value else []


def _store_registration_draft(form_data, temp_document_path=""):
    session[REGISTRATION_DRAFT_SESSION_KEY] = {
        "form_data": _serialize_form_data(form_data),
        "temp_document_path": temp_document_path or "",
    }
    session.modified = True


def _clear_registration_draft():
    draft = session.pop(REGISTRATION_DRAFT_SESSION_KEY, None) or {}
    _delete_uploaded_file(draft.get("temp_document_path", ""))
    session.modified = True


def _draft_context(form_data=None, temp_document_path=""):
    draft = session.get(REGISTRATION_DRAFT_SESSION_KEY, {})
    resolved_form_data = form_data if form_data is not None else draft.get("form_data", {})
    resolved_temp_path = temp_document_path if temp_document_path else draft.get("temp_document_path", "")
    temp_document_name = ""
    if resolved_temp_path:
        filename = os.path.basename(resolved_temp_path)
        temp_document_name = filename.split("_", 1)[1] if "_" in filename else filename
    context = _current_form_context(resolved_form_data)
    context.update(
        {
            "temp_document_path": resolved_temp_path,
            "temp_document_name": temp_document_name,
        }
    )
    return context


def _required_student_numbers(form_data):
    required = [1]
    if (form_data.get("student_1_more") or "").strip().lower() == "si":
        required.append(2)
        if (form_data.get("student_2_more") or "").strip().lower() == "si":
            required.append(3)
    return required


def _normalize_gender(form_data, index):
    base = (form_data.get(f"student_{index}_gender") or "").strip().lower()
    if base != "otros":
        return base
    return (form_data.get(f"student_{index}_gender_other") or "").strip()


def _build_student(form_data, index, section_name, focus_name):
    return {
        "student_number": index,
        "full_name": (form_data.get(f"student_{index}_full_name") or "").strip(),
        "identity_number": (form_data.get(f"student_{index}_identity") or "").strip(),
        "birth_date": _parse_date(form_data.get(f"student_{index}_birth_date")),
        "gender": _normalize_gender(form_data, index),
        "specialty": focus_name,
        "section_name": section_name,
        "has_dining_scholarship": (form_data.get(f"student_{index}_scholarship") or "").strip().lower() == "si",
        "participates_in_english": (form_data.get(f"student_{index}_english") or "").strip().lower() == "si",
        "phone": (form_data.get(f"student_{index}_phone") or "").strip(),
        "email": (form_data.get(f"student_{index}_email") or "").strip().lower(),
    }


def _validate_students(students, required_numbers):
    by_number = {student["student_number"]: student for student in students}
    for number in required_numbers:
        student = by_number[number]
        required = [
            student["full_name"],
            student["identity_number"],
            student["birth_date"],
            student["gender"],
            student["phone"],
            student["email"],
            student["section_name"],
            student["specialty"],
        ]
        if not all(required):
            return f"Completa todos los datos obligatorios del estudiante N.{number}."
    return None


def _current_form_context(form_data):
    categories = (
        Category.query.filter(Category.is_active.is_(True), Category.code.in_(["steam", "emprendimiento"]))
        .order_by(Category.sort_order.asc())
        .all()
    )
    levels = Level.query.filter_by(is_active=True).order_by(Level.sort_order.asc()).all()
    sections = (
        Section.query.join(Level, Level.id == Section.level_id)
        .filter(Section.is_active.is_(True), Level.is_active.is_(True))
        .order_by(Level.sort_order.asc(), Section.sort_order.asc(), Section.name.asc())
        .all()
    )
    specialties = Specialty.query.filter_by(is_active=True).order_by(Specialty.sort_order.asc()).all()
    workshops = Workshop.query.filter_by(is_active=True).order_by(Workshop.sort_order.asc()).all()

    req_values = form_data.getlist("requirements") if hasattr(form_data, "getlist") else _draft_form_list(form_data, "requirements")

    active_campaign = (
        Campaign.query.filter(
            Campaign.is_active.is_(True),
            Campaign.start_date <= date.today(),
            Campaign.end_date >= date.today(),
        )
        .order_by(Campaign.start_date.desc())
        .first()
    )

    return {
        "form_data": form_data,
        "req_values": req_values,
        "categories": categories,
        "levels": levels,
        "sections": sections,
        "specialties": specialties,
        "workshops": workshops,
        "requirements_options": REQUIREMENTS_OPTIONS,
        "active_campaign": active_campaign,
    }


def list_projects():
    is_admin = current_user.is_authenticated and getattr(current_user, "has_admin_access", False)
    maintenance_enabled = _setting_as_bool("maintenance_enabled", "0")

    if not is_admin and maintenance_enabled:
        maintenance_message = SystemSetting.get_value(
            "maintenance_message",
            "Estamos cargando informacion de proyectos. Vuelve pronto.",
        )
        maintenance_image_path = SystemSetting.get_value("maintenance_image_path", "")
        return render_template(
            "public/maintenance.html",
            maintenance_message=maintenance_message,
            maintenance_image_path=maintenance_image_path,
        )

    projects = (
        Project.query.filter(Project.is_active.is_(True))
        .options(joinedload(Project.members), joinedload(Project.section), joinedload(Project.specialty_ref), joinedload(Project.workshop_ref))
        .order_by(Project.created_at.desc())
        .all()
    )

    categories = Category.query.filter_by(is_active=True).order_by(Category.sort_order.asc()).all()
    category_map = {category.code: category.name for category in categories}
    projects_by_category = {category.code: [] for category in categories}
    for project in projects:
        projects_by_category.setdefault(project.category, []).append(project)

    return render_template("public/home_projects.html", projects_by_category=projects_by_category, category_map=category_map)


def home_intro():
    projects = (
        Project.query.filter(Project.is_active.is_(True))
        .options(joinedload(Project.members), joinedload(Project.section), joinedload(Project.specialty_ref), joinedload(Project.workshop_ref))
        .order_by(Project.created_at.desc())
        .all()
    )

    categories = Category.query.filter_by(is_active=True).order_by(Category.sort_order.asc()).all()
    category_map = {category.code: category.name for category in categories}
    projects_by_category = {category.code: [] for category in categories}
    for project in projects:
        projects_by_category.setdefault(project.category, []).append(project)

    return render_template("public/home_intro.html", projects_by_category=projects_by_category, category_map=category_map)


def register_project():
    active_campaign = (
        Campaign.query.filter(
            Campaign.is_active.is_(True),
            Campaign.start_date <= date.today(),
            Campaign.end_date >= date.today(),
        )
        .order_by(Campaign.start_date.desc())
        .first()
    )
    if not active_campaign:
        flash("No hay una campaña de inscripción activa en este momento.", "error")
        return redirect(url_for("public.index"))

    if request.method == "POST":
        form_data = request.form
        document_file = request.files.get("project_document")
        temp_document_path = (form_data.get("temp_document_path") or "").strip()

        if document_file and document_file.filename:
            try:
                new_temp_document_path = _save_temp_project_document(document_file)
            except ValueError as error:
                _store_registration_draft(form_data, temp_document_path)
                flash(str(error), "error")
                return render_template("public/register_project.html", **_draft_context(form_data, temp_document_path))
            _delete_uploaded_file(temp_document_path)
            temp_document_path = new_temp_document_path

        _store_registration_draft(form_data, temp_document_path)

        registration_date = _parse_date(_draft_form_value(form_data, "registration_date"))
        category = (_draft_form_value(form_data, "category") or "").strip()
        section_id = request.form.get("section_id", type=int)
        specialty_id = request.form.get("specialty_id", type=int)
        workshop_id = request.form.get("workshop_id", type=int)

        requirements = [item.strip().lower() for item in request.form.getlist("requirements") if item.strip()]
        requirements_other = (_draft_form_value(form_data, "requirements_other") or "").strip()
        required_students = _required_student_numbers(form_data)

        section = Section.query.get(section_id) if section_id else None
        specialty = Specialty.query.get(specialty_id) if specialty_id else None
        workshop = Workshop.query.get(workshop_id) if workshop_id else None
        level_code = section.level.code if section and section.level else ""

        focus_name = specialty.name if specialty else (workshop.name if workshop else "")
        section_name = section.name if section else ""
        students = [_build_student(form_data, i, section_name, focus_name) for i in [1, 2, 3]]

        project = Project(
            registration_date=registration_date,
            title=(_draft_form_value(form_data, "title") or "").strip(),
            team_name=(_draft_form_value(form_data, "team_name") or "").strip() or "Equipo ExpoTEC",
            representative_name=(_draft_form_value(form_data, "student_1_full_name") or "").strip(),
            representative_email=(_draft_form_value(form_data, "student_1_email") or "").strip().lower(),
            representative_phone=(_draft_form_value(form_data, "student_1_phone") or "").strip(),
            institution_name="CTP Roberto Gamboa Valverde",
            grade_level=level_code,
            specialty=focus_name,
            section_id=section_id,
            specialty_id=specialty_id,
            workshop_id=workshop_id,
            campaign_id=active_campaign.id,
            advisor_name=(_draft_form_value(form_data, "advisor_name") or "").strip(),
            advisor_identity=(_draft_form_value(form_data, "advisor_identity") or "").strip(),
            advisor_email=(_draft_form_value(form_data, "advisor_email") or "").strip().lower(),
            category=category,
            description=(_draft_form_value(form_data, "description") or "Proyecto registrado mediante ExpoTEC-1.").strip(),
            required_resources=(_draft_form_value(form_data, "required_resources") or "").strip(),
            requirements_summary=", ".join(requirements),
            requirements_other=requirements_other,
            consent_terms=(_draft_form_value(form_data, "declaration") or "").strip().lower() == "si",
        )

        valid_categories = {item.code for item in Category.query.filter_by(is_active=True).all()}

        if not registration_date:
            flash("La fecha es obligatoria.", "error")
            return render_template("public/register_project.html", **_draft_context(form_data, temp_document_path))
        if not project.title:
            flash("El nombre del proyecto es obligatorio.", "error")
            return render_template("public/register_project.html", **_draft_context(form_data, temp_document_path))
        if category not in valid_categories:
            flash("Categoria invalida.", "error")
            return render_template("public/register_project.html", **_draft_context(form_data, temp_document_path))
        if not section:
            flash("Debes seleccionar una seccion valida.", "error")
            return render_template("public/register_project.html", **_draft_context(form_data, temp_document_path))

        if category == "emprendimiento":
            if level_code not in {"10", "11", "12"}:
                flash("Emprendimiento solo permite niveles 10, 11 y 12.", "error")
                return render_template("public/register_project.html", **_draft_context(form_data, temp_document_path))
            if not specialty:
                flash("Para Emprendimiento debes indicar la especialidad.", "error")
                return render_template("public/register_project.html", **_draft_context(form_data, temp_document_path))
            project.workshop_id = None
        elif category == "steam":
            if level_code not in {"7", "8", "9"}:
                flash("STEAM solo permite talleres exploratorios de 7, 8 y 9.", "error")
                return render_template("public/register_project.html", **_draft_context(form_data, temp_document_path))
            if not workshop:
                flash("Para STEAM debes indicar el taller.", "error")
                return render_template("public/register_project.html", **_draft_context(form_data, temp_document_path))
            project.specialty_id = None
        else:
            flash("Categoria invalida para este formulario.", "error")
            return render_template("public/register_project.html", **_draft_context(form_data, temp_document_path))

        if not requirements:
            flash("Debes seleccionar al menos un requerimiento.", "error")
            return render_template("public/register_project.html", **_draft_context(form_data, temp_document_path))
        if "otros" in requirements and not requirements_other:
            flash("Debes completar el detalle de 'Otros'.", "error")
            return render_template("public/register_project.html", **_draft_context(form_data, temp_document_path))

        if not temp_document_path:
            flash("Debes adjuntar la documentacion del proyecto.", "error")
            return render_template("public/register_project.html", **_draft_context(form_data, temp_document_path))
        students_error = _validate_students(students, required_students)
        if students_error:
            flash(students_error, "error")
            return render_template("public/register_project.html", **_draft_context(form_data, temp_document_path))

        if not all([project.advisor_name, project.advisor_identity, project.advisor_email]):
            flash("Completa los datos del docente tutor.", "error")
            return render_template("public/register_project.html", **_draft_context(form_data, temp_document_path))

        if not project.consent_terms:
            flash("Debes aceptar la declaracion para finalizar la inscripcion.", "error")
            return render_template("public/register_project.html", **_draft_context(form_data, temp_document_path))

        try:
            project.project_document_path = _promote_temp_project_document(temp_document_path)
        except ValueError as error:
            flash(str(error), "error")
            return render_template("public/register_project.html", **_draft_context(form_data, temp_document_path))

        db.session.add(project)
        db.session.flush()
        for number in required_students:
            student = next(item for item in students if item["student_number"] == number)
            db.session.add(ProjectMember(project_id=project.id, **student))

        log_event(
            "public.project.create",
            "project",
            entity_id=project.id,
            detail=(
                f"Proyecto inscrito: #{project.id} '{project.title}' "
                f"categoria={project.category} equipo='{project.team_name}' estudiantes={len(required_students)}"
            ),
        )
        db.session.commit()
        _clear_registration_draft()
        flash("Proyecto inscrito correctamente con formato ExpoTEC-1.", "success")
        return redirect(url_for("public.register_project"))

    return render_template("public/register_project.html", **_draft_context())


def evaluate_project_entry(project_id: int):
    project = Project.query.get_or_404(project_id)
    if not project.is_active:
        flash("Este proyecto esta inactivo.", "error")
        return redirect(url_for("public.index"))

    if not current_user.is_authenticated:
        return redirect(url_for("auth.login", next=url_for("public.evaluate_project_entry", project_id=project.id)))

    if getattr(current_user, "has_admin_access", False):
        return redirect(url_for("admin.projects_page"))

    assignment = Assignment.query.filter_by(judge_id=current_user.id, project_id=project.id).first()
    if not assignment:
        flash("No tienes este proyecto asignado para evaluacion.", "error")
        return redirect(url_for("judge.dashboard"))

    evaluation_types = get_active_evaluation_types()
    if not evaluation_types:
        flash("No hay tipos de evaluacion configurados.", "error")
        return redirect(url_for("judge.dashboard"))

    selected = next((item for item in evaluation_types if item.code == "escrito"), evaluation_types[0])
    return redirect(url_for("judge.evaluate", project_id=project.id, type=selected.code))
