from flask import Blueprint

from app.controllers import project_controller
from app.controllers import expo_progress_controller

public_bp = Blueprint("public", __name__)
public_bp.add_url_rule("/expo/avance", endpoint="expo_progress", view_func=expo_progress_controller.public_page)
public_bp.add_url_rule("/expo/avance/pdf", endpoint="expo_progress_pdf", view_func=expo_progress_controller.progress_pdf)
public_bp.add_url_rule("/expo/avance/datos", endpoint="expo_progress_data", view_func=expo_progress_controller.public_data)
public_bp.add_url_rule('/expo/recinto/<token>', endpoint='venue_access', view_func=expo_progress_controller.venue_access)
public_bp.add_url_rule('/expo/recinto/<token>/datos', endpoint='venue_access_data', view_func=expo_progress_controller.venue_access, defaults={'output': 'data'})
public_bp.add_url_rule('/expo/recinto/<token>/pdf', endpoint='venue_access_pdf', view_func=expo_progress_controller.venue_access, defaults={'output': 'pdf'})


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
