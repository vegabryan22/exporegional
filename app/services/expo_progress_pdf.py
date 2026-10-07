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
    styles.add(ParagraphStyle('ProjectTitle', parent=styles['Cell'],fontName='Helvetica-Bold',fontSize=12,leading=15,spaceAfter=5))
    styles.add(ParagraphStyle('Secondary',parent=styles['Cell'],fontSize=8.5,leading=12,textColor=colors.HexColor('#526d7b'),spaceAfter=4))
    styles.add(ParagraphStyle('Category',parent=styles['Cell'],fontName='Helvetica-Bold',fontSize=9,leading=12,textColor=colors.HexColor('#177c92'),spaceAfter=6))
    styles.add(ParagraphStyle('Count',parent=styles['Cell'],fontName='Helvetica-Bold',fontSize=18,leading=23,alignment=1))
    styles.add(ParagraphStyle('CenterSmall',parent=styles['Secondary'],alignment=1))
    styles.add(ParagraphStyle('ReportTitle',parent=styles['Cell'],fontName='Helvetica-Bold',fontSize=23,leading=28,textColor=colors.white))
    styles.add(ParagraphStyle('HeaderSub',parent=styles['Secondary'],textColor=colors.HexColor('#d8edf4'),spaceAfter=0))
    styles.add(ParagraphStyle('Venue',parent=styles['Cell'],fontName='Helvetica-Bold',fontSize=14,leading=18,textColor=colors.HexColor('#173f55'),keepWithNext=True))
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
    banner = Table([[[p('EXPO TÉCNICA REGIONAL','HeaderSub'),Spacer(1,7),p('Avance de evaluaciones por recinto','ReportTitle'),Spacer(1,7),p('Corte: ' + datetime.now(ZoneInfo('America/Guatemala')).strftime('%d/%m/%Y a las %H:%M'),'HeaderSub')]]],colWidths=[doc.width])
    banner.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#173f55')),('LEFTPADDING',(0,0),(-1,-1),18),('TOPPADDING',(0,0),(-1,-1),16),('BOTTOMPADDING',(0,0),(-1,-1),16)]))
    metrics=Table([[[p(total,'Count'),p('PROYECTOS','CenterSmall')],[p(complete,'Count'),p('COMPLETOS','CenterSmall')],[p(total-complete,'Count'),p('PENDIENTES','CenterSmall')]]],colWidths=[doc.width/3]*3)
    metrics.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#eef6fa')),('BOX',(0,0),(-1,-1),0.5,colors.HexColor('#d3e2eb')),('LINEBEFORE',(1,0),(2,0),0.5,colors.HexColor('#d3e2eb')),('TOPPADDING',(0,0),(-1,-1),12),('BOTTOMPADDING',(0,0),(-1,-1),10)]))
    story = [banner,Spacer(1,12),metrics,Spacer(1,12)]
    applied = []
    if filters.get('q'): applied.append('Buscar: ' + filters['q'])
    if filters.get('venue'): applied.append('Recinto: ' + next((g['name'] for g in data['venues'] if g['id'] == filters['venue']), filters['venue']))
    if filters.get('category'): applied.append('Categoría: ' + next((c['name'] for c in data['categories'] if c['code'] == filters['category']), filters['category']))
    if filters.get('pending'): applied.append('Solo pendientes')
    story += [p('Filtros: ' + (' | '.join(applied) or 'Todos los proyectos')), Spacer(1,14)]
    labels = {'complete':'Completo','pending':'En proceso','not_started':'Sin evaluar','review':'Requiere revisión'}
    category_names = {c['code']:c['name'] for c in data['categories']}
    category_names.setdefault('steam','STEAM')
    category_names.setdefault('emprendimiento','Emprendimiento')
    for group, rows in groups:
        done = sum(r['status']=='complete' for r in rows)
        heading = Table([[p('RECINTO  ' + group['name'],'Venue'),p(f'{len(rows)} proyectos · {done} completos','Secondary')]],colWidths=[doc.width*.65,doc.width*.35])
        heading.keepWithNext=True
        heading.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#dff0f5')),('LINEBEFORE',(0,0),(0,0),4,colors.HexColor('#2188a7')),('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10),('LEFTPADDING',(0,0),(-1,-1),12)]))
        table_rows = [[p(h,'TableHead') for h in ['Proyecto / colegio','Exposición','Inglés','Estado']]]
        for row in rows:
            detail = [p(row['title'],'ProjectTitle'),p('CATEGORÍA: ' + category_names.get(row['category'],row['category']),'Category'),p('Colegio: ' + row['school'],'Secondary')]
            pending = row.get('pending_judges')
            if pending:
                if pending['exposition']:
                    detail.append(p('Jueces pendientes de exposición: ' + ', '.join(j['name'] for j in pending['exposition']),'Secondary'))
                if pending['exposition_unassigned']: detail.append(p(f"Exposición: falta asignar {pending['exposition_unassigned']} juez(es).",'Secondary'))
                elif not pending['exposition']: detail.append(p('Exposición: sin jueces asignados pendientes.','Secondary'))
                if row['english_participants']:
                    detail.append(p('Inglés: ' + ('; '.join(f"{j['name']} ({j['completed']}/{j['expected']} estudiantes)" for j in pending['english']) or ('Sin juez asignado' if row['english_unassigned'] else 'Completo')),'Secondary'))
            english = f"{row['english']}/{row['english_expected']}" if row['english_participants'] else 'No participa'
            if row['english_unassigned']: english += '\nSin juez asignado'
            expo_cell=[p(f"{row['exposition']}/3",'Count'),p('evaluaciones','CenterSmall')]
            english_cell=[p(f"{row['english']}/{row['english_expected']}",'Count'),p('individuales','CenterSmall')] if row['english_participants'] else [p('No participa','CenterSmall')]
            if row['english_unassigned']: english_cell.append(p('Sin juez asignado','CenterSmall'))
            table_rows.append([detail,expo_cell,english_cell,p(labels[row['status']])])
        table = Table(table_rows,colWidths=[doc.width-285,90,95,100],repeatRows=1,hAlign='LEFT')
        table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#173f55')),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),12),('BOTTOMPADDING',(0,0),(-1,-1),12),('LEFTPADDING',(0,0),(-1,-1),12),('RIGHTPADDING',(0,0),(-1,-1),12),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f5f9fc')]),('LINEBELOW',(0,0),(-1,-1),0.4,colors.HexColor('#d3e2eb'))]))
        tones={'complete':('#e2f3dc','#356814'),'pending':('#fff2d8','#845200'),'not_started':('#edf1f5','#526674'),'review':('#fbe4e6','#9b2638')}
        for index,row in enumerate(rows,1):
            bg,fg=tones[row['status']]
            table.setStyle(TableStyle([('BACKGROUND',(-1,index),(-1,index),colors.HexColor(bg))]))
            table_rows[index][-1].style=ParagraphStyle('Status',parent=styles['Cell'],fontName='Helvetica-Bold',textColor=colors.HexColor(fg),alignment=1)
        story += [KeepTogether([heading,Spacer(1,4)]),table,Spacer(1,16)]
    if not groups: story.append(p('No hay proyectos que coincidan con los filtros.'))
    def footer(canvas, document):
        canvas.saveState(); canvas.setFont('Helvetica',8); canvas.setFillColor(colors.HexColor('#5d7484'))
        canvas.drawString(32,20,'Evaluaciones guardadas al momento de exportar.'); canvas.drawRightString(landscape(A4)[0]-32,20,f'Página {document.page}'); canvas.restoreState()
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    output.seek(0)
    return output
