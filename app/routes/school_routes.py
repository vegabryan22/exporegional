from flask import Blueprint

from app.controllers import project_controller, school_controller


school_bp = Blueprint("school", __name__, url_prefix="/colegio")
school_bp.add_url_rule("/panel", view_func=school_controller.school_coordinator_required(school_controller.dashboard), methods=["GET"])
school_bp.add_url_rule("/perfil", view_func=school_controller.school_coordinator_required(school_controller.profile), methods=["GET", "POST"])
school_bp.add_url_rule("/jueces", endpoint="judges", view_func=school_controller.school_coordinator_required(school_controller.judges), methods=["GET", "POST"])
school_bp.add_url_rule(
    "/proyectos/nuevo",
    endpoint="project_form",
    view_func=school_controller.school_coordinator_required(project_controller.register_project),
    methods=["GET", "POST"],
)
school_bp.add_url_rule(
    "/proyectos/consultar-cedula",
    endpoint="lookup_registration_identity",
    view_func=school_controller.school_coordinator_required(project_controller.lookup_registration_identity),
    methods=["POST"],
)
school_bp.add_url_rule("/proyectos/<int:project_id>/editar", endpoint="project_edit", view_func=school_controller.school_coordinator_required(school_controller.project_form), methods=["GET", "POST"])
school_bp.add_url_rule("/proyectos/<int:project_id>/gestionar", endpoint="project_workspace", view_func=school_controller.school_coordinator_required(school_controller.project_workspace), methods=["GET", "POST"])
school_bp.add_url_rule("/proyectos/<int:project_id>/enviar", endpoint="project_submit", view_func=school_controller.school_coordinator_required(school_controller.submit_project), methods=["POST"])
