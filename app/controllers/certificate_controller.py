import re
from functools import wraps

from flask import abort, flash, jsonify, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models.judge import Judge
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.services.audit_service import log_event
from app.controllers import admin_controller


def certificate_access_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapped(*args, **kwargs):
        if current_user.effective_role != Judge.ROLE_CERTIFICATE_OPERATOR and not current_user.has_admin_access:
            abort(403)
        return view_func(*args, **kwargs)
    return wrapped


def _identity_key(value):
    return re.sub(r"[^0-9A-Za-z]", "", value or "").upper()


@certificate_access_required
def dashboard():
    status = (request.args.get("estado") or "pendientes").strip().lower()
    all_projects = (Project.query.options(joinedload(Project.members)).filter(Project.is_active.is_(True))
                    .order_by(Project.title.asc()).all())
    rows = [{"project": p, "verified": sum(1 for m in p.members if m.certificate_name_verified),
             "total": len(p.members), "complete": bool(p.members) and all(m.certificate_name_verified for m in p.members)} for p in all_projects]
    visible_rows = rows if status == "todos" else [row for row in rows if not row["complete"]]
    return render_template("certificates/dashboard.html", project_rows=visible_rows,
                           status=status, total_projects=len(rows), completed_projects=sum(1 for row in rows if row["complete"]))


@certificate_access_required
def update_member(member_id):
    member = db.session.get(ProjectMember, member_id)
    if not member or not member.project or not member.project.is_active:
        abort(404)
    full_name = " ".join((request.form.get("full_name") or "").split())
    if len(full_name) < 5:
        flash("Escribe el nombre y los apellidos completos.", "error")
    else:
        previous = member.full_name
        member.full_name = full_name
        member.certificate_name_verified = request.form.get("verified") == "1"
        log_event(
            "certificates.member_name.verified",
            "project_member",
            entity_id=member.id,
            detail=f"Nombre para certificado: '{previous}' => '{full_name}'; verificado={member.certificate_name_verified}",
        )
        db.session.commit()
        flash("Nombre guardado y marcado como verificado." if member.certificate_name_verified else "Nombre guardado.", "success")
    q = (request.form.get("q") or "").strip()
    return redirect(url_for("certificates.dashboard", q=q) if q else url_for("certificates.dashboard"))


@certificate_access_required
def update_project_members(project_id):
    project = Project.query.options(joinedload(Project.members)).filter_by(id=project_id, is_active=True).first()
    if not project:
        abort(404)
    updated = 0
    for member in project.members:
        full_name = " ".join((request.form.get(f"full_name_{member.id}") or "").split())
        if len(full_name) < 5:
            continue
        previous = member.full_name
        member.full_name = full_name
        member.certificate_name_verified = request.form.get(f"verified_{member.id}") == "1"
        log_event("certificates.member_name.verified", "project_member", entity_id=member.id,
                  detail=f"Proyecto #{project.id}; nombre para certificado: '{previous}' => '{full_name}'; verificado={member.certificate_name_verified}")
        updated += 1
    db.session.commit()
    complete = bool(project.members) and all(member.certificate_name_verified for member in project.members)
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"ok": True, "updated": updated, "complete": complete,
                        "verified": sum(1 for member in project.members if member.certificate_name_verified),
                        "total": len(project.members)})
    flash(f"Se actualizaron {updated} integrante(s) del proyecto. Los cambios confirmados ya están listos para imprimir.", "success")
    if request.form.get("continue") == "next":
        next_project = (Project.query.join(ProjectMember).filter(Project.is_active.is_(True),
                        Project.id != project.id, ProjectMember.certificate_name_verified.is_(False))
                        .order_by(Project.title.asc()).first())
        if next_project:
            return redirect(url_for("certificates.dashboard", proyecto=next_project.id))
    return redirect(url_for("certificates.dashboard", estado="todos", proyecto=project.id))


def _pdf(project_id=None, download=False):
    context = admin_controller._build_participation_certificate_context(project_id)
    if project_id is not None and not context["projects"]:
        abort(404)
    if not admin_controller.REPORTLAB_AVAILABLE:
        flash("No se pudo generar el PDF porque ReportLab no está disponible.", "error")
        return redirect(url_for("certificates.dashboard"))
    pdf_bytes = admin_controller._render_participation_certificates_pdf(context)
    name = "certificados_participacion.pdf" if project_id is None else f"certificados_proyecto_{project_id}.pdf"
    return send_file(pdf_bytes, mimetype="application/pdf", as_attachment=download, download_name=name)


@certificate_access_required
def certificates_pdf():
    return _pdf()


@certificate_access_required
def certificates_download():
    return _pdf(download=True)


@certificate_access_required
def project_pdf(project_id):
    return _pdf(project_id)


@certificate_access_required
def project_download(project_id):
    return _pdf(project_id, download=True)
