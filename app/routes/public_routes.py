from flask import Blueprint

from app.controllers import admin_controller, project_controller

public_bp = Blueprint("public", __name__)


@public_bp.route("/")
def index():
    return project_controller.home_intro()


@public_bp.route("/proyectos")
def projects():
    return project_controller.list_projects()


public_bp.add_url_rule(
    "/inscripcion",
    view_func=project_controller.register_project,
    methods=["GET", "POST"],
)

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
    "/proyecto/<int:project_id>/actualizar-documento",
    endpoint="project_document_revision",
    view_func=project_controller.submit_document_revision,
    methods=["GET", "POST"],
)

public_bp.add_url_rule(
    "/actualizar-documento",
    endpoint="search_project_revision",
    view_func=project_controller.search_project_for_revision,
    methods=["GET"],
)

public_bp.add_url_rule(
    "/proyecto/<int:project_id>/integrante/<int:member_id>/editar",
    endpoint="project_member_edit",
    view_func=project_controller.submit_member_edit,
    methods=["GET", "POST"],
)

public_bp.add_url_rule(
    "/proyecto/<int:project_id>/documentos/paquete",
    endpoint="project_documents_packet",
    view_func=project_controller.project_documents_packet,
    methods=["GET"],
)

public_bp.add_url_rule(
    "/jueces/registro",
    endpoint="judge_registration",
    view_func=admin_controller.public_judge_registration,
    methods=["GET", "POST"],
)

public_bp.add_url_rule(
    "/registro-jueces",
    endpoint="judge_registration_short",
    view_func=admin_controller.public_judge_registration,
    methods=["GET", "POST"],
)

public_bp.add_url_rule(
    "/registro/jueces",
    endpoint="judge_registration_alt",
    view_func=admin_controller.public_judge_registration,
    methods=["GET", "POST"],
)

public_bp.add_url_rule(
    "/api/forms/judge-access",
    view_func=admin_controller.judge_form_webhook,
    methods=["POST"],
)
