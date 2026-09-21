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
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    support_email = SystemSetting.get_value("judge_invitation_support_email", SUPPORT_EMAIL_DEFAULT)
    school_name = SystemSetting.get_value("school_name", "ExpoTécnica Regional")
    school_logo_path = (SystemSetting.get_value("school_logo_path", "") or "").strip()
    copy = _process_copy(process.process_type)
    deadline = _deadline_label(process.deadline)
    output = BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=letter,
        rightMargin=0.72 * inch,
        leftMargin=0.72 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
        title=f"Invitación - {judge.full_name}",
        author="Comité de Juzgamiento CORVEC Unidos por la Excelencia",
    )
    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "InvitationBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=15,
        alignment=TA_JUSTIFY,
        textColor=colors.HexColor("#17324d"),
        spaceAfter=10,
    )
    meta = ParagraphStyle("InvitationMeta", parent=body, leading=14, spaceAfter=3)
    date_style = ParagraphStyle("InvitationDate", parent=body, alignment=TA_RIGHT, spaceAfter=14)
    title_style = ParagraphStyle(
        "InvitationTitle",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#0e527a"),
        spaceBefore=6,
        spaceAfter=15,
    )
    story = []
    logo_file = Path(current_app.static_folder) / school_logo_path if school_logo_path else None
    if logo_file and logo_file.is_file():
        logo = Image(str(logo_file), width=0.9 * inch, height=0.9 * inch, kind="proportional")
        header = Table(
            [[logo, Paragraph(f"<b>{escape(school_name)}</b><br/>Comité de Juzgamiento<br/>CORVEC Unidos por la Excelencia", meta)]],
            colWidths=[1.05 * inch, 5.4 * inch],
        )
    else:
        header = Table(
            [[Paragraph(f"<b>{escape(school_name)}</b><br/>Comité de Juzgamiento<br/>CORVEC Unidos por la Excelencia", meta)]],
            colWidths=[6.45 * inch],
        )
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eef7fc")),
        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#86b9d5")),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.extend([header, Spacer(1, 12)])
    today = datetime.now()
    story.append(Paragraph(f"{today.day} de {SPANISH_MONTHS[today.month - 1]} de {today.year}", date_style))
    story.append(Paragraph("<b>De:</b> Comité de Juzgamiento CORVEC Unidos por la Excelencia", meta))
    story.append(Paragraph(f"<b>Para:</b> {escape(judge.full_name)}", meta))
    story.append(Paragraph(f"<b>Asunto:</b> Solicitud de colaboración como juez(a) en la Feria Técnica Regional CORVEC", meta))
    story.append(Paragraph(copy["title"], title_style))
    story.append(Paragraph("Reciba un cordial saludo desde el CTP Roberto Gamboa Valverde.", body))
    story.append(Paragraph(
        "Por medio de la presente, el Comité de Juzgamiento del CORVEC Unidos por la Excelencia "
        f"desea expresarle nuestro más sincero agradecimiento por su disposición a colaborar con {copy['purpose']}.",
        body,
    ))
    story.append(Paragraph(
        "Estudiantes de once centros educativos se han preparado con esmero para la ExpoTécnica Regional. "
        "Su aporte, retroalimentación y evaluación son fundamentales en su proceso de aprendizaje.",
        body,
    ))
    if process.process_type == AssignmentProcess.TYPE_DOCUMENTATION:
        story.append(Paragraph(f"La evaluación debe quedar finalizada a más tardar el <b>{deadline}</b>.", body))
    story.append(Paragraph(
        "Los proyectos asignados, el enlace de ingreso y las indicaciones operativas se incluyen en el cuerpo del correo que acompaña esta invitación.",
        body,
    ))
    story.append(Paragraph(
        f"Para cualquier duda o soporte, por favor escriba a <b>{escape(support_email)}</b>.",
        body,
    ))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Agradecemos de antemano su apoyo para el éxito de esta actividad.", body))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Atentamente,<br/><br/><b>Erick Álvarez Sosa</b><br/>Teléfono: 8372-5297", body))
    doc.build(story)
    return output.getvalue()


def send_process_invitations(process):
    support_email = SystemSetting.get_value("judge_invitation_support_email", SUPPORT_EMAIL_DEFAULT)
    panel_url = url_for("judge.dashboard", _external=True)
    copy = _process_copy(process.process_type)
    deadline = _deadline_label(process.deadline)
    grouped = defaultdict(list)
    for item in process.items:
        retryable = process.status == AssignmentProcess.STATUS_SENT or item.notification_sent_at is None
        if retryable and item.judge and item.judge.email and item.judge.is_active_user:
            grouped[item.judge_id].append(item)

    messages = []
    rows = []
    for items in grouped.values():
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
        messages.append({
            "to_email": judge.email,
            "subject": copy["subject"],
            "body": body,
            "html_body": html_body,
            "attachments": [{
                "content": build_personalized_invitation_pdf(judge, process),
                "maintype": "application",
                "subtype": "pdf",
                "filename": filename,
            }],
        })
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
