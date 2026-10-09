"""Print-ready access card, with a vector QR for reliable scanning."""
from io import BytesIO
from html import escape
from pathlib import Path
from flask import current_app
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from app.models.system_setting import SystemSetting


def build_access_card(venue, link):
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4, leftMargin=42, rightMargin=42, topMargin=40, bottomMargin=40)
    ink = colors.HexColor('#173f55')
    def p(text, size=12, bold=False, color=ink):
        return Paragraph(escape(str(text)), ParagraphStyle('card', fontName='Helvetica-Bold' if bold else 'Helvetica', fontSize=size, leading=size*1.3, alignment=1, textColor=color, spaceAfter=8, wordWrap='CJK'))
    story = []
    compact = len(venue['name']) > 40 or len(venue.get('responsible', '')) > 65
    configured = SystemSetting.get_value('expo_logo_path', '')
    root = Path(current_app.static_folder).resolve()
    logo = (root / configured).resolve() if configured else root / 'judge_invitation/mep_logo.png'
    if logo.is_relative_to(root) and logo.is_file():
        try:
            image = Image(str(logo), width=145, height=50 if compact else 70, kind='proportional')
            image.hAlign = 'CENTER'
            story += [image, Spacer(1, 16)]
        except (OSError, ValueError):
            pass
    banner = Table([[p('EXPO TÉCNICA REGIONAL', 12, True, colors.white)], [p('ACCESO DEL RESPONSABLE', 11, False, colors.white)]], colWidths=[doc.width])
    banner.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),ink),('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
    story += [banner, Spacer(1,12 if compact else 24), p('RECINTO',11,True), p(venue['name'],34 if len(venue['name']) < 25 else 18,True), p('Responsable: ' + (venue.get('responsible') or 'Pendiente de asignar'),12 if compact else 14), Spacer(1,12)]
    qr = QrCodeWidget(link, barLevel='M')
    bounds = qr.getBounds(); width = bounds[2]-bounds[0]; height = bounds[3]-bounds[1]
    size = 190 if compact else 230
    drawing = Drawing(size,size,transform=[size/width,0,0,size/height,0,0])
    drawing.add(Rect(0,0,width,height,fillColor=colors.white,strokeColor=None)); drawing.add(qr)
    frame = Table([[drawing]], colWidths=[doc.width])
    frame.setStyle(TableStyle([('ALIGN',(0,0),(-1,-1),'CENTER'),('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#eef6fa')),('TOPPADDING',(0,0),(-1,-1),16),('BOTTOMPADDING',(0,0),(-1,-1),16)]))
    story += [frame,Spacer(1,18),p('Escanea con la cámara de tu celular',16,True),p('Sin usuario ni contraseña. Consulta los proyectos del recinto, su avance y los jueces pendientes.',12),p('Actualización automática cada 30 segundos.',11),Spacer(1,10),p('ENLACE PRIVADO · SOLO CONSULTA',10,True),p('Entrega esta ficha únicamente al responsable. Si se revoca o reemplaza el acceso, este QR dejará de funcionar.',10)]
    doc.build(story); output.seek(0)
    return output
