from flask import Blueprint

from app.controllers import school_controller


school_bp = Blueprint("school", __name__, url_prefix="/colegio")
school_bp.add_url_rule("/panel", view_func=school_controller.school_coordinator_required(school_controller.dashboard), methods=["GET"])
school_bp.add_url_rule("/perfil", view_func=school_controller.school_coordinator_required(school_controller.profile), methods=["POST"])
school_bp.add_url_rule("/proyectos/nuevo", view_func=school_controller.school_coordinator_required(school_controller.project_form), methods=["GET", "POST"])
school_bp.add_url_rule("/proyectos/<int:project_id>/editar", endpoint="project_edit", view_func=school_controller.school_coordinator_required(school_controller.project_form), methods=["GET", "POST"])
school_bp.add_url_rule("/proyectos/<int:project_id>/enviar", endpoint="project_submit", view_func=school_controller.school_coordinator_required(school_controller.submit_project), methods=["POST"])
