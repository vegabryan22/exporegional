import os
import re
import uuid
from io import BytesIO
from datetime import date, datetime

from flask import current_app, flash, redirect, render_template, request, send_file, session, url_for
from flask_login import current_user
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models.category import Category
from app.models.campaign import Campaign
from app.models.level import Level
from app.models.project import Project
from app.models.project_document_revision import ProjectDocumentRevision
from app.models.project_member import ProjectMember
from app.models.project_member_edit_request import ProjectMemberEditRequest
from app.models.project_type import ProjectType
from app.models.assignment import Assignment
from app.models.section import Section
from app.models.specialty import Specialty
from app.models.system_setting import SystemSetting
from app.models.thematic_axis import ThematicAxis
from app.models.judge import Judge
from app.services.audit_service import log_event
from app.services.mail_service import send_email, smtp_is_configured
from app.services.parameter_service import get_active_evaluation_types

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False

ALLOWED_DOC_EXTENSIONS = {"pdf"}
REGISTRATION_DRAFT_SESSION_KEY = "project_registration_draft"
IDENTITY_MAX_LENGTH = 12
PHONE_RE = re.compile(r"^\d{8}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
REQUIREMENTS_OPTIONS = [
    ("corriente", "Conexion a corriente"),
    ("salidas", "Salidas"),
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


def _normalize_identity(raw_value: str) -> str:
    value = (raw_value or "").strip().upper()
    value = re.sub(r"[\s-]+", "", value)
    return value


def _normalize_phone(raw_value: str) -> str:
    return re.sub(r"\D+", "", raw_value or "")


def _phone_error(phone: str, label: str) -> str | None:
    if not phone:
        return f"{label} es obligatorio."
    if not PHONE_RE.fullmatch(phone):
        return f"{label} debe contener exactamente 8 digitos."
    return None


def _email_error(email: str, label: str, required: bool = True) -> str | None:
    if not email:
        return f"{label} es obligatorio." if required else None
    if not EMAIL_RE.fullmatch(email):
        return f"{label} debe tener un formato valido."
    return None


def _identity_error(identity: str, label: str) -> str | None:
    if not identity:
        return f"{label} es obligatorio."
    if len(identity) > IDENTITY_MAX_LENGTH:
        return f"{label} no puede superar {IDENTITY_MAX_LENGTH} caracteres."
    if not re.fullmatch(r"[A-Z0-9]+", identity):
        return f"{label} solo puede contener letras y numeros, sin espacios ni guiones."
    return None


def _get_extension(filename):
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def _save_project_document(document_file):
    original_name = secure_filename(document_file.filename or "")
    extension = _get_extension(original_name)
    if extension not in ALLOWED_DOC_EXTENSIONS:
        raise ValueError("Formato de documento invalido. La documentacion del proyecto debe ser PDF.")

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
        raise ValueError("Formato de documento invalido. La documentacion del proyecto debe ser PDF.")

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
    if extension not in ALLOWED_DOC_EXTENSIONS:
        raise ValueError("Formato de documento invalido. La documentacion del proyecto debe ser PDF.")
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


def _pdf_text(value) -> str:
    text = "" if value is None else str(value)
    return text.encode("latin-1", "replace").decode("latin-1")


def _pdf_lines(text, width_chars=95):
    words = _pdf_text(text).split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= width_chars:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def _draw_wrapped(pdf, text, x, y, width_chars=95, leading=12, font="Helvetica", size=9):
    pdf.setFont(font, size)
    for line in _pdf_lines(text, width_chars=width_chars):
        pdf.drawString(x, y, line)
        y -= leading
    return y


def _pdf_lines_by_width(pdf, text, max_width, font="Helvetica", size=9):
    words = _pdf_text(text).split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if not current or pdf.stringWidth(candidate, font, size) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def _draw_wrapped_width(pdf, text, x, y, max_width, leading=12, font="Helvetica", size=9):
    pdf.setFont(font, size)
    for line in _pdf_lines_by_width(pdf, text, max_width, font=font, size=size):
        pdf.drawString(x, y, line)
        y -= leading
    return y


def _static_pdf_image_path(relative_path: str) -> str:
    if not relative_path or relative_path.startswith("http://") or relative_path.startswith("https://"):
        return ""
    absolute_path = os.path.join(current_app.static_folder, relative_path.replace("/", os.sep))
    return absolute_path if os.path.exists(absolute_path) else ""


def _draw_pdf_logo(pdf, relative_path: str, x: float, y: float, max_width: float = 64, max_height: float = 52):
    absolute_path = _static_pdf_image_path(relative_path)
    if not absolute_path:
        return False
    try:
        image = ImageReader(absolute_path)
        image_width, image_height = image.getSize()
        scale = min(max_width / image_width, max_height / image_height)
        draw_width = image_width * scale
        draw_height = image_height * scale
        pdf.drawImage(
            image,
            x + (max_width - draw_width) / 2,
            y + (max_height - draw_height) / 2,
            width=draw_width,
            height=draw_height,
            preserveAspectRatio=True,
            mask="auto",
        )
        return True
    except Exception:
        return False


def _draw_document_header(pdf, title, subtitle="Curso lectivo 2026"):
    width, height = letter
    school_logo = SystemSetting.get_value("school_logo_path", "")
    expo_logo = SystemSetting.get_value("expo_logo_path", "")
    school_name = SystemSetting.get_value("school_name", "CTP Roberto Gamboa Valverde")

    logo_y = height - 72
    if not _draw_pdf_logo(pdf, school_logo, 42, logo_y, max_width=62, max_height=54):
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(42, height - 50, "CTP")
    if not _draw_pdf_logo(pdf, expo_logo, width - 104, logo_y, max_width=62, max_height=54):
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawRightString(width - 42, height - 50, "ExpoTEC")

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawCentredString(width / 2, height - 50, _pdf_text(title))
    pdf.setFont("Helvetica", 10)
    pdf.drawCentredString(width / 2, height - 66, _pdf_text(subtitle))
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawCentredString(width / 2, height - 80, _pdf_text(school_name))
    pdf.line(42, height - 92, width - 42, height - 92)
    return height - 118


def _draw_field(pdf, label, value, x, y, line_width=230):
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(x, y, _pdf_text(label))
    pdf.setFont("Helvetica", 9)
    pdf.drawString(x, y - 13, _pdf_text(value or ""))
    pdf.line(x, y - 16, x + line_width, y - 16)
    return y - 30


def _pdf_date(value):
    if not value:
        return ""
    if isinstance(value, (date, datetime)):
        return value.strftime("%d/%m/%Y")
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        pass
    return str(value)


def _pdf_setting(key, default=""):
    return SystemSetting.get_value(key, default) or default


def _pdf_setting_any(keys, default=""):
    for key in keys:
        value = SystemSetting.get_value(key, "")
        if value:
            return value
    return default


def _draw_excel_background(pdf, width, height, step_x=50, step_y=18):
    pdf.saveState()
    pdf.setStrokeColor(colors.HexColor("#d9d9d9"))
    pdf.setLineWidth(0.25)
    x = 0
    while x <= width:
        pdf.line(x, 0, x, height)
        x += step_x
    y = 0
    while y <= height:
        pdf.line(0, y, width, y)
        y += step_y
    pdf.restoreState()


def _draw_pdf_cell(pdf, x, y, w, h, text="", bold=False, size=8, align="left", valign="middle", fill=None):
    if fill:
        pdf.setFillColor(fill)
        pdf.rect(x, y, w, h, stroke=0, fill=1)
    pdf.setStrokeColor(colors.black)
    pdf.setLineWidth(0.55)
    pdf.rect(x, y, w, h, stroke=1, fill=0)
    if text:
        pdf.setFillColor(colors.black)
        pdf.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        lines = _pdf_lines(text, max(8, int(w / (size * 0.52))))
        line_height = size + 2
        total_height = len(lines) * line_height
        if valign == "top":
            text_y = y + h - size - 4
        else:
            text_y = y + (h + total_height) / 2 - line_height + 1
        for line in lines[: max(1, int(h / line_height))]:
            if align == "center":
                pdf.drawCentredString(x + w / 2, text_y, _pdf_text(line))
            elif align == "right":
                pdf.drawRightString(x + w - 4, text_y, _pdf_text(line))
            else:
                pdf.drawString(x + 4, text_y, _pdf_text(line))
            text_y -= line_height


def _draw_pdf_label_box(pdf, label, value, x, y, label_w, value_w, h=14, label_size=8):
    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica-Bold", label_size)
    pdf.drawString(x, y + 3, _pdf_text(label))
    _draw_pdf_cell(pdf, x + label_w, y, value_w, h, value, size=8)


def _project_type_label(project):
    return project.project_type.name if project.project_type else ""


def _project_thematic_axis_label(project):
    return project.thematic_axis.name if project.thematic_axis else ""


def _requirements_value(project, keyword):
    haystack = f"{project.requirements_summary or ''} {project.required_resources or ''}".lower()
    return "X" if keyword in haystack else ""


def _project_category_label(project):
    category = Category.query.filter_by(code=project.category).first()
    return category.name if category else project.category


def _render_project_documents_packet(project: Project):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=landscape(letter))
    width, height = letter
    width, height = landscape(letter)
    today = _pdf_date(project.registration_date or date.today())
    members = sorted(project.members, key=lambda item: item.student_number)
    school_name = project.institution_name or _pdf_setting("school_name", "CTP Roberto Gamboa Valverde")
    service_type = _pdf_setting("expotec_service_type", "Tecnico profesional")
    school_phone = _pdf_setting("school_phone", "")
    school_email = _pdf_setting("school_email", "")
    director_name = _pdf_setting_any(["expotec_director_name", "director_name", "school_director_name"], "")
    director_email = _pdf_setting_any(["expotec_director_email", "director_email", "school_director_email"], "")
    coordinator_name = _pdf_setting_any(
        ["expotec_technical_coordinator_name", "technical_coordinator_name", "school_coordinator_name"],
        "",
    )
    coordinator_email = _pdf_setting_any(
        ["expotec_technical_coordinator_email", "technical_coordinator_email", "school_coordinator_email"],
        "",
    )
    course_year = _pdf_setting("expotec_school_year", "2026")
    stage = _pdf_setting("expotec_stage", "Institucional")
    start_date = _pdf_date(project.project_start_date) or _pdf_date(project.campaign.start_date if project.campaign else "")
    end_date = _pdf_date(project.project_end_date) or _pdf_date(project.campaign.end_date if project.campaign else "")

    pdf.setFillColor(colors.white)
    pdf.rect(0, 0, width, height, stroke=0, fill=1)

    def clean_section(title, y_pos):
        pdf.setFillColor(colors.HexColor("#eaf3fb"))
        pdf.roundRect(36, y_pos - 20, width - 72, 22, 7, stroke=0, fill=1)
        pdf.setFillColor(colors.HexColor("#073d70"))
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(48, y_pos - 13, _pdf_text(title))
        return y_pos - 38

    def clean_field(label, value, x, y_pos, w, h=28):
        pdf.setStrokeColor(colors.HexColor("#bfd0e2"))
        pdf.setFillColor(colors.HexColor("#ffffff"))
        pdf.roundRect(x, y_pos, w, h, 5, stroke=1, fill=1)
        pdf.setFillColor(colors.HexColor("#506a86"))
        pdf.setFont("Helvetica-Bold", 6.8)
        pdf.drawString(x + 8, y_pos + h - 10, _pdf_text(label.upper()))
        pdf.setFillColor(colors.HexColor("#0d1f33"))
        pdf.setFont("Helvetica", 8.2)
        text_y = y_pos + h - 20
        for line in _pdf_lines(value or "", max(12, int(w / 4.4)))[:2]:
            pdf.drawString(x + 8, text_y, _pdf_text(line))
            text_y -= 10

    def clean_checkbox(label, checked, x, y_pos, w=116):
        pdf.setStrokeColor(colors.HexColor("#bfd0e2"))
        pdf.setFillColor(colors.white)
        pdf.roundRect(x, y_pos, w, 22, 5, stroke=1, fill=1)
        pdf.rect(x + 8, y_pos + 6, 10, 10, stroke=1, fill=0)
        if checked:
            pdf.setFillColor(colors.HexColor("#0f7a38"))
            pdf.setFont("Helvetica-Bold", 9)
            pdf.drawCentredString(x + 13, y_pos + 6, "X")
        pdf.setFillColor(colors.HexColor("#0d1f33"))
        pdf.setFont("Helvetica", 7.8)
        pdf.drawString(x + 24, y_pos + 7, _pdf_text(label))

    # Header
    logo_y = height - 86
    school_logo = _pdf_setting("school_logo_path", "")
    expo_logo = _pdf_setting("expo_logo_path", "")
    if not _draw_pdf_logo(pdf, school_logo, 40, logo_y, max_width=118, max_height=52):
        pdf.setFillColor(colors.HexColor("#1d3461"))
        pdf.setFont("Helvetica-Bold", 8)
        pdf.drawString(44, height - 48, "MINISTERIO DE EDUCACION PUBLICA")
        pdf.drawString(44, height - 60, "GOBIERNO DE COSTA RICA")
    pdf.setFillColor(colors.HexColor("#1d3461"))
    pdf.setFont("Helvetica-Bold", 8)
    program_office = _pdf_setting("expotec_program_office", "Direccion de Educacion Tecnica y Capacidades Emprendedoras")
    for index, line in enumerate(_pdf_lines(program_office, width_chars=26)[:3]):
        pdf.drawString(168, height - 44 - (index * 11), _pdf_text(line))

    pdf.setFont("Helvetica-Bold", 17)
    pdf.setFillColor(colors.HexColor("#004b73"))
    pdf.drawCentredString(width / 2, height - 31, "ExpoTEC-1")
    pdf.setFont("Helvetica-Bold", 15)
    pdf.setFillColor(colors.HexColor("#c34d0a"))
    pdf.drawCentredString(width / 2, height - 53, "Inscripcion del Proyecto")
    pdf.setFont("Helvetica-Bold", 13)
    pdf.setFillColor(colors.HexColor("#1d7a22"))
    pdf.drawCentredString(width / 2, height - 74, f"Curso lectivo {course_year}")
    if not _draw_pdf_logo(pdf, expo_logo, width - 160, height - 92, max_width=120, max_height=72):
        pdf.setFillColor(colors.HexColor("#f37021"))
        pdf.setFont("Helvetica-Bold", 27)
        pdf.drawRightString(width - 42, height - 48, "Expo")
        pdf.setFillColor(colors.HexColor("#666666"))
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawRightString(width - 42, height - 70, "tecnica")

    pdf.setStrokeColor(colors.HexColor("#c8d6e6"))
    pdf.line(36, height - 104, width - 36, height - 104)

    y = clean_section("Datos institucionales", height - 122)
    clean_field("Etapa", stage, 42, y - 26, 150)
    clean_field("Fecha de inscripcion", today, 210, y - 26, 150)
    clean_field("Nombre del centro educativo", school_name, 378, y - 26, 372)
    y -= 58
    clean_field("Tipo de servicio educativo", service_type, 42, y, 214)
    clean_field("Telefono institucional", school_phone, 274, y, 166)
    clean_field("Correo institucional", school_email, 458, y, 292)
    y -= 48
    clean_field("Persona directora", director_name, 42, y, 276)
    clean_field("Correo persona directora", director_email, 336, y, 414)
    y -= 44
    clean_field("Persona coordinadora tecnica", coordinator_name, 42, y, 276)
    clean_field("Correo coordinacion tecnica", coordinator_email, 336, y, 414)

    y = clean_section("Datos del proyecto", y - 16)
    clean_field("Nombre del proyecto", project.title, 42, y - 26, 708)
    y -= 64
    clean_field("Categoria", _project_category_label(project), 42, y, 206)
    clean_field("Eje tematico", _project_thematic_axis_label(project), 266, y, 250)
    clean_field("Tipo de proyecto", _project_type_label(project), 534, y, 216)

    y = clean_section("Requerimientos y calendario", y - 36)
    req_y = y - 24
    clean_checkbox("Corriente", bool(_requirements_value(project, "corriente")), 42, req_y)
    clean_checkbox("Salidas", bool(_requirements_value(project, "salidas")), 170, req_y)
    clean_checkbox("Agua", bool(_requirements_value(project, "agua")), 298, req_y)
    clean_checkbox("Internet", bool(_requirements_value(project, "internet")), 426, req_y)
    clean_field("Otro requerimiento", project.requirements_other or "", 554, req_y - 4, 196, h=26)
    y = req_y - 40
    clean_field("Fecha inicio del proyecto", start_date, 42, y, 214)
    clean_field("Fecha finalizacion del proyecto", end_date, 274, y, 214)
    pdf.showPage()
    pdf.setPageSize(landscape(letter))
    width, height = landscape(letter)
    pdf.setFillColor(colors.white)
    pdf.rect(0, 0, width, height, stroke=0, fill=1)

    pdf.setFillColor(colors.HexColor("#073d70"))
    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawString(42, height - 40, "ExpoTEC-1")
    pdf.setFont("Helvetica", 9)
    pdf.setFillColor(colors.HexColor("#506a86"))
    pdf.drawString(42, height - 56, "Datos de participantes, declaracion y firmas")
    pdf.setStrokeColor(colors.HexColor("#c8d6e6"))
    pdf.line(42, height - 68, width - 42, height - 68)
    y = height - 90

    def clean_table(title, rows, y_position, max_rows=3):
        y_position = clean_section(title, y_position)
        headers = [
            ("Nombre completo", 150),
            ("Carrera tecnica", 150),
            ("Fecha nac.", 78),
            ("Sexo", 58),
            ("Cedula", 88),
            ("Telefono", 86),
            ("E-mail", 98),
        ]
        pdf.setStrokeColor(colors.HexColor("#bfd0e2"))
        pdf.setFillColor(colors.HexColor("#f3f8fd"))
        pdf.roundRect(42, y_position - 2, 708, 20, 5, stroke=1, fill=1)
        x = 42
        for label, col_w in headers:
            pdf.setFillColor(colors.HexColor("#073d70"))
            pdf.setFont("Helvetica-Bold", 7.1)
            pdf.drawCentredString(x + col_w / 2, y_position + 6, _pdf_text(label))
            if x > 42:
                pdf.setStrokeColor(colors.HexColor("#d6e2ef"))
                pdf.line(x, y_position - 2, x, y_position + 18)
            x += col_w
        y_position -= 18
        for index in range(max_rows):
            row = rows[index] if index < len(rows) else ["", "", "", "", "", "", ""]
            pdf.setStrokeColor(colors.HexColor("#d6e2ef"))
            pdf.setFillColor(colors.white)
            pdf.rect(42, y_position, 708, 16, stroke=1, fill=1)
            x = 42
            for value, (_, col_w) in zip(row, headers):
                if x > 42:
                    pdf.setStrokeColor(colors.HexColor("#d6e2ef"))
                    pdf.line(x, y_position, x, y_position + 16)
                pdf.setFillColor(colors.HexColor("#0d1f33"))
                pdf.setFont("Helvetica", 6.8)
                lines = _pdf_lines(value or "", max(8, int(col_w / 4.2)))
                pdf.drawString(x + 4, y_position + 5, _pdf_text(lines[0] if lines else ""))
                x += col_w
            y_position -= 16
        return y_position - 12

    student_rows = [
        [
            member.full_name,
            member.specialty or project.specialty or "",
            _pdf_date(member.birth_date),
            member.gender or "",
            member.identity_number or "",
            member.phone or "",
            member.email or "",
        ]
        for member in members
    ]
    y = clean_table("Datos de las personas estudiantes", student_rows, y)
    teacher_rows = [[
        project.advisor_name or "",
        project.advisor_specialty or "",
        _pdf_date(project.advisor_birth_date),
        project.advisor_gender or "",
        project.advisor_identity or "",
        project.advisor_phone or "",
        project.advisor_email or "",
    ]]
    y = clean_table("Datos de la persona docente tutor", teacher_rows, y, max_rows=1)
    mentor_rows = [[
        project.mentor_name or "",
        project.mentor_specialty or project.specialty or "",
        _pdf_date(project.mentor_birth_date),
        project.mentor_gender or "",
        project.mentor_identity or "",
        project.mentor_phone or "",
        project.mentor_email or "",
    ]]
    y = clean_table("Datos de la persona mentor", mentor_rows, y, max_rows=1)

    y = clean_section("Personas estudiantes", y)
    pdf.setFillColor(colors.HexColor("#0d1f33"))
    pdf.setFont("Helvetica-Bold", 8.2)
    pdf.drawString(42, y + 2, "Desea participar en la exposicion del proyecto con dominio linguistico en ingles con lengua extranjera?")
    y -= 22
    pdf.setStrokeColor(colors.HexColor("#bfd0e2"))
    pdf.setFillColor(colors.HexColor("#f3f8fd"))
    pdf.roundRect(42, y, 520, 22, 5, stroke=1, fill=1)
    pdf.setFillColor(colors.HexColor("#073d70"))
    pdf.setFont("Helvetica-Bold", 7.3)
    pdf.drawString(50, y + 8, "Nombre del estudiante")
    pdf.drawCentredString(278, y + 8, "Si")
    pdf.drawCentredString(326, y + 8, "No")
    pdf.drawCentredString(456, y + 8, "Firma")
    y -= 20
    for member in members[:3]:
        pdf.setStrokeColor(colors.HexColor("#d6e2ef"))
        pdf.rect(42, y, 520, 18, stroke=1, fill=0)
        pdf.line(260, y, 260, y + 18)
        pdf.line(300, y, 300, y + 18)
        pdf.line(352, y, 352, y + 18)
        pdf.setFillColor(colors.HexColor("#0d1f33"))
        pdf.setFont("Helvetica", 7)
        pdf.drawString(50, y + 6, _pdf_text(member.full_name))
        pdf.setFont("Helvetica-Bold", 8)
        pdf.drawCentredString(280, y + 5, "X" if member.participates_in_english else "")
        pdf.drawCentredString(326, y + 5, "" if member.participates_in_english else "X")
        y -= 18
    for _ in range(max(0, 3 - len(members[:3]))):
        pdf.rect(42, y, 520, 18, stroke=1, fill=0)
        pdf.line(260, y, 260, y + 18)
        pdf.line(300, y, 300, y + 18)
        pdf.line(352, y, 352, y + 18)
        y -= 18

    declaration = (
        "Declaramos bajo juramento que el proyecto inscrito en el formulario ExpoTEC-1 fue realizado por las personas "
        "estudiantes y la persona docente o especialista que los asesoro durante el proceso. El documento presentado es "
        "de autoria propia, no violenta los derechos de terceras personas. Los datos que sustentan el proyecto son "
        "verdaderos y producto de la investigacion o desarrollo. Ademas, damos fe de que este proyecto ha sido "
        "desarrollado por un maximo de tres participantes y aceptamos los lineamientos establecidos por la organizacion "
        "de la ExpoTECNICA."
    )
    y -= 14
    declaration_y = y
    y = _draw_wrapped(pdf, declaration, 42, y, width_chars=95, leading=9, size=7.2)
    pdf.setFont("Helvetica-Bold", 7.5)
    pdf.drawString(520, declaration_y, "Firma docente tutora:")
    pdf.line(520, declaration_y - 18, 740, declaration_y - 18)
    pdf.drawString(520, declaration_y - 42, "Firma persona mentor:")
    pdf.line(520, declaration_y - 60, 740, declaration_y - 60)
    y -= 12
    pdf.setFont("Helvetica-Bold", 7.5)
    pdf.drawString(42, y, "Nota:")
    pdf.setFont("Helvetica", 7.5)
    pdf.drawString(68, y, "Adjuntar las fotocopias de las cedulas del estudiantado, docente tutor y mentor.")
    pdf.showPage()

    def consent_section(title, y_pos):
        pdf.setFillColor(colors.HexColor("#eaf3fb"))
        pdf.roundRect(36, y_pos - 20, width - 72, 22, 7, stroke=0, fill=1)
        pdf.setFillColor(colors.HexColor("#073d70"))
        pdf.setFont("Helvetica-Bold", 9.5)
        pdf.drawString(48, y_pos - 13, _pdf_text(title))
        return y_pos - 34

    def consent_field(label, value, x, y_pos, w, h=29):
        pdf.setStrokeColor(colors.HexColor("#bfd0e2"))
        pdf.setFillColor(colors.white)
        pdf.roundRect(x, y_pos, w, h, 5, stroke=1, fill=1)
        pdf.setFillColor(colors.HexColor("#506a86"))
        pdf.setFont("Helvetica-Bold", 6.8)
        pdf.drawString(x + 8, y_pos + h - 10, _pdf_text(label.upper()))
        pdf.setFillColor(colors.HexColor("#0d1f33"))
        pdf.setFont("Helvetica", 8.2)
        text_y = y_pos + h - 20
        for line in _pdf_lines(value or "", max(12, int(w / 4.4)))[:2]:
            pdf.drawString(x + 8, text_y, _pdf_text(line))
            text_y -= 10

    def consent_signature_line(label, x, y_pos, w):
        pdf.setFillColor(colors.HexColor("#0d1f33"))
        pdf.setFont("Helvetica-Bold", 8)
        pdf.drawString(x, y_pos, _pdf_text(label))
        pdf.setStrokeColor(colors.HexColor("#506a86"))
        pdf.line(x + 170, y_pos, x + w, y_pos)

    def consent_check(text, x, y_pos, max_width=None):
        pdf.setStrokeColor(colors.HexColor("#bfd0e2"))
        pdf.setFillColor(colors.white)
        pdf.roundRect(x, y_pos - 2, 17, 13, 4, stroke=1, fill=1)
        pdf.setFillColor(colors.HexColor("#506a86"))
        pdf.setFont("Helvetica-Bold", 6.2)
        pdf.drawCentredString(x + 8.5, y_pos + 2, "X")
        pdf.setFillColor(colors.HexColor("#0d1f33"))
        pdf.setFont("Helvetica", 7.8)
        text_x = x + 26
        resolved_width = max_width or (width - text_x - 42)
        lines = _pdf_lines_by_width(pdf, text, resolved_width, size=7.8)
        text_y = y_pos + 7
        for line in lines:
            pdf.drawString(text_x, text_y, _pdf_text(line))
            text_y -= 9.2
        return y_pos - max(24, (len(lines) * 9.2) + 9)

    pdf.setPageSize(letter)
    width, height = letter
    for member in sorted(project.members, key=lambda item: item.student_number):
        pdf.setFillColor(colors.white)
        pdf.rect(0, 0, width, height, stroke=0, fill=1)

        logo_y = height - 88
        if not _draw_pdf_logo(pdf, school_logo, 42, logo_y, max_width=86, max_height=50):
            pdf.setFillColor(colors.HexColor("#1d3461"))
            pdf.setFont("Helvetica-Bold", 7)
            pdf.drawString(42, height - 52, "MINISTERIO DE")
            pdf.drawString(42, height - 62, "EDUCACION PUBLICA")
        pdf.setFillColor(colors.HexColor("#1d3461"))
        pdf.setFont("Helvetica-Bold", 7)
        for index, line in enumerate(_pdf_lines(program_office, width_chars=24)[:3]):
            pdf.drawString(145, height - 50 - (index * 10), _pdf_text(line))
        if not _draw_pdf_logo(pdf, expo_logo, width - 132, height - 92, max_width=88, max_height=58):
            pdf.setFillColor(colors.HexColor("#f37021"))
            pdf.setFont("Helvetica-Bold", 22)
            pdf.drawRightString(width - 42, height - 54, "Expo")
            pdf.setFillColor(colors.HexColor("#666666"))
            pdf.setFont("Helvetica-Bold", 13)
            pdf.drawRightString(width - 42, height - 73, "tecnica")

        pdf.setFillColor(colors.HexColor("#073d70"))
        pdf.setFont("Helvetica-Bold", 13)
        pdf.drawCentredString(width / 2, height - 42, "ExpoTEC-2")
        pdf.setFillColor(colors.HexColor("#c34d0a"))
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawCentredString(width / 2, height - 58, "Consentimiento Informado")
        pdf.setFillColor(colors.HexColor("#1d7a22"))
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawCentredString(width / 2, height - 73, f"Curso lectivo {course_year}")
        pdf.setStrokeColor(colors.HexColor("#c8d6e6"))
        pdf.line(42, height - 104, width - 42, height - 104)

        y = height - 128
        y = consent_section("Datos de consentimiento", y)
        pdf.setStrokeColor(colors.HexColor("#d6e2ef"))
        pdf.setFillColor(colors.HexColor("#f8fbff"))
        pdf.roundRect(42, y - 116, width - 84, 120, 7, stroke=1, fill=1)
        pdf.setFillColor(colors.HexColor("#0d1f33"))
        pdf.setFont("Helvetica", 8.4)
        _draw_wrapped(
            pdf,
            "El suscrito, en mi condicion de padre, madre o encargado legal:",
            54,
            y - 16,
            width_chars=78,
            leading=10,
            size=8.4,
        )
        consent_field("Nombre del padre, madre o encargado legal", "", 54, y - 52, 330)
        consent_field("Cedula", "", 402, y - 52, 156)
        pdf.setFont("Helvetica", 8.4)
        _draw_wrapped(
            pdf,
            "doy mi consentimiento para que la persona estudiante indicada a continuacion:",
            54,
            y - 76,
            width_chars=78,
            leading=10,
            size=8.4,
        )
        consent_field("Persona estudiante", member.full_name, 54, y - 112, 330)
        consent_field("Numero de identidad", member.identity_number or "", 402, y - 112, 156)
        y -= 138
        pdf.setFillColor(colors.HexColor("#0d1f33"))
        pdf.setFont("Helvetica", 8.4)
        pdf.drawString(42, y, "realice lo que a continuacion se detalla:")

        y -= 26
        info_text = (
            "Anuncio sin fines de lucro con mensaje dirigido al estudiantado del sistema educativo sobre la ExpoTECNICA "
            "Institucional, Regional CORVEC y Nacional. Actividad que se realiza con el aval del Ministerio de Educacion "
            "Publica y que tiene como proposito estimular en las personas estudiantes la resolucion de problemas o "
            "necesidades en un contexto especifico de la sociedad, la innovacion, ingenieria y autoaprendizaje mediante "
            "procesos que involucran la observacion, el diseno y desarrollo de prototipos, asi como la experimentacion, "
            "el analisis de informacion y la divulgacion cientifica y tecnologica."
        )
        info_lines = _pdf_lines_by_width(pdf, info_text, width - 108, font="Helvetica", size=7.8)
        info_box_height = max(50, (len(info_lines) * 9.2) + 22)
        pdf.setStrokeColor(colors.HexColor("#b9d7b1"))
        pdf.setFillColor(colors.HexColor("#eef8e9"))
        pdf.roundRect(42, y - info_box_height, width - 84, info_box_height + 4, 7, stroke=1, fill=1)
        pdf.setFillColor(colors.HexColor("#0d1f33"))
        _draw_wrapped_width(pdf, info_text, 54, y - 12, width - 108, leading=9.2, size=7.8)

        y -= info_box_height + 24
        y = consent_section("Constancias", y + 12)
        pdf.setFont("Helvetica-Bold", 8.4)
        pdf.setFillColor(colors.HexColor("#0d1f33"))
        pdf.drawString(42, y, "Para lo cual dejo constancia que:  (escriba una X sobre la linea, segun corresponda).")
        y -= 24
        y = consent_check("Recibi informacion sencilla y comprensible respecto a los beneficios y actividades que conlleva esta actividad, por parte del Ministerio de Educacion Publica.", 42, y)
        y = consent_check("Se me ha explicado este documento.", 42, y)
        y = consent_check("Libero de toda responsabilidad a los y las funcionarias que trabajaran en esta grabacion, en la medida que las imagenes no sean utilizadas para fines comerciales.", 42, y)

        pdf.setFont("Helvetica", 8)
        pdf.setFillColor(colors.HexColor("#0d1f33"))
        pdf.drawString(42, y, "Lo anterior, se respalda en los Articulos 47 y 48 del Codigo Civil que rezan:")
        y -= 18
        pdf.setFont("Helvetica-Bold", 8)
        pdf.drawString(42, y, "Articulo 47")
        y -= 10
        pdf.setFont("Helvetica", 7.3)
        y = _draw_wrapped_width(pdf, "La fotografia o la imagen de una persona no puede ser publicada, reproducida, expuesta ni vendida en forma alguna si no es con su consentimiento.", 42, y, width - 84, leading=8.4, size=7.3)
        y -= 10
        pdf.setFont("Helvetica-Bold", 8)
        pdf.drawString(42, y, "Articulo 48")
        y -= 10
        pdf.setFont("Helvetica", 7.3)
        _draw_wrapped_width(pdf, "Si la imagen o fotografia de una persona se publica sin su consentimiento y no se encuentra dentro de los casos de excepcion previstos en el articulo anterior, procede el reclamo correspondiente.", 42, y, width - 84, leading=8.4, size=7.3)

        y = 74
        consent_signature_line("Firma del padre, madre o encargado legal:", 42, y, 390)
        pdf.setFont("Helvetica-Bold", 8)
        pdf.drawString(455, y, "Fecha:")
        pdf.rect(500, y - 7, 70, 16, stroke=1, fill=0)
        pdf.showPage()

    pdf.save()
    buffer.seek(0)
    return buffer


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


def _normalize_person_gender(form_data, field_name):
    base = (form_data.get(field_name) or "").strip().lower()
    if base != "otros":
        return base
    return (form_data.get(f"{field_name}_other") or "").strip()


def _build_student(form_data, index, sections_by_id, specialties_by_id):
    section_id_raw = (form_data.get(f"student_{index}_section_id") or "").strip()
    section_id = int(section_id_raw) if section_id_raw.isdigit() else None
    section = sections_by_id.get(section_id)
    specialty_id_raw = (form_data.get(f"student_{index}_specialty_id") or "").strip()
    specialty_id = int(specialty_id_raw) if specialty_id_raw.isdigit() else None
    specialty = specialties_by_id.get(specialty_id)
    return {
        "student_number": index,
        "full_name": (form_data.get(f"student_{index}_full_name") or "").strip(),
        "identity_number": _normalize_identity(form_data.get(f"student_{index}_identity")),
        "birth_date": _parse_date(form_data.get(f"student_{index}_birth_date")),
        "gender": _normalize_gender(form_data, index),
        "specialty_id": specialty_id,
        "specialty": specialty.name if specialty else "",
        "section_name": section.name if section else "",
        "section_level_code": section.level.code if section and section.level else "",
        "has_dining_scholarship": (form_data.get(f"student_{index}_scholarship") or "").strip().lower() == "si",
        "participates_in_english": (form_data.get(f"student_{index}_english") or "").strip().lower() == "si",
        "phone": _normalize_phone(form_data.get(f"student_{index}_phone")),
        "email": (form_data.get(f"student_{index}_email") or "").strip().lower(),
    }


def _validate_students(students, required_numbers):
    by_number = {student["student_number"]: student for student in students}
    required_identities = []
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
            student["section_level_code"],
            student["specialty_id"],
            student["specialty"],
        ]
        if not all(required):
            return f"Completa todos los datos obligatorios del estudiante N.{number}."
        if student["section_level_code"] not in {"10", "11", "12"}:
            return f"La sección del estudiante N.{number} debe pertenecer a especialidad técnica (niveles 10, 11 o 12)."
        identity_error = _identity_error(student["identity_number"], f"La cedula/documento del estudiante N.{number}")
        if identity_error:
            return identity_error
        phone_error = _phone_error(student["phone"], f"El telefono del estudiante N.{number}")
        if phone_error:
            return phone_error
        email_error = _email_error(student["email"], f"El correo del estudiante N.{number}")
        if email_error:
            return email_error
        required_identities.append((number, student["identity_number"]))

    seen = {}
    for number, identity in required_identities:
        if identity in seen:
            return (
                "La cedula/documento no puede repetirse entre participantes: "
                f"estudiante N.{seen[identity]} y estudiante N.{number}."
            )
        seen[identity] = number

    normalized_db_identity = func.upper(func.replace(func.replace(ProjectMember.identity_number, "-", ""), " ", ""))
    existing_identity = (
        ProjectMember.query.filter(normalized_db_identity.in_([identity for _, identity in required_identities]))
        .with_entities(ProjectMember.identity_number)
        .scalar()
    )
    if existing_identity:
        return f"La cedula/documento {existing_identity} ya esta registrada en otro proyecto."
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
        .filter(Level.code.in_(["10", "11", "12"]))
        .order_by(Level.sort_order.asc(), Section.sort_order.asc(), Section.name.asc())
        .all()
    )
    specialties = Specialty.query.filter_by(is_active=True).order_by(Specialty.sort_order.asc()).all()
    thematic_axes = ThematicAxis.query.filter_by(is_active=True).order_by(ThematicAxis.sort_order.asc(), ThematicAxis.name.asc()).all()
    project_types = ProjectType.query.filter_by(is_active=True).order_by(ProjectType.sort_order.asc(), ProjectType.name.asc()).all()
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
        "thematic_axes": thematic_axes,
        "project_types": project_types,
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
        project_start_date = _parse_date(_draft_form_value(form_data, "project_start_date"))
        project_end_date = _parse_date(_draft_form_value(form_data, "project_end_date"))
        category = (_draft_form_value(form_data, "category") or "").strip()
        thematic_axis_id = request.form.get("thematic_axis_id", type=int)
        project_type_id = request.form.get("project_type_id", type=int)

        requirements = [item.strip().lower() for item in request.form.getlist("requirements") if item.strip()]
        requirements_other = (_draft_form_value(form_data, "requirements_other") or "").strip()
        required_students = _required_student_numbers(form_data)

        thematic_axis = ThematicAxis.query.get(thematic_axis_id) if thematic_axis_id else None
        project_type = ProjectType.query.get(project_type_id) if project_type_id else None

        sections_by_id = {
            item.id: item
            for item in Section.query.join(Level, Level.id == Section.level_id)
            .filter(Section.is_active.is_(True), Level.is_active.is_(True), Level.code.in_(["10", "11", "12"]))
            .all()
        }
        specialties_by_id = {item.id: item for item in Specialty.query.filter_by(is_active=True).all()}
        students = [_build_student(form_data, i, sections_by_id, specialties_by_id) for i in [1, 2, 3]]
        required_student_records = [student for student in students if student["student_number"] in required_students]
        project_sections_summary = ", ".join(
            sorted({student["section_name"] for student in required_student_records if student["section_name"]})
        )
        project_specialties_summary = ", ".join(
            sorted({student["specialty"] for student in required_student_records if student["specialty"]})
        )
        advisor_identity = _normalize_identity(_draft_form_value(form_data, "advisor_identity"))
        mentor_identity = _normalize_identity(_draft_form_value(form_data, "mentor_identity"))

        project = Project(
            registration_date=registration_date,
            title=(_draft_form_value(form_data, "title") or "").strip(),
            team_name=(_draft_form_value(form_data, "team_name") or "").strip() or "Equipo ExpoTEC",
            representative_name=(_draft_form_value(form_data, "student_1_full_name") or "").strip(),
            representative_email=(_draft_form_value(form_data, "student_1_email") or "").strip().lower(),
            representative_phone=_normalize_phone(_draft_form_value(form_data, "student_1_phone")),
            institution_name="CTP Roberto Gamboa Valverde",
            grade_level=project_sections_summary,
            specialty=project_specialties_summary,
            section_id=None,
            specialty_id=None,
            thematic_axis_id=thematic_axis_id,
            project_type_id=project_type_id,
            workshop_id=None,
            campaign_id=active_campaign.id,
            advisor_name=(_draft_form_value(form_data, "advisor_name") or "").strip(),
            advisor_identity=advisor_identity,
            advisor_birth_date=_parse_date(_draft_form_value(form_data, "advisor_birth_date")),
            advisor_gender=_normalize_person_gender(form_data, "advisor_gender"),
            advisor_specialty=(_draft_form_value(form_data, "advisor_specialty") or "").strip(),
            advisor_email=(_draft_form_value(form_data, "advisor_email") or "").strip().lower(),
            advisor_phone=_normalize_phone(_draft_form_value(form_data, "advisor_phone")),
            mentor_name=(_draft_form_value(form_data, "mentor_name") or "").strip(),
            mentor_identity=mentor_identity,
            mentor_birth_date=_parse_date(_draft_form_value(form_data, "mentor_birth_date")),
            mentor_gender=_normalize_person_gender(form_data, "mentor_gender"),
            mentor_specialty=(_draft_form_value(form_data, "mentor_specialty") or "").strip(),
            mentor_email=(_draft_form_value(form_data, "mentor_email") or "").strip().lower(),
            mentor_phone=_normalize_phone(_draft_form_value(form_data, "mentor_phone")),
            category=category,
            description=(_draft_form_value(form_data, "description") or "Proyecto registrado mediante ExpoTEC-1.").strip(),
            required_resources=(_draft_form_value(form_data, "required_resources") or "").strip(),
            project_start_date=project_start_date,
            project_end_date=project_end_date,
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
        if not project.project_start_date or not project.project_end_date:
            flash("Debes indicar fecha de inicio y fecha de finalizacion del proyecto.", "error")
            return render_template("public/register_project.html", **_draft_context(form_data, temp_document_path))
        if project.project_end_date < project.project_start_date:
            flash("La fecha de finalizacion no puede ser anterior a la fecha de inicio.", "error")
            return render_template("public/register_project.html", **_draft_context(form_data, temp_document_path))
        if category not in valid_categories:
            flash("Categoria invalida.", "error")
            return render_template("public/register_project.html", **_draft_context(form_data, temp_document_path))

        if category not in {"emprendimiento", "steam"}:
            flash("Categoria invalida para este formulario.", "error")
            return render_template("public/register_project.html", **_draft_context(form_data, temp_document_path))
        if not thematic_axis or not thematic_axis.is_active:
            flash("Debes seleccionar un eje tematico valido.", "error")
            return render_template("public/register_project.html", **_draft_context(form_data, temp_document_path))
        if not project_type or not project_type.is_active:
            flash("Debes seleccionar un tipo de proyecto valido.", "error")
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

        if not all([
            project.advisor_name,
            project.advisor_identity,
            project.advisor_birth_date,
            project.advisor_gender,
            project.advisor_specialty,
            project.advisor_phone,
            project.advisor_email,
        ]):
            flash("Completa los datos del docente tutor.", "error")
            return render_template("public/register_project.html", **_draft_context(form_data, temp_document_path))
        advisor_identity_error = _identity_error(project.advisor_identity, "La cedula/documento del docente")
        if advisor_identity_error:
            flash(advisor_identity_error, "error")
            return render_template("public/register_project.html", **_draft_context(form_data, temp_document_path))
        advisor_phone_error = _phone_error(project.advisor_phone, "El telefono del docente")
        if advisor_phone_error:
            flash(advisor_phone_error, "error")
            return render_template("public/register_project.html", **_draft_context(form_data, temp_document_path))
        advisor_email_error = _email_error(project.advisor_email, "El correo del docente")
        if advisor_email_error:
            flash(advisor_email_error, "error")
            return render_template("public/register_project.html", **_draft_context(form_data, temp_document_path))
        if project.mentor_identity:
            mentor_identity_error = _identity_error(project.mentor_identity, "La cedula/documento de la persona mentora")
            if mentor_identity_error:
                flash(mentor_identity_error, "error")
                return render_template("public/register_project.html", **_draft_context(form_data, temp_document_path))
        mentor_values = [
            project.mentor_name,
            project.mentor_identity,
            project.mentor_birth_date,
            project.mentor_gender,
            project.mentor_specialty,
            project.mentor_phone,
            project.mentor_email,
        ]
        if any(mentor_values) and not all(mentor_values):
            flash("Si agregas persona mentora, completa todos sus datos.", "error")
            return render_template("public/register_project.html", **_draft_context(form_data, temp_document_path))
        if project.mentor_phone:
            mentor_phone_error = _phone_error(project.mentor_phone, "El telefono de la persona mentora")
            if mentor_phone_error:
                flash(mentor_phone_error, "error")
                return render_template("public/register_project.html", **_draft_context(form_data, temp_document_path))
        mentor_email_error = _email_error(project.mentor_email, "El correo de la persona mentora", required=False)
        if mentor_email_error:
            flash(mentor_email_error, "error")
            return render_template("public/register_project.html", **_draft_context(form_data, temp_document_path))

        if not project.consent_terms:
            flash("Debes aceptar la declaracion para finalizar la inscripcion.", "error")
            return render_template("public/register_project.html", **_draft_context(form_data, temp_document_path))

        try:
            project.project_document_path = _promote_temp_project_document(temp_document_path)
            project.logistics_document_ok = True
        except ValueError as error:
            flash(str(error), "error")
            return render_template("public/register_project.html", **_draft_context(form_data, temp_document_path))

        db.session.add(project)
        db.session.flush()
        for number in required_students:
            student = next(item for item in students if item["student_number"] == number)
            student_payload = {key: value for key, value in student.items() if key != "section_level_code"}
            db.session.add(ProjectMember(project_id=project.id, **student_payload))

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
        return redirect(url_for("public.project_documents", project_id=project.id))

    return render_template("public/register_project.html", **_draft_context())


def project_documents(project_id: int):
    project = (
        Project.query.options(
            joinedload(Project.members),
            joinedload(Project.section),
            joinedload(Project.specialty_ref),
            joinedload(Project.thematic_axis),
            joinedload(Project.project_type),
            joinedload(Project.workshop_ref),
        )
        .filter(Project.id == project_id)
        .first_or_404()
    )
    return render_template("public/project_documents.html", project=project)


def project_documents_packet(project_id: int):
    project = (
        Project.query.options(
            joinedload(Project.members),
            joinedload(Project.section),
            joinedload(Project.specialty_ref),
            joinedload(Project.thematic_axis),
            joinedload(Project.project_type),
            joinedload(Project.workshop_ref),
        )
        .filter(Project.id == project_id)
        .first_or_404()
    )
    if not REPORTLAB_AVAILABLE:
        flash("No se pudo generar PDF. Instala reportlab en el entorno.", "error")
        return redirect(url_for("public.project_documents", project_id=project.id))
    pdf_bytes = _render_project_documents_packet(project)
    safe_title = "".join(char for char in project.title.lower().replace(" ", "_") if char.isalnum() or char in {"_", "-"})
    return send_file(
        pdf_bytes,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"expotec_documentos_{project.id}_{safe_title or 'proyecto'}.pdf",
    )


def search_project_for_forms():
    query = (request.args.get("q") or "").strip()
    results = []
    searched = False

    if query and len(query) >= 3:
        searched = True
        normalized = re.sub(r"[\s\-]+", "", query).upper()

        members_by_identity = (
            ProjectMember.query
            .options(joinedload(ProjectMember.project).joinedload(Project.members))
            .filter(
                func.upper(func.replace(func.replace(ProjectMember.identity_number, "-", ""), " ", "")) == normalized
            )
            .all()
        )
        members_by_name = (
            ProjectMember.query
            .options(joinedload(ProjectMember.project).joinedload(Project.members))
            .filter(ProjectMember.full_name.ilike(f"%{query}%"))
            .all()
        )
        all_project_ids = {m.project_id for m in members_by_identity} | {m.project_id for m in members_by_name}

        if all_project_ids:
            projects = (
                Project.query
                .options(joinedload(Project.members))
                .filter(Project.id.in_(all_project_ids), Project.is_active.is_(True))
                .order_by(Project.title.asc())
                .all()
            )
            for project in projects:
                matching_members = [
                    m for m in project.members
                    if (
                        re.sub(r"[\s\-]+", "", m.identity_number or "").upper() == normalized
                        or query.lower() in (m.full_name or "").lower()
                    )
                ]
                results.append({"project": project, "matching_members": matching_members})

    return render_template(
        "public/search_project_forms.html",
        query=query,
        results=results,
        searched=searched,
    )


def search_project_for_revision():
    query = (request.args.get("q") or "").strip()
    results = []
    searched = False

    if query and len(query) >= 3:
        searched = True
        normalized = re.sub(r"[\s\-]+", "", query).upper()

        members_by_identity = (
            ProjectMember.query
            .options(joinedload(ProjectMember.project).joinedload(Project.members))
            .filter(
                func.upper(func.replace(func.replace(ProjectMember.identity_number, "-", ""), " ", "")) == normalized
            )
            .all()
        )
        project_ids_from_identity = {m.project_id for m in members_by_identity}

        members_by_name = (
            ProjectMember.query
            .options(joinedload(ProjectMember.project).joinedload(Project.members))
            .filter(ProjectMember.full_name.ilike(f"%{query}%"))
            .all()
        )
        project_ids_from_name = {m.project_id for m in members_by_name}

        all_project_ids = project_ids_from_identity | project_ids_from_name

        if all_project_ids:
            projects = (
                Project.query
                .options(joinedload(Project.members))
                .filter(Project.id.in_(all_project_ids), Project.is_active.is_(True))
                .order_by(Project.title.asc())
                .all()
            )
            pending_ids = {
                r.project_id
                for r in ProjectDocumentRevision.query
                .filter(
                    ProjectDocumentRevision.project_id.in_(all_project_ids),
                    ProjectDocumentRevision.status == ProjectDocumentRevision.STATUS_PENDING,
                )
                .all()
            }
            for project in projects:
                matching_members = [
                    m for m in project.members
                    if (
                        re.sub(r"[\s\-]+", "", m.identity_number or "").upper() == normalized
                        or query.lower() in (m.full_name or "").lower()
                    )
                ]
                results.append({
                    "project": project,
                    "matching_members": matching_members,
                    "has_pending_revision": project.id in pending_ids,
                })

    return render_template(
        "public/search_project_revision.html",
        query=query,
        results=results,
        searched=searched,
    )


def submit_document_revision(project_id: int):
    project = (
        Project.query.options(joinedload(Project.members))
        .filter(Project.id == project_id)
        .first_or_404()
    )

    if not project.is_active:
        flash("Este proyecto no está activo.", "error")
        return redirect(url_for("public.project_documents", project_id=project_id))

    pending_revision = ProjectDocumentRevision.query.filter_by(
        project_id=project.id, status=ProjectDocumentRevision.STATUS_PENDING
    ).first()

    if request.method == "POST":
        submitted_by_name = (request.form.get("submitted_by_name") or "").strip()
        justification = (request.form.get("justification") or "").strip()
        document_file = request.files.get("project_document")

        errors = []
        if not submitted_by_name:
            errors.append("Debes seleccionar o indicar tu nombre.")
        if not justification or len(justification) < 10:
            errors.append("La justificación debe tener al menos 10 caracteres.")
        if not document_file or not document_file.filename:
            errors.append("Debes adjuntar el nuevo documento PDF.")
        if pending_revision:
            errors.append("Ya existe una solicitud pendiente de revisión para este proyecto. Espera a que sea procesada antes de enviar otra.")

        doc_path = None
        if not errors:
            try:
                doc_path = _save_revision_document(document_file)
            except ValueError as err:
                errors.append(str(err))

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template(
                "public/project_document_revision.html",
                project=project,
                pending_revision=pending_revision,
            )

        revision = ProjectDocumentRevision(
            project_id=project.id,
            document_path=doc_path,
            justification=justification,
            submitted_by_name=submitted_by_name,
            status=ProjectDocumentRevision.STATUS_PENDING,
        )
        db.session.add(revision)
        log_event(
            "public.project.document_revision.submit",
            "project",
            entity_id=project.id,
            detail=(
                f"Solicitud de revision de documento enviada para proyecto #{project.id} "
                f"'{project.title}' por '{submitted_by_name}'"
            ),
        )
        db.session.commit()
        if smtp_is_configured() and project.representative_email:
            _send_request_received_email(
                to_email=project.representative_email,
                requester_name=submitted_by_name,
                project_title=project.title,
                request_type="actualización de documento",
                detail=f"Justificación: {justification}",
            )
        flash("Solicitud enviada. La organización revisará tu documento actualizado y te notificará si es aprobado.", "success")
        return redirect(url_for("public.project_documents", project_id=project_id))

    return render_template(
        "public/project_document_revision.html",
        project=project,
        pending_revision=pending_revision,
    )


def _send_request_received_email(*, to_email: str, requester_name: str, project_title: str, request_type: str, detail: str):
    subject = f"Solicitud recibida: {request_type} – ExpoTécnica"
    plain = (
        f"Hola {requester_name},\n\n"
        f"Tu solicitud de {request_type} para el proyecto «{project_title}» fue recibida exitosamente.\n"
        f"{detail}\n\n"
        "La organización de ExpoTécnica revisará tu solicitud y recibirás una notificación con el resultado.\n\n"
        "ExpoTécnica"
    )
    html = f"""\
<!doctype html><html lang="es"><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#eef5fb;font-family:Arial,Helvetica,sans-serif;color:#123f6b;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#eef5fb;padding:28px 12px;">
    <tr><td align="center">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:620px;background:#fff;border:1px solid #cfe0f1;border-radius:18px;overflow:hidden;">
        <tr><td style="background:#123f6b;padding:20px 26px;color:#fff;font-size:20px;font-weight:800;">ExpoTécnica — Solicitud recibida</td></tr>
        <tr><td style="padding:28px 26px;">
          <p style="margin:0 0 10px;font-size:16px;">Hola <strong>{requester_name}</strong>,</p>
          <p style="margin:0 0 16px;font-size:15px;line-height:1.6;">Tu solicitud de <strong>{request_type}</strong> para el proyecto <strong>«{project_title}»</strong> fue recibida exitosamente.</p>
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f8fd;border:1px solid #d6e7f7;border-radius:12px;margin:0 0 18px;">
            <tr><td style="padding:14px 18px;font-size:14px;color:#3a5a7a;">{detail}</td></tr>
          </table>
          <p style="margin:0;font-size:14px;color:#607998;">La organización revisará tu solicitud y recibirás un correo con el resultado.</p>
        </td></tr>
        <tr><td style="background:#f0f6fd;padding:14px 26px;font-size:12px;color:#8aaecc;border-top:1px solid #ddeaf7;">ExpoTécnica — Sistema de gestión de proyectos</td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""
    send_email(to_email, subject, plain, html_body=html)


def _send_request_decision_email(*, to_email: str, requester_name: str, project_title: str, request_type: str, approved: bool, notes: str = ""):
    estado = "aprobada" if approved else "rechazada"
    color = "#1d7a22" if approved else "#b01c1c"
    subject = f"Solicitud {estado}: {request_type} – ExpoTécnica"
    plain = (
        f"Hola {requester_name},\n\n"
        f"Tu solicitud de {request_type} para el proyecto «{project_title}» fue {estado}.\n"
        + (f"Observaciones: {notes}\n" if notes else "")
        + "\nExpoTécnica"
    )
    notes_block = f'<p style="margin:12px 0 0;font-size:14px;color:#3a5a7a;"><strong>Observaciones:</strong> {notes}</p>' if notes else ""
    html = f"""\
<!doctype html><html lang="es"><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#eef5fb;font-family:Arial,Helvetica,sans-serif;color:#123f6b;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#eef5fb;padding:28px 12px;">
    <tr><td align="center">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:620px;background:#fff;border:1px solid #cfe0f1;border-radius:18px;overflow:hidden;">
        <tr><td style="background:{color};padding:20px 26px;color:#fff;font-size:20px;font-weight:800;">ExpoTécnica — Solicitud {estado}</td></tr>
        <tr><td style="padding:28px 26px;">
          <p style="margin:0 0 10px;font-size:16px;">Hola <strong>{requester_name}</strong>,</p>
          <p style="margin:0 0 16px;font-size:15px;line-height:1.6;">Tu solicitud de <strong>{request_type}</strong> para el proyecto <strong>«{project_title}»</strong> fue <strong style="color:{color};">{estado}</strong>.</p>
          {notes_block}
        </td></tr>
        <tr><td style="background:#f0f6fd;padding:14px 26px;font-size:12px;color:#8aaecc;border-top:1px solid #ddeaf7;">ExpoTécnica — Sistema de gestión de proyectos</td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""
    send_email(to_email, subject, plain, html_body=html)


def _save_revision_document(document_file):
    original_name = secure_filename(document_file.filename or "")
    extension = _get_extension(original_name)
    if extension not in ALLOWED_DOC_EXTENSIONS:
        raise ValueError("Formato invalido. El documento debe ser PDF.")

    relative_dir = os.path.join("uploads", "projects", "revisions")
    absolute_dir = os.path.join(current_app.static_folder, relative_dir)
    os.makedirs(absolute_dir, exist_ok=True)

    unique_name = f"{uuid.uuid4().hex}.{extension}"
    absolute_path = os.path.join(absolute_dir, unique_name)
    document_file.save(absolute_path)
    return f"{relative_dir}/{unique_name}".replace("\\", "/")


def evaluate_project_entry(project_id: int):
    project = Project.query.get_or_404(project_id)
    if not project.is_active:
        flash("Este proyecto esta inactivo.", "error")
        return redirect(url_for("public.index"))

    if not current_user.is_authenticated:
        return redirect(url_for("auth.login", next=url_for("public.evaluate_project_entry", project_id=project.id)))

    if getattr(current_user, "has_admin_access", False):
        return redirect(url_for("admin.projects_page"))

    assignment = Assignment.query.filter_by(
        judge_id=current_user.id,
        project_id=project.id,
        status=Assignment.STATUS_CONFIRMED,
    ).first()
    if not assignment:
        flash("No tienes este proyecto asignado para evaluacion.", "error")
        return redirect(url_for("judge.dashboard"))

    evaluation_types = get_active_evaluation_types()
    if not evaluation_types:
        flash("No hay tipos de evaluacion configurados.", "error")
        return redirect(url_for("judge.dashboard"))

    selected = next((item for item in evaluation_types if item.code == "escrito"), evaluation_types[0])
    return redirect(url_for("judge.evaluate", project_id=project.id, type=selected.code))


def search_project_for_member_edit():
    query = (request.args.get("q") or "").strip()
    results = []
    searched = False

    if query and len(query) >= 3:
        searched = True
        normalized = re.sub(r"[\s\-]+", "", query).upper()

        members_by_identity = (
            ProjectMember.query
            .options(joinedload(ProjectMember.project).joinedload(Project.members))
            .filter(
                func.upper(func.replace(func.replace(ProjectMember.identity_number, "-", ""), " ", "")) == normalized
            )
            .all()
        )
        members_by_name = (
            ProjectMember.query
            .options(joinedload(ProjectMember.project).joinedload(Project.members))
            .filter(ProjectMember.full_name.ilike(f"%{query}%"))
            .all()
        )
        all_project_ids = {m.project_id for m in members_by_identity} | {m.project_id for m in members_by_name}

        if all_project_ids:
            projects = (
                Project.query
                .options(joinedload(Project.members))
                .filter(Project.id.in_(all_project_ids), Project.is_active.is_(True))
                .order_by(Project.title.asc())
                .all()
            )
            # fetch pending edit requests per member
            pending_member_ids = {
                r.member_id
                for r in ProjectMemberEditRequest.query
                .filter(
                    ProjectMemberEditRequest.project_id.in_(all_project_ids),
                    ProjectMemberEditRequest.status == ProjectMemberEditRequest.STATUS_PENDING,
                )
                .all()
            }
            for project in projects:
                matching_members = [
                    m for m in project.members
                    if (
                        re.sub(r"[\s\-]+", "", m.identity_number or "").upper() == normalized
                        or query.lower() in (m.full_name or "").lower()
                    )
                ]
                results.append({
                    "project": project,
                    "matching_members": matching_members,
                    "pending_member_ids": pending_member_ids,
                })

    return render_template(
        "public/search_member_edit.html",
        query=query,
        results=results,
        searched=searched,
    )


def submit_member_edit(project_id: int, member_id: int):
    import json as _json
    project = (
        Project.query.options(joinedload(Project.members))
        .filter(Project.id == project_id)
        .first_or_404()
    )
    member = next((m for m in project.members if m.id == member_id), None)
    if not member:
        flash("Integrante no encontrado.", "error")
        return redirect(url_for("public.project_documents", project_id=project_id))

    if not project.is_active:
        flash("Este proyecto no está activo.", "error")
        return redirect(url_for("public.project_documents", project_id=project_id))

    pending = ProjectMemberEditRequest.query.filter_by(
        member_id=member_id,
        status=ProjectMemberEditRequest.STATUS_PENDING,
    ).first()

    past_requests = (
        ProjectMemberEditRequest.query
        .filter_by(member_id=member_id)
        .order_by(ProjectMemberEditRequest.created_at.desc())
        .limit(5)
        .all()
    )

    if request.method == "POST":
        if pending:
            flash("Ya existe una solicitud pendiente para este integrante. Espera a que sea procesada.", "error")
            return redirect(url_for("public.project_member_edit", project_id=project_id, member_id=member_id))

        justification = (request.form.get("justification") or "").strip()
        new_vals = {
            "full_name":               (request.form.get("full_name") or "").strip(),
            "identity_number":         (request.form.get("identity_number") or "").strip(),
            "birth_date":              (request.form.get("birth_date") or "").strip(),
            "gender":                  (request.form.get("gender") or "").strip(),
            "specialty":               (request.form.get("specialty") or "").strip(),
            "section_name":            (request.form.get("section_name") or "").strip(),
            "has_dining_scholarship":  "1" in request.form.getlist("has_dining_scholarship"),
            "participates_in_english": "1" in request.form.getlist("participates_in_english"),
            "phone":                   (request.form.get("phone") or "").strip(),
            "email":                   (request.form.get("email") or "").strip(),
            "role":                    (request.form.get("role") or "").strip(),
        }

        snapshot = {
            "full_name":               member.full_name or "",
            "identity_number":         member.identity_number or "",
            "birth_date":              str(member.birth_date) if member.birth_date else "",
            "gender":                  member.gender or "",
            "specialty":               member.specialty or "",
            "section_name":            member.section_name or "",
            "has_dining_scholarship":  bool(member.has_dining_scholarship),
            "participates_in_english": bool(member.participates_in_english),
            "phone":                   member.phone or "",
            "email":                   member.email or "",
            "role":                    member.role or "",
        }

        errors = []
        if not new_vals["full_name"]:
            errors.append("El nombre completo es obligatorio.")
        if not justification or len(justification) < 10:
            errors.append("Debes indicar el motivo del cambio (mínimo 10 caracteres).")
        if new_vals == snapshot:
            errors.append("No se detectó ningún cambio en los datos. Modifica al menos un campo antes de enviar la solicitud.")
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("public/project_member_edit.html", project=project, member=member,
                                   pending=pending, past_requests=past_requests)

        edit_req = ProjectMemberEditRequest(
            project_id=project_id,
            member_id=member_id,
            submitted_by_name=new_vals["full_name"],
            justification=justification,
            changes_json=_json.dumps(new_vals, ensure_ascii=False),
            snapshot_json=_json.dumps(snapshot, ensure_ascii=False),
            status=ProjectMemberEditRequest.STATUS_PENDING,
        )
        db.session.add(edit_req)
        log_event(
            "public.project.member_edit.submit",
            "project_member",
            entity_id=member_id,
            detail=f"Solicitud de edición de datos enviada para integrante '{member.full_name}' del proyecto #{project_id}",
        )
        db.session.commit()
        recipient = member.email or project.representative_email
        if smtp_is_configured() and recipient:
            _send_request_received_email(
                to_email=recipient,
                requester_name=new_vals["full_name"],
                project_title=project.title,
                request_type="actualización de datos de integrante",
                detail=f"Integrante: {member.full_name}. Motivo: {justification}",
            )
        flash("Solicitud enviada. La organización revisará los cambios y te notificará si son aprobados.", "success")
        return redirect(url_for("public.project_documents", project_id=project_id))

    return render_template(
        "public/project_member_edit.html",
        project=project,
        member=member,
        pending=pending,
        past_requests=past_requests,
    )


def judge_attendance_confirm(token: str):
    from datetime import datetime as _dt
    judge = Judge.query.filter_by(attendance_token=token).first()
    if not judge:
        return render_template("public/attendance_invalid.html"), 404

    already_responded = judge.attendance_confirmed is not None

    if request.method == "POST":
        confirmed = request.form.get("attendance") == "yes"
        needs_parking = request.form.get("needs_parking") == "1"
        evaluation_scope = (request.form.get("evaluation_scope") or "ambas").strip().lower()
        category_scope = (request.form.get("category_scope") or "ambas").strip().lower()
        can_evaluate_english = request.form.get("can_evaluate_english") == "1"

        if category_scope not in {"steam", "emprendimiento", "ambas"}:
            category_scope = "ambas"
        if evaluation_scope == "documento":
            can_evaluate_documentation = True
            can_evaluate_exposition = False
        elif evaluation_scope == "exposicion":
            can_evaluate_documentation = False
            can_evaluate_exposition = True
        else:
            can_evaluate_documentation = True
            can_evaluate_exposition = True

        judge.job_title = (request.form.get("job_title") or "").strip()
        judge.institution = (request.form.get("institution") or "").strip()
        judge.phone = (request.form.get("phone") or "").strip()
        judge.category_scope = category_scope
        judge.can_evaluate_documentation = can_evaluate_documentation
        judge.can_evaluate_exposition = can_evaluate_exposition
        judge.can_evaluate_english = can_evaluate_english
        judge.attendance_confirmed = confirmed
        judge.needs_parking = needs_parking
        judge.attendance_responded_at = _dt.utcnow()
        if not confirmed:
            judge.is_active_user = False
        else:
            judge.is_active_user = True
        log_event(
            "judge.attendance.confirm",
            "judge",
            entity_id=judge.id,
            detail=(
                f"Asistencia={'si' if confirmed else 'no'}, categoria={judge.category_scope}, "
                f"documento={judge.can_evaluate_documentation}, exposicion={judge.can_evaluate_exposition}, "
                f"ingles={judge.can_evaluate_english}"
            ),
        )
        db.session.commit()
        return render_template(
            "public/attendance_thanks.html",
            judge=judge,
            confirmed=confirmed,
            needs_parking=needs_parking,
        )

    return render_template(
        "public/attendance_confirm.html",
        judge=judge,
        already_responded=already_responded,
    )
