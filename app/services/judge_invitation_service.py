from collections import defaultdict
from datetime import datetime
from html import escape
from io import BytesIO
from pathlib import Path

from flask import current_app, url_for

from app.models.assignment_process import AssignmentProcess
from app.models.system_setting import SystemSetting
from app.services.mail_service import send_email_batch


SUPPORT_EMAIL_DEFAULT = "Erick.Alvarez.Sosa@mep.go.cr"
SPANISH_MONTHS = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)


def _deadline_label(value):
    if not value:
        return "según el cronograma oficial"
    return value.strftime("%d/%m/%Y a las %H:%M")


def _process_copy(process_type):
    return {
        AssignmentProcess.TYPE_DOCUMENTATION: {
            "subject": "Invitación para evaluar documentos escritos - ExpoTécnica Regional",
            "title": "Evaluación de trabajos escritos",
            "purpose": "la lectura y evaluación de los trabajos escritos",
        },
        AssignmentProcess.TYPE_EXPOSITION: {
            "subject": "Invitación para evaluar exposiciones - ExpoTécnica Regional",
            "title": "Evaluación de exposiciones",
            "purpose": "la evaluación de las exposiciones de los proyectos",
        },
        AssignmentProcess.TYPE_ENGLISH: {
            "subject": "Invitación para evaluar exposiciones en inglés - ExpoTécnica Regional",
            "title": "Evaluación de exposiciones en inglés",
            "purpose": "la evaluación individual de las exposiciones en inglés",
        },
    }[process_type]


def build_personalized_invitation_pdf(judge, process):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_JUSTIFY, TA_RIGHT
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer
    from PIL import Image as PILImage, ImageChops

    support_email = SystemSetting.get_value("judge_invitation_support_email", SUPPORT_EMAIL_DEFAULT)
    copy = _process_copy(process.process_type)
    letter_purpose = (
        "la evaluación de los trabajos escritos"
        if process.process_type == AssignmentProcess.TYPE_DOCUMENTATION
        else copy["purpose"]
    )
    deadline = _deadline_label(process.deadline)
    assets = Path(current_app.static_folder) / "judge_invitation"
    output = BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=letter,
        rightMargin=0.92 * inch,
        leftMargin=0.92 * inch,
        topMargin=1.48 * inch,
        bottomMargin=1.05 * inch,
        title=f"Invitación - {judge.full_name}",
        author="Comité de Juzgamiento CORVEC Unidos por la Excelencia",
    )
    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "InvitationBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10.7,
        leading=16,
        alignment=TA_JUSTIFY,
        textColor=colors.black,
        spaceAfter=12,
    )
    meta = ParagraphStyle("InvitationMeta", parent=body, alignment=0, spaceAfter=6)
    date_style = ParagraphStyle("InvitationDate", parent=body, alignment=TA_RIGHT, spaceAfter=15)
    story = []
    with PILImage.open(assets / "mep_logo.png") as source_logo:
        background = PILImage.new("RGB", source_logo.size, "white")
        logo_bounds = ImageChops.difference(source_logo.convert("RGB"), background).getbbox()
        cropped_logo = BytesIO()
        source_logo.crop(logo_bounds).save(cropped_logo, format="PNG")
    cropped_logo.seek(0)
    mep_image = ImageReader(cropped_logo)

    def original_letter_chrome(canvas, document):
        canvas.saveState()
        ink = colors.HexColor("#8890a6")
        canvas.setStrokeColor(ink)
        canvas.setFillColor(ink)
        canvas.drawImage(mep_image, 0.83 * inch, 9.76 * inch, width=1.27 * inch, height=0.47 * inch, mask="auto")
        for x in (2.18, 3.88, 5.37):
            canvas.setLineWidth(0.7)
            canvas.line(x * inch, 9.75 * inch, x * inch, 10.3 * inch)
        canvas.setFont("Times-Bold", 8.5)
        canvas.drawCentredString(3.03 * inch, 10.06 * inch, "Dirección Regional de")
        canvas.drawCentredString(3.03 * inch, 9.86 * inch, "Educación de Desamparados")
        canvas.drawCentredString(4.62 * inch, 9.96 * inch, "Supervisión Circuito 07")
        canvas.drawImage(str(assets / "school_crest.jpg"), 5.52 * inch, 9.72 * inch, width=0.47 * inch, height=0.6 * inch, preserveAspectRatio=True, mask="auto")
        canvas.drawCentredString(6.63 * inch, 10.05 * inch, "C.T.P. Roberto Gamboa")
        canvas.drawCentredString(6.63 * inch, 9.86 * inch, "Valverde")

        canvas.setFillColor(colors.HexColor("#9299ac"))
        canvas.rect(0, 0, letter[0], 0.82 * inch, stroke=0, fill=1)
        canvas.setFillColor(colors.white)
        canvas.setFont("Times-Bold", 9.5)
        canvas.drawCentredString(letter[0] / 2, 0.44 * inch, "100 este de Gasolinera Anatot, San Rafael Abajo, Desamparados, San José")
        canvas.drawCentredString(letter[0] / 2, 0.22 * inch, "Teléfono 2275-2317 / ctp.robertogamboavalvede@www.mep.go.cr")
        canvas.restoreState()

    today = datetime.now()
    story.append(Paragraph(f"{SPANISH_MONTHS[today.month - 1].capitalize()} {today.year}", date_style))
    story.append(Paragraph("<b>De:</b> Comité de Juzgamiento Corvec Unidos por la Excelencia", meta))
    story.append(Paragraph(f"<b>Para:</b> {escape(judge.full_name)}", meta))
    story.append(Paragraph("<b>Asunto:</b> Solicitud de colaboración como juez(a) en la Feria Técnica Regional CORVEC", meta))
    story.append(Spacer(1, 17))
    story.append(Paragraph("Reciba un cordial saludo desde el CTP Roberto Gamboa Valverde.", body))
    story.append(Paragraph(
        "Por medio de la presente, el Comité de Juzgamiento del CORVEC Unidos por la Excelencia desea "
        f"expresarle nuestro más sincero agradecimiento por su disposición a formar parte del jurado en {letter_purpose}.",
        body,
    ))
    story.append(Paragraph(
        "Estudiantes de once centros educativos se han preparado con esmero y han clasificado a la "
        "ExpoTécnica 2026 en su etapa regional. Su aporte, retroalimentación y evaluación son "
        "fundamentales en el proceso de aprendizaje de los estudiantes.",
        body,
    ))
    story.append(Paragraph(
        "Para obtener detalles del proceso de cómo ingresar a la plataforma, utilice el siguiente enlace: "
        "https://expotecnica-regionaldesamparados.com/auth/login.", body,
    ))
    if process.process_type == AssignmentProcess.TYPE_DOCUMENTATION:
        story.append(Paragraph(
            "Por ello, le solicitamos de la manera más respetuosa que nos colabore con la evaluación, "
            f"la cual tiene como fecha límite el <b>{deadline}</b>.", body,
        ))
    story.append(Paragraph(
        "Agradecemos de antemano su apoyo para el éxito de esta actividad. "
        f"Le solicitamos confirmar su colaboración al correo: <b>{escape(support_email)}</b>.",
        body,
    ))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Atentamente,", body))
    story.append(Image(str(assets / "signature.png"), width=1.52 * inch, height=0.66 * inch, kind="proportional"))
    story.append(Paragraph("<b>Erick Álvarez Sosa</b><br/>Teléfono: 8372-5297", body))
    doc.build(story, onFirstPage=original_letter_chrome, onLaterPages=original_letter_chrome)
    return output.getvalue()


