"""Email-inspired branded access card, with a clean vector QR."""
from io import BytesIO
from html import escape
from pathlib import Path
from flask import current_app
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from app.models.system_setting import SystemSetting


def _brand_logo(key):
    root = Path(current_app.static_folder).resolve()
    configured = SystemSetting.get_value(key, '')
    if not configured:
        return None
    path = (root / configured).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        return None
    try:
        image = ImageReader(str(path))
        image.getSize()
        return image
    except (OSError, ValueError):
        return None


def build_access_card(venue, link):
    output = BytesIO()
    pdf = canvas.Canvas(output, pagesize=A4)
    pdf.setTitle('Acceso del responsable - ' + venue['name'])
    width, height = A4
    ink = colors.HexColor('#173f55')
    teal = colors.HexColor('#218aa0')
    orange = colors.HexColor('#f5a11a')
    muted = colors.HexColor('#597382')
    def paragraph(text, x, top, available, size=12, bold=False, color=ink):
        style = ParagraphStyle('card', fontName='Helvetica-Bold' if bold else 'Helvetica', fontSize=size,
                               leading=size*1.3, alignment=1, textColor=color)
        item = Paragraph(escape(str(text)), style)
        _, h = item.wrap(available, height)
        item.drawOn(pdf, x, top-h)
        return h
    pdf.setFillColor(colors.HexColor('#edf5fa')); pdf.rect(0,0,width,height,fill=1,stroke=0)
    pdf.setFillColor(colors.white); pdf.roundRect(28,28,width-56,height-56,18,fill=1,stroke=0)
    pdf.setFillColor(ink); pdf.roundRect(28,height-176,width-56,148,18,fill=1,stroke=0)
    pdf.rect(28,height-176,width-56,24,fill=1,stroke=0)
    for key,x,w,label in [('school_logo_path',50,100,'CORVEC'),('expo_logo_path',width-230,180,'ExpoTécnica')]:
        pdf.setFillColor(colors.white); pdf.roundRect(x,height-120,w,80,10,fill=1,stroke=0)
        image = _brand_logo(key)
        if image:
            pdf.drawImage(image,x+8,height-112,width=w-16,height=64,preserveAspectRatio=True,anchor='c',mask='auto')
        else:
            paragraph(label,x,height-70,w,14,True)
    paragraph('ExpoTécnica Regional',50,height-128,width-100,21,True,colors.white)
    paragraph('ACCESO DEL RESPONSABLE DE RECINTO',50,height-157,width-100,9,True,colors.HexColor('#cfe8f1'))
    pdf.setFillColor(orange); pdf.rect(28,height-180,width-56,4,fill=1,stroke=0)
    paragraph('TU RECINTO',52,height-199,width-104,10,True,teal)
    name_h = paragraph(venue['name'],52,height-219,width-104,36 if len(venue['name']) < 25 else 18,True)
    responsible_top = height-219-name_h-8
    responsible_h = paragraph('Responsable: ' + (venue.get('responsible') or 'Pendiente de asignar'),60,responsible_top,width-120,12,False,muted)
    qr_top = responsible_top-responsible_h-16
    qr_size = 224 if len(venue['name']) < 40 and len(venue.get('responsible','')) < 65 else 190
    pdf.setFillColor(colors.HexColor('#f1f8fb'))
    pdf.roundRect(52,qr_top-qr_size-28,width-104,qr_size+28,14,fill=1,stroke=0)
    qr = QrCodeWidget(link, barLevel='M')
    bounds = qr.getBounds(); w = bounds[2]-bounds[0]; h = bounds[3]-bounds[1]
    drawing = Drawing(qr_size,qr_size,transform=[qr_size/w,0,0,qr_size/h,0,0])
    drawing.add(Rect(0,0,w,h,fillColor=colors.white,strokeColor=None)); drawing.add(qr)
    renderPDF.draw(drawing,pdf,(width-qr_size)/2,qr_top-qr_size-14)
    action_top = qr_top-qr_size-44
    pdf.setFillColor(orange); pdf.roundRect(95,action_top-36,width-190,36,9,fill=1,stroke=0)
    paragraph('Escanea y consulta tu recinto',100,action_top-9,width-200,14,True)
    info_top = action_top-51
    paragraph('Sin usuario ni contraseña',60,info_top,width-120,12,True)
    paragraph('Proyectos · Avance de evaluaciones · Jueces pendientes',60,info_top-22,width-120,11,False,muted)
    paragraph('Actualización automática cada 30 segundos.',60,info_top-43,width-120,10,False,muted)
    pdf.setStrokeColor(colors.HexColor('#d9e7ed')); pdf.line(60,113,width-60,113)
    paragraph('ENLACE PRIVADO · SOLO CONSULTA',60,100,width-120,9,True,teal)
    paragraph('Entrega esta ficha únicamente al responsable. Si el acceso se revoca o reemplaza, este QR deja de funcionar.',60,82,width-120,9,False,muted)
    pdf.showPage(); pdf.save(); output.seek(0)
    return output
