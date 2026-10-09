from flask import render_template, send_file
from app.controllers.admin_controller import admin_module_required, _base_context, build_admin_evaluation_overview
from app.services.closing_awards_service import closing_awards, closing_awards_pdf


@admin_module_required('evaluations')
def closing_awards_page():
    return render_template('admin/closing_awards.html',**_base_context('evaluations'),**closing_awards(build_admin_evaluation_overview()))


@admin_module_required('evaluations')
def closing_awards_download():
    response = send_file(closing_awards_pdf(closing_awards(build_admin_evaluation_overview())),mimetype='application/pdf',as_attachment=True,download_name='lista_premiacion_cierre_regional.pdf')
    response.headers['Cache-Control'] = 'no-store, private'
    return response
