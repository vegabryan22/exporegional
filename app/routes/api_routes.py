from flask import Blueprint

from app.controllers import api_controller


api_bp = Blueprint("api", __name__, url_prefix="/api/v1")
api_bp.add_url_rule("/regional-projects", view_func=api_controller.upsert_regional_project, methods=["POST"])
api_bp.add_url_rule("/regional-projects/<string:external_project_id>/files", view_func=api_controller.upload_regional_project_files, methods=["POST"])
api_bp.add_url_rule("/regional-projects/<string:external_project_id>/status", view_func=api_controller.get_regional_project_status, methods=["GET"])