def send_process_invitations(process):
    grouped = defaultdict(list)
    for item in process.items:
        retryable = process.status == AssignmentProcess.STATUS_SENT or item.notification_sent_at is None
        if retryable and item.judge and item.judge.email and item.judge.is_active_user:
            grouped[item.judge_id].append(item)

    messages = []
    rows = []
    for items in grouped.values():
        messages.append(build_process_invitation_message(process, items))
        rows.append(items)

    results = send_email_batch(messages)
    sent = failed = 0
    now = datetime.now()
    for items, (ok, error) in zip(rows, results):
        for item in items:
            item.notification_sent_at = now if ok else None
            item.notification_error = None if ok else error
        sent += int(ok)
        failed += int(not ok)
    if sent and not failed:
        process.status = AssignmentProcess.STATUS_SENT
        process.sent_at = now
    return sent, failed


def build_process_invitation_message(process, items, *, include_attachment=True):
    """One source of truth for both the preview and the actual SMTP payload."""
    if not items:
        raise ValueError("El juez no tiene proyectos en este proceso.")
    support_email = SystemSetting.get_value("judge_invitation_support_email", SUPPORT_EMAIL_DEFAULT)
    panel_url = url_for("judge.dashboard", _external=True)
    copy = _process_copy(process.process_type)
    deadline = _deadline_label(process.deadline)
    judge = items[0].judge
    project_names = sorted({item.project.title for item in items if item.project})
    project_lines = "\n".join(f"- {name}" for name in project_names)
    project_html = "".join(f"<li>{escape(name)}</li>" for name in project_names)
    deadline_plain = f"\nFecha límite: {deadline}\n" if process.process_type == AssignmentProcess.TYPE_DOCUMENTATION else ""
    deadline_html = f"<p><strong>Fecha límite:</strong> {escape(deadline)}</p>" if process.process_type == AssignmentProcess.TYPE_DOCUMENTATION else ""
    body = (
        f"Hola {judge.full_name},\n\n"
        f"Se aprobó su asignación para {copy['purpose']}.\n\n"
        f"Proyectos asignados:\n{project_lines}\n"
        f"{deadline_plain}\n"
        f"Ingreso a la plataforma: {panel_url}\n\n"
        f"Dudas o soporte: {support_email}\n\n"
        "Adjuntamos la invitación formal personalizada en formato PDF."
    )
    html_body = (
        "<html><body style='font-family:Arial,sans-serif;color:#17324d'>"
        f"<h2 style='color:#0e527a'>{escape(copy['title'])}</h2>"
        f"<p>Hola <strong>{escape(judge.full_name)}</strong>,</p>"
        f"<p>Se aprobó su asignación para {escape(copy['purpose'])}.</p>"
        f"<p><strong>Proyectos asignados:</strong></p><ul>{project_html}</ul>{deadline_html}"
        f"<p><a href='{escape(panel_url)}' style='background:#0e527a;color:white;padding:11px 18px;border-radius:8px;text-decoration:none;font-weight:bold'>Ingresar a la plataforma</a></p>"
        f"<p>Dudas o soporte: <a href='mailto:{escape(support_email)}'>{escape(support_email)}</a></p>"
        "<p>Adjuntamos la invitación formal personalizada en formato PDF.</p></body></html>"
    )
    filename = f"Invitacion-{process.process_type}-{judge.full_name}.pdf".replace("/", "-").replace("\\", "-")
    message = {
        "to_email": judge.email,
        "subject": copy["subject"],
        "body": body,
        "html_body": html_body,
        "attachment_filename": filename,
    }
    if include_attachment:
        message["attachments"] = [{
            "content": build_personalized_invitation_pdf(judge, process),
            "maintype": "application",
            "subtype": "pdf",
            "filename": filename,
        }]
    return message
