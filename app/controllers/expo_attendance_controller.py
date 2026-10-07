import json
from datetime import datetime, timezone
from io import BytesIO
from flask import render_template, request, redirect, url_for, flash, send_file, abort
from flask_login import current_user
from app.extensions import db
from app.models.judge import Judge
from app.models.system_setting import SystemSetting
from app.controllers.admin_controller import admin_module_required, _base_context
from app.services.audit_service import log_event
from app.services.expo_attendance_service import exposition_judges, presence_records, presence_key, invitation_pdf, invitation_message
from app.services.mail_service import smtp_is_configured, send_email_batch

@admin_module_required('judge_pool')
def attendance_page():
    judges = exposition_judges()
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'presence':
            judge = next((j for j in judges if j.id == request.form.get('judge_id',type=int)),None)
            if not judge: abort(404)
            records = presence_records()
            present = request.form.get('present') == '1'
            records[str(judge.id)] = {'present':present,'at':datetime.now(timezone.utc).isoformat(),'by':current_user.id}
            SystemSetting.set_value(presence_key(),json.dumps(records))
            log_event('admin.judge.expo.checkin','judge',judge.id,f'Presencia en recinto: {present}')
            db.session.commit(); flash('Llegada del juez actualizada.','success')
        elif action == 'send':
            ids = set(request.form.getlist('judge_ids',type=int))
            selected = [j for j in judges if j.id in ids]
            if not selected or not smtp_is_configured():
                flash('Selecciona jueces y verifica la configuración de correo.','error')
                return redirect(url_for('admin.expo_attendance'))
            try: messages = [invitation_message(j) for j in selected]
            except ValueError as error:
                db.session.rollback(); flash(str(error),'error'); return redirect(url_for('admin.expo_attendance'))
            db.session.commit()
            results = send_email_batch(messages)
            for judge, (ok,error) in zip(selected,results):
                if ok: judge.attendance_invitation_sent_at = datetime.utcnow()
                judge.attendance_invitation_error = error
                log_event('admin.judge.expo.invitation','judge',judge.id,'Enviada' if ok else f'Error: {error}')
            db.session.commit(); flash(f'Invitaciones enviadas: {sum(ok for ok,_ in results)} de {len(selected)}.','success')
        return redirect(url_for('admin.expo_attendance'))
    return render_template('admin/expo_attendance.html',**_base_context('expo_attendance'),expo_judges=judges,presence=presence_records())

@admin_module_required('judge_pool')
def preview(judge_id):
    judge = next((j for j in exposition_judges() if j.id == judge_id),None)
    if not judge: abort(404)
    if request.args.get('pdf') == '1':
        response = send_file(BytesIO(invitation_pdf(judge)),mimetype='application/pdf',download_name='Invitacion-exposicion.pdf')
    else:
        response = render_template('admin/expo_invitation_preview.html',**_base_context('judge_pool'),judge=judge,message=invitation_message(judge,preview=True))
    from flask import make_response
    response = make_response(response); response.headers['Cache-Control']='no-store'; return response
