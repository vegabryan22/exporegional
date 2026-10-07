import json
import secrets
from io import BytesIO
from pathlib import Path
from datetime import datetime, timezone
from flask import current_app, render_template, url_for
from app.models.judge import Judge
from app.models.campaign import Campaign
from app.models.system_setting import SystemSetting

def presence_key():
    campaign = Campaign.query.filter_by(is_active=True).first()
    return 'expo_presence_' + str(campaign.id if campaign else 'regional') + '_' + SystemSetting.get_value('expotec_event_date','2026-10-09')

def presence_records():
    return json.loads(SystemSetting.get_value(presence_key(), '{}'))

def present_judge_ids():
    return {int(key) for key, value in presence_records().items() if value.get('present')}

def exposition_judges():
    return Judge.query.filter(Judge.role == Judge.ROLE_JUDGE, Judge.is_active_user.is_(True), Judge.can_evaluate_exposition.is_(True)).order_by(Judge.full_name).all()

def invitation_pdf(judge):
    from pypdf import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    assets = Path(current_app.root_path) / 'assets' / 'expo_invitation'
    if 'InvitationArial' not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont('InvitationArial', str(assets / 'arial.ttf')))
    reader = PdfReader(str(assets / 'original.pdf'))
    page = reader.pages[0]
    width, height = float(page.mediabox.width), float(page.mediabox.height)
    overlay = BytesIO()
    pdf = canvas.Canvas(overlay,pagesize=(width,height))
    slots = ((judge.full_name,139.41998291015625),(judge.job_title or 'Juez de exposición',167.04998779296875))
    for text, top in slots:
        # Only the two recipient slots are covered; all other original PDF content is retained.
        pdf.setFillColorRGB(1,1,1); pdf.rect(84,height-top-4,440,19,stroke=0,fill=1)
    for text, top in slots:
        pdf.setFillColorRGB(0,0,0); pdf.setFont('InvitationArial',12)
        lines = ['']
        for word in text.split():
            candidate = (lines[-1] + ' ' + word).strip()
            if pdfmetrics.stringWidth(candidate,'InvitationArial',12) > 435:
                lines.append(word)
            else: lines[-1] = candidate
        if len(lines) > 2 or any(pdfmetrics.stringWidth(line,'InvitationArial',12) > 435 for line in lines):
            raise ValueError(f'El nombre o cargo de {judge.full_name} excede el espacio de la carta. Ajusta su ficha antes de enviar.')
        for index,line in enumerate(lines): pdf.drawString(85.025,height-top-index*13,line)
    pdf.save(); overlay.seek(0)
    page.merge_page(PdfReader(overlay).pages[0])
    writer = PdfWriter(); writer.add_page(page)
    output = BytesIO(); writer.write(output)
    return output.getvalue()

def invitation_message(judge, *, preview=False):
    token = judge.attendance_token or ('vista-previa' if preview else secrets.token_urlsafe(40))
    if not preview: judge.attendance_token = token
    confirmation = url_for('public.judge_attendance_confirm',token=token,_external=True)
    subject = 'Invitación a evaluar exposición - ExpoTécnica Regional 2026'
    body = f'Hola {judge.full_name},\n\nTe invitamos a evaluar exposición el 09 de octubre de 2026, de 07:30 a. m. a 2:00 p. m., en el CTP José Albertazzi Avendaño.\nAdjuntamos la carta personalizada.\nConfirma tu asistencia: {confirmation}\nLos proyectos se distribuirán el día del evento entre los jueces presentes.\nConsultas: expotecnicaregionaldesamparado@gmail.com'
    school_logo = SystemSetting.get_value('school_logo_path','')
    expo_logo = SystemSetting.get_value('expo_logo_path','')
    return {'to_email':judge.email,'subject':subject,'body':body,'html_body':render_template('admin/email_expo_attendance.html',judge=judge,confirmation=confirmation,preview=preview,school_logo=url_for('static',filename=school_logo,_external=True) if school_logo else '',expo_logo=url_for('static',filename=expo_logo,_external=True) if expo_logo else ''),'attachments':[{'content':invitation_pdf(judge),'filename':'Invitacion-exposicion.pdf','maintype':'application','subtype':'pdf'}]}
