from io import BytesIO
from html import escape
from datetime import datetime
from zoneinfo import ZoneInfo
import unicodedata
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether

def normalize(value):
    return ''.join(c for c in unicodedata.normalize('NFD', value) if unicodedata.category(c) != 'Mn').lower()

def build_progress_pdf(data, filters):
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=landscape(A4), rightMargin=32, leftMargin=32, topMargin=32, bottomMargin=36)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle('Cell', fontName='Helvetica', fontSize=9, leading=12, textColor=colors.HexColor('#173f55')))
    styles.add(ParagraphStyle('TableHead', parent=styles['Cell'], textColor=colors.white, fontName='Helvetica-Bold'))
    def p(value, style='Cell'):
        return Paragraph(escape(str(value)).replace('\n','<br/>'), styles[style])
    groups = []
    for group in data['venues']:
        if filters.get('venue') and group['id'] != filters['venue']:
            continue
        rows = [r for r in group['projects'] if (not filters.get('category') or r['category'] == filters['category']) and (not filters.get('pending') or r['status'] != 'complete') and normalize(filters.get('q','')) in normalize(r['title'] + ' ' + r['school'])]
        if rows:
            groups.append((group, rows))
    total = sum(len(rows) for _, rows in groups)
    complete = sum(r['status'] == 'complete' for _, rows in groups for r in rows)
    story = [p('Avance de evaluaciones por recinto','Title'), p('ExpoTécnica Regional - Corte: ' + datetime.now(ZoneInfo('America/Guatemala')).strftime('%d/%m/%Y %H:%M')), Spacer(1,12), p(f'{total} proyectos en este reporte | {complete} completos | {total-complete} pendientes'), Spacer(1,10)]
    applied = []
    if filters.get('q'): applied.append('Buscar: ' + filters['q'])
    if filters.get('venue'): applied.append('Recinto: ' + next((g['name'] for g in data['venues'] if g['id'] == filters['venue']), filters['venue']))
    if filters.get('category'): applied.append('Categoría: ' + next((c['name'] for c in data['categories'] if c['code'] == filters['category']), filters['category']))
    if filters.get('pending'): applied.append('Solo pendientes')
    story += [p('Filtros: ' + (' | '.join(applied) or 'Todos los proyectos')), Spacer(1,14)]
    labels = {'complete':'Completo','pending':'En proceso','not_started':'Sin evaluar','review':'Requiere revisión'}
    for group, rows in groups:
        heading = p(group['name'] + f' - {len(rows)} proyectos','Heading2')
        table_rows = [[p(h,'TableHead') for h in ['Proyecto / colegio','Exposición','Inglés','Estado']]]
        for row in rows:
            detail = row['title'] + '\n' + row['school']
            pending = row.get('pending_judges')
            if pending:
                detail += '\nExposición pendiente: ' + (', '.join(j['name'] for j in pending['exposition']) or 'Sin jueces pendientes')
                if pending['exposition_unassigned']: detail += f"\nFalta asignar {pending['exposition_unassigned']} juez(es) de exposición."
                if row['english_participants']:
                    detail += '\nInglés pendiente: ' + ('; '.join(f"{j['name']} ({j['completed']}/{j['expected']} estudiantes)" for j in pending['english']) or ('Sin juez asignado' if row['english_unassigned'] else 'Completo'))
            english = f"{row['english']}/{row['english_expected']}" if row['english_participants'] else 'No participa'
            if row['english_unassigned']: english += '\nSin juez asignado'
            table_rows.append([p(detail),p(f"{row['exposition']}/3"),p(english),p(labels[row['status']])])
        table = Table(table_rows,colWidths=[doc.width-260,65,95,100],repeatRows=1,hAlign='LEFT')
        table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#173f55')),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),9),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#eef6fa')]),('LINEBELOW',(0,0),(-1,-1),0.4,colors.HexColor('#d3e2eb'))]))
        story += [KeepTogether([heading,Spacer(1,4)]),table,Spacer(1,16)]
    if not groups: story.append(p('No hay proyectos que coincidan con los filtros.'))
    def footer(canvas, document):
        canvas.saveState(); canvas.setFont('Helvetica',8); canvas.setFillColor(colors.HexColor('#5d7484'))
        canvas.drawString(32,20,'Evaluaciones guardadas al momento de exportar.'); canvas.drawRightString(landscape(A4)[0]-32,20,f'Página {document.page}'); canvas.restoreState()
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    output.seek(0)
    return output
