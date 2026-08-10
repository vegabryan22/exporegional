from flask import Blueprint

from app.controllers import certificate_controller


certificate_bp = Blueprint("certificates", __name__, url_prefix="/certificados")
certificate_bp.add_url_rule("/", view_func=certificate_controller.dashboard, methods=["GET"])
certificate_bp.add_url_rule("/integrantes/<int:member_id>", view_func=certificate_controller.update_member, methods=["POST"])
certificate_bp.add_url_rule("/proyecto/<int:project_id>/integrantes", view_func=certificate_controller.update_project_members, methods=["POST"])
certificate_bp.add_url_rule("/pdf", view_func=certificate_controller.certificates_pdf, methods=["GET"])
certificate_bp.add_url_rule("/descargar", view_func=certificate_controller.certificates_download, methods=["GET"])
certificate_bp.add_url_rule("/proyecto/<int:project_id>/pdf", view_func=certificate_controller.project_pdf, methods=["GET"])
certificate_bp.add_url_rule("/proyecto/<int:project_id>/descargar", view_func=certificate_controller.project_download, methods=["GET"])
