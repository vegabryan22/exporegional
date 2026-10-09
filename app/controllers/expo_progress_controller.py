import json
import uuid
from flask import render_template, request, redirect, url_for, flash, jsonify, make_response, send_file, abort, session
import secrets
from flask_login import current_user
from app.extensions import db
from app.models.project import Project
from app.services.expo_progress_service import venue_config, public_progress, VENUE_SETTING, default_venue_responsible, group_venue_projects
from app.models.system_setting import SystemSetting
from app.services.audit_service import log_event
from app.controllers.admin_controller import admin_module_required, _base_context
from app.services.venue_access_service import resolve_access, scoped_progress, access_url, change_access
from urllib.parse import urlencode


def venue_access(token, output='page'):
    venue = resolve_access(token)
    data = scoped_progress(venue)
    if output == 'data':
        response = jsonify(data)
    elif output == 'pdf':
        from app.services.expo_progress_pdf import build_progress_pdf
        filters = {'q': request.args.get('q', '').strip(), 'category': request.args.get('category', ''), 'pending': request.args.get('pending') == '1'}
        response = send_file(build_progress_pdf(data, filters), mimetype='application/pdf', as_attachment=True, download_name='avance_recinto.pdf')
    else:
        response = make_response(render_template('public/expo_progress.html', progress=data, show_pending_judges=True, venue_access=venue,
            progress_data_url=url_for('public.venue_access_data', token=token), progress_pdf_url=url_for('public.venue_access_pdf', token=token)))
    response.headers['Cache-Control'] = 'no-store, private'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['X-Robots-Tag'] = 'noindex, nofollow, noarchive'
    return response


@admin_module_required('assignments')
def venue_access_card(venue_id):
    from app.services.venue_access_pdf import build_access_card
    venue = next((v for v in venue_config()['venues'] if v['id'] == venue_id), None)
    if not venue or not venue.get('access_nonce'):
        abort(404)
    response = send_file(build_access_card(venue, access_url(venue)), mimetype='application/pdf', as_attachment=True, download_name='acceso_recinto.pdf')
    response.headers['Cache-Control'] = 'no-store, private'
    return response


@admin_module_required('assignments')
def venue_access_cards():
    from app.services.venue_access_pdf import build_access_cards
    entries = [(v, access_url(v)) for v in venue_config()['venues'] if v.get('access_nonce')]
    if not entries:
        flash('Habilita al menos un acceso antes de imprimir las tarjetas.', 'error')
        return redirect(url_for('admin.venues_page', _anchor='manage-venues'))
    response = send_file(build_access_cards(entries), mimetype='application/pdf', as_attachment=True, download_name='tarjetas_acceso_recintos.pdf')
    response.headers['Cache-Control'] = 'no-store, private'
    return response

def progress_pdf():
    from app.services.expo_progress_pdf import build_progress_pdf
    authorized = current_user.is_authenticated and current_user.has_admin_access
    data = public_progress(include_pending_judges=authorized)
    filters = {"q": request.args.get("q", "").strip(), "venue": request.args.get("venue", ""), "category": request.args.get("category", ""), "pending": request.args.get("pending") == "1"}
    response = send_file(build_progress_pdf(data, filters), mimetype="application/pdf", as_attachment=True, download_name="avance_evaluaciones_por_recinto.pdf")
    response.headers["Cache-Control"] = "no-store, private"
    response.vary.add("Cookie")
    return response

def public_page():
    authorized = current_user.is_authenticated and current_user.has_admin_access
    response = make_response(render_template("public/expo_progress.html", progress=public_progress(include_pending_judges=authorized), show_pending_judges=authorized))
    response.headers["Cache-Control"] = "no-store"
    response.vary.add("Cookie")
    return response

def public_data():
    authorized = current_user.is_authenticated and current_user.has_admin_access
    response = jsonify(public_progress(include_pending_judges=authorized))
    response.headers["Cache-Control"] = "no-store"
    response.vary.add("Cookie")
    return response

