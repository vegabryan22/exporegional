import json
import uuid
from flask import render_template, request, redirect, url_for, flash, jsonify, make_response
from app.extensions import db
from app.models.project import Project
from app.services.expo_progress_service import venue_config, public_progress, VENUE_SETTING
from app.models.system_setting import SystemSetting
from app.services.audit_service import log_event
from app.controllers.admin_controller import admin_module_required, _base_context

def public_page():
    response = make_response(render_template("public/expo_progress.html", progress=public_progress()))
    response.headers["Cache-Control"] = "no-store"
    return response

def public_data():
    response = jsonify(public_progress())
    response.headers["Cache-Control"] = "no-store"
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
            config["venues"].append({"id": uuid.uuid4().hex, "name": name})
        elif action == "save":
            names = [request.form.get("name_" + v["id"], v["name"]).strip() for v in config["venues"]]
            if any(not n or len(n) > 120 for n in names) or len({n.casefold() for n in names}) != len(names):
                flash("Los recintos deben tener nombres únicos de hasta 120 caracteres.", "error")
                return redirect(url_for("admin.venues_page"))
            for venue, name in zip(config["venues"], names):
                venue["name"] = name
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
    return render_template("admin/expo_venues.html", **_base_context("venues"), venues=config["venues"], locations=config["projects"], venue_projects=projects)
