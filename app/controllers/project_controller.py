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
from app.models.project_member import ProjectMember
from app.models.assignment import Assignment
from app.models.section import Section
from app.models.specialty import Specialty
from app.models.system_setting import SystemSetting
from app.services.audit_service import log_event
from app.services.parameter_service import get_active_evaluation_types

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False

ALLOWED_DOC_EXTENSIONS = {"pdf", "doc", "docx", "ppt", "pptx", "zip", "rar"}
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
    return "Especialidad tecnica"


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
    director_name = _pdf_setting("expotec_director_name", "")
    director_email = _pdf_setting("expotec_director_email", "")
    coordinator_name = _pdf_setting("expotec_technical_coordinator_name", "")
    coordinator_email = _pdf_setting("expotec_technical_coordinator_email", "")
    course_year = _pdf_setting("expotec_school_year", "2026")
    stage = _pdf_setting("expotec_stage", "Institucional")
    start_date = _pdf_date(project.project_start_date) or _pdf_date(_pdf_setting("expotec_project_start_date", _pdf_date(project.campaign.start_date) if project.campaign else ""))
    end_date = _pdf_date(project.project_end_date) or _pdf_date(_pdf_setting("expotec_project_end_date", _pdf_date(project.campaign.end_date) if project.campaign else ""))

    _draw_excel_background(pdf, width, height)

    # Header
    logo_y = height - 78
    school_logo = _pdf_setting("school_logo_path", "")
    expo_logo = _pdf_setting("expo_logo_path", "")
    if not _draw_pdf_logo(pdf, school_logo, 18, logo_y, max_width=110, max_height=42):
        pdf.setFillColor(colors.HexColor("#1d3461"))
        pdf.setFont("Helvetica-Bold", 8)
        pdf.drawString(18, height - 42, "MINISTERIO DE")
        pdf.drawString(18, height - 53, "EDUCACION PUBLICA")
        pdf.drawString(96, height - 42, "GOBIERNO")
        pdf.drawString(96, height - 53, "DE COSTA RICA")
    pdf.setStrokeColor(colors.HexColor("#7f8ca3"))
    pdf.line(132, height - 25, 122, height - 76)
    pdf.setFillColor(colors.HexColor("#1d3461"))
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(142, height - 34, _pdf_setting("expotec_program_office", "Direccion de Educacion"))
    pdf.drawString(142, height - 48, "Tecnica y Capacidades")
    pdf.drawString(142, height - 62, "Emprendedoras")

    pdf.setFont("Helvetica-Bold", 15)
    pdf.setFillColor(colors.HexColor("#004b73"))
    pdf.drawCentredString(width / 2, height - 23, "ExpoTEC-1")
    pdf.setFont("Helvetica-Bold", 14)
    pdf.setFillColor(colors.HexColor("#c34d0a"))
    pdf.drawCentredString(width / 2, height - 43, "Inscripcion del Proyecto")
    pdf.setFont("Helvetica-Bold", 13)
    pdf.setFillColor(colors.HexColor("#1d7a22"))
    pdf.drawCentredString(width / 2, height - 63, f"Curso lectivo {course_year}")
    if not _draw_pdf_logo(pdf, expo_logo, width - 150, height - 84, max_width=110, max_height=70):
        pdf.setFillColor(colors.HexColor("#f37021"))
        pdf.setFont("Helvetica-Bold", 27)
        pdf.drawRightString(width - 42, height - 45, "Expo")
        pdf.setFillColor(colors.HexColor("#666666"))
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawRightString(width - 42, height - 67, "tecnica")

    y = height - 102
    _draw_pdf_label_box(pdf, "Etapa:", stage, 0, y, 64, 98, h=13)
    _draw_pdf_label_box(pdf, "Fecha de inscripcion:", today, 248, y, 106, 148, h=13)
    y -= 24
    _draw_pdf_label_box(pdf, "Nombre del centro educativo:", school_name, 0, y, 162, 338, h=13)
    y -= 24
    _draw_pdf_label_box(pdf, "Tipo de servicio educativo:", service_type, 0, y, 162, 338, h=13)
    y -= 24
    _draw_pdf_label_box(pdf, "Telefono institucional:", school_phone, 0, y, 162, 125, h=13)
    _draw_pdf_label_box(pdf, "Correo institucional:", school_email, 314, y, 96, 210, h=13)
    y -= 24
    _draw_pdf_label_box(pdf, "Persona directora:", director_name, 0, y, 114, 174, h=13)
    _draw_pdf_label_box(pdf, "Correo electronico:", director_email, 314, y, 96, 210, h=13)
    y -= 24
    _draw_pdf_label_box(pdf, "Persona coordinadora tecnica:", coordinator_name, 0, y, 162, 190, h=13)
    _draw_pdf_label_box(pdf, "Correo electronico:", coordinator_email, 404, y, 96, 248, h=13)
    y -= 24
    _draw_pdf_label_box(pdf, "Nombre del proyecto:", project.title, 0, y, 114, 632, h=13)
    y -= 24
    _draw_pdf_label_box(pdf, "Categoria:", _project_category_label(project), 0, y, 64, 224, h=13)
    _draw_pdf_label_box(pdf, "Eje tematico:", project.specialty or (project.specialty_ref.name if project.specialty_ref else ""), 344, y, 96, 210, h=13)
    y -= 24
    _draw_pdf_label_box(pdf, "Tipo de proyecto:", _project_type_label(project), 0, y, 114, 240, h=13)
    y -= 24

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(0, y + 3, "Requerimientos del proyecto:  (escriba una X en la respectiva casilla, si corresponde)")
    y -= 17
    requirement_rows = [
        ("Voltaje (no sistema trifasico)", _requirements_value(project, "corriente")),
        ("Salidas", _requirements_value(project, "salidas")),
        ("Agua", _requirements_value(project, "agua")),
        ("Internet", _requirements_value(project, "internet")),
        ("Otro:", project.requirements_other or ""),
    ]
    for label, value in requirement_rows:
        pdf.setFont("Helvetica", 8)
        pdf.drawString(2, y + 3, _pdf_text(label))
        _draw_pdf_cell(pdf, 166, y, 50 if label != "Otro:" else 345, 13, value, size=8)
        y -= 13
    y -= 12
    _draw_pdf_label_box(pdf, "Fecha inicio del proyecto:", start_date, 2, y, 162, 190, h=13)
    y -= 24
    _draw_pdf_label_box(pdf, "Fecha finalizacion del proyecto:", end_date, 2, y, 162, 190, h=13)
    pdf.showPage()
    pdf.setPageSize(landscape(letter))
    width, height = landscape(letter)
    _draw_excel_background(pdf, width, height)
    y = height - 38

    def draw_people_table(title, rows, y_position, max_rows=3):
        pdf.setFillColor(colors.black)
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(2, y_position + 3, _pdf_text(title))
        y_position -= 16
        headers = [
            ("Nombre completo", 116),
            ("Carrera tecnica", 174),
            ("Fecha de\nnacimiento", 66),
            ("Sexo", 56),
            ("Cedula", 90),
            ("Telefono", 120),
            ("E-mail", 128),
        ]
        x = 2
        for label, col_w in headers:
            _draw_pdf_cell(pdf, x, y_position, col_w, 25, label, bold=True, size=8, align="center")
            x += col_w
        y_position -= 25
        for index in range(max_rows):
            row = rows[index] if index < len(rows) else ["", "", "", "", "", "", ""]
            x = 2
            for value, (_, col_w) in zip(row, headers):
                _draw_pdf_cell(pdf, x, y_position, col_w, 13, value, size=6.8)
                x += col_w
            y_position -= 13
        return y_position - 14

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
    y = draw_people_table("Datos de las personas estudiantes:", student_rows, y)
    teacher_rows = [[
        project.advisor_name or "",
        project.specialty or "",
        _pdf_date(project.advisor_birth_date),
        project.advisor_gender or "",
        project.advisor_identity or "",
        project.advisor_phone or "",
        project.advisor_email or "",
    ]]
    y = draw_people_table("Datos de la persona docente tutor:", teacher_rows, y, max_rows=1)
    mentor_rows = [[
        project.mentor_name or "",
        project.mentor_specialty or project.specialty or "",
        _pdf_date(project.mentor_birth_date),
        project.mentor_gender or "",
        project.mentor_identity or "",
        project.mentor_phone or "",
        project.mentor_email or "",
    ]]
    y = draw_people_table("Datos de la persona mentor:", mentor_rows, y, max_rows=1)

    pdf.setFillColor(colors.red)
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(2, y + 4, "Personas estudiantes")
    y -= 17
    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica-Bold", 8.5)
    pdf.drawString(2, y + 5, "¿Desea participar en la exposicion del proyecto con dominio linguistico en ingles con lengua extranjera?")
    y -= 15
    _draw_pdf_cell(pdf, 2, y, 166, 13, "Nombre del estudiante", bold=True, size=8, align="center")
    _draw_pdf_cell(pdf, 168, y, 50, 13, "Si", bold=True, size=8, align="center")
    _draw_pdf_cell(pdf, 218, y, 76, 13, "No", bold=True, size=8, align="center")
    y -= 13
    for member in members[:3]:
        _draw_pdf_cell(pdf, 2, y, 166, 13, member.full_name, size=7)
        _draw_pdf_cell(pdf, 168, y, 50, 13, "X" if member.participates_in_english else "", size=8, align="center")
        _draw_pdf_cell(pdf, 218, y, 76, 13, "" if member.participates_in_english else "X", size=8, align="center")
        y -= 13
    for _ in range(max(0, 3 - len(members[:3]))):
        _draw_pdf_cell(pdf, 2, y, 166, 13, "", size=7)
        _draw_pdf_cell(pdf, 168, y, 50, 13, "", size=8)
        _draw_pdf_cell(pdf, 218, y, 76, 13, "", size=8)
        y -= 13
    y -= 14
    declaration = (
        "Declaramos bajo juramento que el proyecto inscrito en el formulario ExpoTEC-1 fue realizado por las personas "
        "estudiantes y la persona docente o especialista que los asesoro durante el proceso. El documento presentado es "
        "de autoria propia, no violenta los derechos de terceras personas. Los datos que sustentan el proyecto son "
        "verdaderos y producto de la investigacion o desarrollo. Ademas, damos fe de que este proyecto ha sido "
        "desarrollado por un maximo de tres participantes y aceptamos los lineamientos establecidos por la organizacion "
        "de la ExpoTECNICA."
    )
    y = _draw_wrapped(pdf, declaration, 2, y, width_chars=150, leading=10, size=8)
    y -= 10
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(2, y, "Firmas de las personas estudiantes:")
    y -= 26
    pdf.line(2, y, 220, y)
    pdf.line(294, y, 510, y)
    y -= 24
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(2, y, "Firma de la persona docente tutora:")
    pdf.line(178, y, 345, y)
    y -= 24
    pdf.drawString(2, y, "Firma de la persona mentor:")
    pdf.line(148, y, 315, y)
    y -= 20
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(2, y, "Nota:")
    pdf.setFont("Helvetica", 8)
    pdf.drawString(30, y, "Adjuntar las fotocopias de las cedulas del estudiantado, docente tutor y mentor.")
    pdf.showPage()

    pdf.setPageSize(letter)
    width, height = letter
    for member in sorted(project.members, key=lambda item: item.student_number):
        y = _draw_document_header(pdf, "ExpoTEC-2 - Consentimiento Informado")
        intro = (
            "El suscrito, en mi condicion de padre, madre o encargado legal, doy mi consentimiento para que "
            "la persona estudiante participe en la ExpoTECNICA Institucional, actividad avalada por el "
            "Ministerio de Educacion Publica y orientada a estimular la resolucion de problemas, la innovacion, "
            "la ingenieria y el autoaprendizaje."
        )
        y = _draw_wrapped(pdf, intro, 42, y, width_chars=105, leading=13, size=9)
        y -= 10

        _draw_field(pdf, "Nombre del estudiante", member.full_name, 42, y, 300)
        _draw_field(pdf, "Numero de identidad", member.identity_number or "", 375, y, 170)
        y -= 42
        _draw_field(pdf, "Proyecto", project.title, 42, y, 300)
        _draw_field(pdf, "Seccion", member.section_name or "", 375, y, 170)
        y -= 48

        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(42, y, "Dejo constancia que:")
        y -= 18
        checks = [
            "Recibi informacion sencilla y comprensible respecto a los beneficios y actividades de esta actividad.",
            "Se me ha explicado este documento.",
            "Autorizo la participacion de la persona estudiante en la ExpoTECNICA.",
            "Libero de responsabilidad a las personas funcionarias cuando las imagenes no sean utilizadas para fines comerciales.",
        ]
        pdf.setFont("Helvetica", 9)
        for item in checks:
            pdf.rect(48, y - 2, 8, 8)
            y = _draw_wrapped(pdf, item, 64, y, width_chars=92, leading=12, size=9)
            y -= 6

        y -= 16
        _draw_field(pdf, "Nombre padre, madre o encargado legal", "", 42, y, 300)
        _draw_field(pdf, "Cedula", "", 375, y, 170)
        y -= 46
        _draw_field(pdf, "Firma", "", 42, y, 250)
        _draw_field(pdf, "Fecha", "", 375, y, 170)
        y -= 42
        pdf.setFont("Helvetica", 8)
        pdf.drawString(42, y, _pdf_text("Documento generado por el sistema ExpoTecnica. Debe imprimirse, firmarse y entregarse a la organizacion."))
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