@admin_module_required("assignments")
def venues_page():
    config = venue_config()
    projects = Project.query.filter(Project.is_active.is_(True)).order_by(Project.title).all()
    if request.method == "POST":
        action = request.form.get("action")
        if action in {'access_enable', 'access_rotate', 'access_revoke', 'access_enable_all'}:
            supplied = request.form.get('access_csrf', '')
            expected = session.get('venue_access_csrf', '')
            if not expected or not secrets.compare_digest(supplied, expected):
                abort(400)
        if action == 'access_enable_all':
            enabled = 0
            for venue in config['venues']:
                if not venue.get('access_nonce'):
                    change_access(venue, 'access_enable')
                    enabled += 1
            log_event('admin.expo.venue.access_enable_all', 'setting', detail=f'Accesos habilitados: {enabled}. Se conservaron los enlaces activos.')
        elif action == "create":
            name = request.form.get("name", "").strip()
            if not name or len(name) > 120 or any(v["name"].casefold() == name.casefold() for v in config["venues"]):
                flash("Indica un nombre único de recinto, de hasta 120 caracteres.", "error")
                return redirect(url_for("admin.venues_page"))
            responsible = request.form.get('responsible','').strip() or default_venue_responsible(name)
            if len(responsible)>120:
                flash('El nombre del responsable debe tener hasta 120 caracteres.','error')
                return redirect(url_for('admin.venues_page'))
            config["venues"].append({"id": uuid.uuid4().hex, "name": name, "responsible":responsible})
        elif action in {'update','delete','access_enable','access_rotate','access_revoke'}:
            venue_id = request.form.get('venue_id','')
            venue = next((v for v in config['venues'] if v['id'] == venue_id),None)
            if not venue:
                flash('Recinto no encontrado.','error')
                return redirect(url_for('admin.venues_page'))
            if action.startswith('access_'):
                change_access(venue, action)
                log_event('admin.expo.venue.' + action, 'setting', detail=f"Acceso de consulta: {venue['name']}")
            elif action == 'delete':
                if venue_id in config['projects'].values():
                    flash('No se puede eliminar un recinto con proyectos asignados. Reubica sus proyectos y guarda las ubicaciones primero.','error')
                    return redirect(url_for('admin.venues_page'))
                config['venues'] = [v for v in config['venues'] if v['id'] != venue_id]
                log_event('admin.expo.venue.delete','setting',detail=f"Recinto eliminado: {venue['name']}")
            else:
                name = request.form.get('name','').strip()
                responsible = request.form.get('responsible','').strip()
                if not name or len(name)>120 or len(responsible)>120 or any(v['id'] != venue_id and v['name'].casefold() == name.casefold() for v in config['venues']):
                    flash('Indica un nombre único de recinto y datos de hasta 120 caracteres.','error')
                    return redirect(url_for('admin.venues_page'))
                venue.update(name=name,responsible=responsible)
        elif action == "save":
            names = [request.form.get("name_" + v["id"], v["name"]).strip() for v in config["venues"]]
            if any(not n or len(n) > 120 for n in names) or len({n.casefold() for n in names}) != len(names):
                flash("Los recintos deben tener nombres únicos de hasta 120 caracteres.", "error")
                return redirect(url_for("admin.venues_page"))
            for venue, name in zip(config["venues"], names):
                venue["name"] = name
                responsible = request.form.get('responsible_' + venue['id'],venue.get('responsible','')).strip()
                if len(responsible)>120:
                    flash('El nombre del responsable debe tener hasta 120 caracteres.','error')
                    return redirect(url_for('admin.venues_page'))
                venue['responsible'] = responsible
            allowed = {v["id"] for v in config["venues"]}
            for project in projects:
                venue_id = request.form.get("venue_" + str(project.id), "")
                if venue_id and venue_id not in allowed:
                    flash("El recinto seleccionado no existe.", "error")
                    return redirect(url_for("admin.venues_page"))
                if venue_id:
                    config["projects"][str(project.id)] = venue_id
                else:
                    config["projects"].pop(str(project.id), None)
        else:
            flash("Acción no válida.", "error")
            return redirect(url_for("admin.venues_page"))
        SystemSetting.set_value(VENUE_SETTING, json.dumps(config, ensure_ascii=False))
        log_event("admin.expo.venues.update", "setting", detail=f"Recintos y ubicaciones actualizados: {len(config['venues'])} recintos.")
        db.session.commit()
        if action.startswith('access_'):
            flash(f'{enabled} accesos habilitados. Los enlaces activos no se modificaron.' if action == 'access_enable_all' else 'Acceso revocado. El enlace y QR anteriores ya no funcionan.' if action == 'access_revoke' else 'Acceso de consulta listo. Puedes compartir el enlace o descargar la ficha QR.', 'success')
        else:
            flash("Recintos guardados. La vista pública ya refleja las ubicaciones.", "success")
        return redirect(url_for("admin.venues_page", _anchor='manage-venues' if action.startswith('access_') else None))
    session.setdefault('venue_access_csrf', secrets.token_urlsafe(32))
    links = {}
    for venue in config['venues']:
        link = access_url(venue)
        if link:
            message = f"Hola {venue.get('responsible') or 'compañero/a'}, este es el acceso de consulta del recinto {venue['name']} de ExpoTécnica Regional. Aquí puedes ver los proyectos y jueces pendientes. No necesitas usuario. No compartas este enlace fuera del equipo organizador.\n{link}"
            links[venue['id']] = {'url': link, 'message': message, 'whatsapp': 'https://wa.me/?' + urlencode({'text': message})}
    return render_template("admin/expo_venues.html", **_base_context("venues"), venues=config["venues"], venue_access_links=links, locations=config["projects"], venue_projects=projects, venue_school_groups=group_venue_projects(projects))
