from flask import Blueprint

from app.controllers import project_controller

public_bp = Blueprint("public", __name__)


@public_bp.route("/")
def index():
    return project_controller.home_intro()


public_bp.add_url_rule("/health", endpoint="system_health", view_func=project_controller.system_health, methods=["GET"])


@public_bp.route("/proyectos")
def projects():
    return project_controller.list_projects()


public_bp.add_url_rule(
    "/proyecto/<int:project_id>/evaluar",
    view_func=project_controller.evaluate_project_entry,
    methods=["GET"],
)

public_bp.add_url_rule(
    "/proyecto/<int:project_id>/documentos",
    endpoint="project_documents",
    view_func=project_controller.project_documents,
    methods=["GET"],
)

public_bp.add_url_rule(
    "/proyecto/<int:project_id>/documentos/paquete",
    endpoint="project_documents_packet",
    view_func=project_controller.project_documents_packet,
    methods=["GET"],
)

public_bp.add_url_rule(
    "/juez/confirmar/<token>",
    endpoint="judge_attendance_confirm",
    view_func=project_controller.judge_attendance_confirm,
    methods=["GET", "POST"],
)
