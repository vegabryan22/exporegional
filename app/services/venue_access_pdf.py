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
from reportlab.lib.units import mm
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


def build_access_cards(entries):
    """Eight 90 x 55 mm personal cards per A4 sheet, with external trim marks."""
    if not entries:
        raise ValueError('No hay accesos habilitados para imprimir.')
    output = BytesIO()
    pdf = canvas.Canvas(output, pagesize=A4)
    pdf.setTitle('Tarjetas de acceso por recinto - ExpoTécnica Regional')
    page_w, page_h = A4
    card_w, card_h, gap = 90*mm, 55*mm, 6*mm
    left = (page_w-2*card_w-gap)/2
    ink = colors.HexColor('#173f55')
    orange = colors.HexColor('#f5a11a')
    logos = [_brand_logo('school_logo_path'), _brand_logo('expo_logo_path')]
    pages = (len(entries)+7)//8

    def text(value, x, top, width, max_height, size, bold=False, color=ink):
        # Fit complete names rather than cutting off the recipient's identity.
        while True:
            item = Paragraph(escape(str(value)), ParagraphStyle('mini-card', fontName='Helvetica-Bold' if bold else 'Helvetica', fontSize=size, leading=size*1.12, textColor=color))
            _, h = item.wrap(width, card_h)
            if h <= max_height or size <= 5:
                break
            size -= .5
        item.drawOn(pdf,x,top-h)
        return h

    for page in range(pages):
        pdf.setFillColor(ink); pdf.setFont('Helvetica-Bold',14)
        pdf.drawString(left,page_h-30,'Tarjetas de acceso por recinto')
        pdf.setFont('Helvetica',9)
        pdf.drawString(left,page_h-46,'Imprimir al 100% / tamaño real · A4 · Recortar por las marcas')
        for index,(venue,link) in enumerate(entries[page*8:(page+1)*8]):
            x = left+(index%2)*(card_w+gap)
            y = page_h-68-card_h-(index//2)*(card_h+gap)
            pdf.setFillColor(colors.white); pdf.rect(x,y,card_w,card_h,fill=1,stroke=0)
            pdf.setFillColor(ink); pdf.rect(x,y+card_h-36,card_w,36,fill=1,stroke=0)
            for image,lx,lw,label in [(logos[0],x+6,30,'CORVEC'),(logos[1],x+card_w-71,65,'ExpoTécnica')]:
                pdf.setFillColor(colors.white); pdf.roundRect(lx,y+card_h-31,lw,26,3,fill=1,stroke=0)
                if image:
                    pdf.drawImage(image,lx+2,y+card_h-29,width=lw-4,height=22,preserveAspectRatio=True,anchor='c',mask='auto')
                else:
                    text(label,lx+2,y+card_h-13,lw-4,16,5.5,True)
            text('ExpoTécnica Regional',x+43,y+card_h-11,card_w-122,20,8,True,colors.white)
            pdf.setFillColor(orange); pdf.rect(x,y+card_h-38,card_w,2,fill=1,stroke=0)
            content_w = card_w-112
            text('RESPONSABLE DE RECINTO',x+9,y+card_h-47,content_w,12,6,True,colors.HexColor('#218aa0'))
            title_h = text(venue['name'],x+9,y+card_h-61,content_w,31,16,True)
            name_top = y+card_h-66-title_h
            text(venue.get('responsible') or 'Pendiente de asignar',x+9,name_top,content_w,max(28,name_top-y-25),9,True)
            text('Escanea para ver proyectos y jueces pendientes. Sin usuario.',x+9,y+29,content_w,22,6.5)
            qr = QrCodeWidget(link,barLevel='M')
            bounds = qr.getBounds(); w,h = bounds[2]-bounds[0],bounds[3]-bounds[1]
            size = 96
            drawing = Drawing(size,size,transform=[size/w,0,0,size/h,0,0])
            drawing.add(Rect(0,0,w,h,fillColor=colors.white,strokeColor=None)); drawing.add(qr)
            renderPDF.draw(drawing,pdf,x+card_w-size-5,y+17)
            pdf.setFillColor(ink); pdf.setFont('Helvetica',5.5)
            pdf.drawString(x+9,y+6,'ACCESO PERSONAL · SOLO CONSULTA · NO COMPARTIR')
            # Corner marks stay outside the card and its QR quiet zone.
            pdf.setStrokeColor(colors.HexColor('#8998a0')); pdf.setLineWidth(.4)
            for cx,cy,sx,sy in [(x,y,-1,-1),(x+card_w,y,1,-1),(x,y+card_h,-1,1),(x+card_w,y+card_h,1,1)]:
                pdf.line(cx+sx*2,cy,cx+sx*7,cy)
                pdf.line(cx,cy+sy*2,cx,cy+sy*7)
        pdf.setFillColor(ink); pdf.setFont('Helvetica',8)
        pdf.drawString(left,24,f'{len(entries)} tarjetas · 90 × 55 mm · Página {page+1} de {pages}')
        pdf.showPage()
    pdf.save(); output.seek(0)
    return output
