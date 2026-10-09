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

def _attendance_return_url():
    filters = {"filter_" + key: request.form.get("filter_" + key, "")[:200]
               for key in ("q", "school", "invitation", "response", "presence", "profile")}
    return url_for('admin.expo_attendance', **{key: value for key, value in filters.items() if value})

@admin_module_required('judge_pool')
def attendance_page():
    judges = exposition_judges()
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'response':
            judge = next((j for j in judges if j.id == request.form.get('judge_id',type=int)),None)
            if not judge: abort(404)
            answer = request.form.get('attendance')
            notes = request.form.get('notes','').strip()
            if answer not in {'yes','no','pending'} or len(notes)>500:
                flash('Selecciona una respuesta válida y una observación de hasta 500 caracteres.','error')
                return redirect(_attendance_return_url())
            before = judge.attendance_status_label
            judge.attendance_confirmed = True if answer == 'yes' else False if answer == 'no' else None
            judge.attendance_responded_at = datetime.utcnow() if answer != 'pending' else None
            if answer == 'no':
                records = presence_records()
                records[str(judge.id)] = {'present':False,'at':datetime.now(timezone.utc).isoformat(),'by':current_user.id}
                SystemSetting.set_value(presence_key(),json.dumps(records))
            log_event('admin.judge.attendance.response','judge',judge.id,f'{before} -> {judge.attendance_status_label}; registrado por {current_user.full_name}; observación: {notes or "Sin observación"}')
            db.session.commit(); flash('Respuesta registrada. La cuenta y las evaluaciones anteriores se conservan.','success')
        elif action == 'presence':
            judge = next((j for j in judges if j.id == request.form.get('judge_id',type=int)),None)
            if not judge: abort(404)
            records = presence_records()
            present = request.form.get('present') == '1'
            if present and judge.attendance_confirmed is False:
                flash('El juez está marcado como No asiste. Corrige su respuesta antes de registrar la llegada.','error')
                return redirect(_attendance_return_url())
            records[str(judge.id)] = {'present':present,'at':datetime.now(timezone.utc).isoformat(),'by':current_user.id}
            SystemSetting.set_value(presence_key(),json.dumps(records))
            log_event('admin.judge.expo.checkin','judge',judge.id,f'Presencia en recinto: {present}')
            db.session.commit(); flash('Llegada del juez actualizada.','success')
        elif action == 'send':
            ids = set(request.form.getlist('judge_ids',type=int))
            selected = [j for j in judges if j.id in ids]
            if not selected or not smtp_is_configured():
                flash('Selecciona jueces y verifica la configuración de correo.','error')
                return redirect(_attendance_return_url())
            try: messages = [invitation_message(j) for j in selected]
            except ValueError as error:
                db.session.rollback(); flash(str(error),'error'); return redirect(_attendance_return_url())
            db.session.commit()
            results = send_email_batch(messages)
            for judge, (ok,error) in zip(selected,results):
                if ok: judge.attendance_invitation_sent_at = datetime.utcnow()
                judge.attendance_invitation_error = error
                log_event('admin.judge.expo.invitation','judge',judge.id,'Enviada' if ok else f'Error: {error}')
            db.session.commit(); flash(f'Invitaciones enviadas: {sum(ok for ok,_ in results)} de {len(selected)}.','success')
        return redirect(_attendance_return_url())
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
