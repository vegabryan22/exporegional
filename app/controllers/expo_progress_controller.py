import json
import uuid
from flask import render_template, request, redirect, url_for, flash, jsonify, make_response, send_file
from flask_login import current_user
from app.extensions import db
from app.models.project import Project
from app.services.expo_progress_service import venue_config, public_progress, VENUE_SETTING, default_venue_responsible, group_venue_projects
from app.models.system_setting import SystemSetting
from app.services.audit_service import log_event
from app.controllers.admin_controller import admin_module_required, _base_context

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
        if action == "create":
            name = request.form.get("name", "").strip()
            if not name or len(name) > 120 or any(v["name"].casefold() == name.casefold() for v in config["venues"]):
                flash("Indica un nombre único de recinto, de hasta 120 caracteres.", "error")
                return redirect(url_for("admin.venues_page"))
            responsible = request.form.get('responsible','').strip() or default_venue_responsible(name)
            if len(responsible)>120:
                flash('El nombre del responsable debe tener hasta 120 caracteres.','error')
                return redirect(url_for('admin.venues_page'))
            config["venues"].append({"id": uuid.uuid4().hex, "name": name, "responsible":responsible})
        elif action in {'update','delete'}:
            venue_id = request.form.get('venue_id','')
            venue = next((v for v in config['venues'] if v['id'] == venue_id),None)
            if not venue:
                flash('Recinto no encontrado.','error')
                return redirect(url_for('admin.venues_page'))
            if action == 'delete':
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
        flash("Recintos guardados. La vista pública ya refleja las ubicaciones.", "success")
        return redirect(url_for("admin.venues_page"))
    return render_template("admin/expo_venues.html", **_base_context("venues"), venues=config["venues"], locations=config["projects"], venue_projects=projects, venue_school_groups=group_venue_projects(projects))