def _build_student(form_data, index, section_name, default_specialty_name, specialties_by_id):
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
        "specialty": specialty.name if specialty else default_specialty_name,
        "section_name": section_name,
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
            student["specialty_id"],
            student["specialty"],
        ]
        if not all(required):
            return f"Completa todos los datos obligatorios del estudiante N.{number}."
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
        section_id = request.form.get("section_id", type=int)
        specialty_id = request.form.get("specialty_id", type=int)

        requirements = [item.strip().lower() for item in request.form.getlist("requirements") if item.strip()]
        requirements_other = (_draft_form_value(form_data, "requirements_other") or "").strip()
        required_students = _required_student_numbers(form_data)

        section = Section.query.get(section_id) if section_id else None
        specialty = Specialty.query.get(specialty_id) if specialty_id else None
        level_code = section.level.code if section and section.level else ""

        focus_name = specialty.name if specialty else ""
        section_name = section.name if section else ""
        specialties_by_id = {item.id: item for item in Specialty.query.filter_by(is_active=True).all()}
        students = [_build_student(form_data, i, section_name, focus_name, specialties_by_id) for i in [1, 2, 3]]
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
            grade_level=level_code,
            specialty=focus_name,
            section_id=section_id,
            specialty_id=specialty_id,
            workshop_id=None,
            campaign_id=active_campaign.id,
            advisor_name=(_draft_form_value(form_data, "advisor_name") or "").strip(),
            advisor_identity=advisor_identity,
            advisor_birth_date=_parse_date(_draft_form_value(form_data, "advisor_birth_date")),
            advisor_gender=_normalize_person_gender(form_data, "advisor_gender"),
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
        if not section:
            flash("Debes seleccionar una seccion valida.", "error")
            return render_template("public/register_project.html", **_draft_context(form_data, temp_document_path))

        if category not in {"emprendimiento", "steam"}:
            flash("Categoria invalida para este formulario.", "error")
            return render_template("public/register_project.html", **_draft_context(form_data, temp_document_path))
        if level_code not in {"10", "11", "12"}:
            flash("La ExpoTecnica institucional solo permite secciones de especialidad tecnica (niveles 10, 11 y 12).", "error")
            return render_template("public/register_project.html", **_draft_context(form_data, temp_document_path))
        if not specialty:
            flash("Debes indicar la especialidad tecnica del proyecto.", "error")
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
        return redirect(url_for("public.project_documents", project_id=project.id))

    return render_template("public/register_project.html", **_draft_context())


def project_documents(project_id: int):
    project = (
        Project.query.options(
            joinedload(Project.members),
            joinedload(Project.section),
            joinedload(Project.specialty_ref),
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
