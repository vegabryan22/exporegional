"""Ceremony list using the same winners as the award certificates."""
from datetime import datetime
from zoneinfo import ZoneInfo
from html import escape
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


def closing_awards(overview):
    rows = []
    def school(project):
        return project.institution.name if project.institution else project.institution_name or 'Sin colegio vinculado'
    for item in overview.get('category_winners', []):
        for key,place in [('winner','Primer lugar'),('runner_up','Segundo lugar')]:
            winner = item.get(key)
            if not winner or not winner.get('project'):
                continue
            project = winner['project']
            members = sorted(project.members,key=lambda m:(m.student_number or 0,m.id))
            rows.append({'category':item['category'].name,'school':school(project),'place':place,
                         'project':project.title,'students':[m.full_name for m in members],'kind':'category'})
    # English recognitions are individual, not awards for the whole project team.
    for winner in overview.get('english_ranking', [])[:2]:
        member,project = winner.get('member'),winner.get('project')
        if member and project:
            rows.append({'category':'Inglés','school':school(project),'place':'Mención de honor',
                         'project':project.title,'students':[member.full_name],'kind':'english'})
    summary = overview.get('summary_cards', {})
    final = bool(summary.get('projects') and summary.get('completed_projects') == summary['projects']
                 and summary.get('completed_english_evaluations',0) == summary.get('expected_english_evaluations',0))
    return {'award_rows':rows,'is_final':final,'generated_at':datetime.now(ZoneInfo('America/Guatemala'))}


def closing_awards_pdf(data):
    output = BytesIO()
    doc = SimpleDocTemplate(output,pagesize=landscape(A4),leftMargin=30,rightMargin=30,topMargin=30,bottomMargin=34)
    ink = colors.HexColor('#173f55')
    style = ParagraphStyle('award',fontName='Helvetica',fontSize=10,leading=14,textColor=ink)
    heading = ParagraphStyle('award-head',parent=style,fontName='Helvetica-Bold',textColor=colors.white)
    title = ParagraphStyle('award-title',parent=style,fontName='Helvetica-Bold',fontSize=22,leading=27)
    def p(value,chosen=style):
        return Paragraph(escape(str(value)),chosen)
    story = [p('ExpoTécnica Regional',style),Spacer(1,6),p('Lista de premiación para el cierre',title),Spacer(1,8),p('Generado: '+data['generated_at'].strftime('%d/%m/%Y %H:%M')),Spacer(1,12)]
    if not data['is_final']:
        story += [p('RESULTADOS PROVISIONALES: hay evaluaciones pendientes. Verifica los resultados antes de anunciar la premiación.'),Spacer(1,12)]
    table_rows = [[p(h,heading) for h in ['Categoría','Colegio','Puesto','Nombre del proyecto','Estudiantes']]]
    for row in data['award_rows']:
        names = [p(name) for name in row['students']] or [p('Sin integrantes registrados')]
        table_rows.append([p(row['category']),p(row['school']),p(row['place']),p(row['project']),names])
    if len(table_rows) == 1:
        story.append(p('No hay premiados calculados.'))
    else:
        table = Table(table_rows,colWidths=[doc.width*f for f in (.13,.22,.15,.24,.26)],repeatRows=1,hAlign='LEFT')
        commands = [('BACKGROUND',(0,0),(-1,0),ink),('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.4,colors.HexColor('#d7e3ea')),('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),12),('BOTTOMPADDING',(0,0),(-1,-1),12)]
        for i,row in enumerate(data['award_rows'],start=1):
            commands.append(('BACKGROUND',(0,i),(-1,i),colors.HexColor('#e8f4ed') if row['kind']=='english' else colors.white if i%2 else colors.HexColor('#f1f7fa')))
        table.setStyle(TableStyle(commands)); story.append(table)
    def footer(pdf,document):
        pdf.setFont('Helvetica',8); pdf.setFillColor(ink)
        pdf.drawString(30,17,'Solo premiados · Las menciones de honor de inglés se presentan al final.')
        pdf.drawRightString(landscape(A4)[0]-30,17,f'Página {document.page}')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    output.seek(0)
    return output
