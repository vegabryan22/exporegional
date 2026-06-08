from flask import Blueprint

from app.controllers import evaluation_controller

judge_bp = Blueprint("judge", __name__, url_prefix="/juez")

judge_bp.add_url_rule("/panel", view_func=evaluation_controller.dashboard, methods=["GET"])
judge_bp.add_url_rule(
    "/proyecto/<int:project_id>/documento",
    view_func=evaluation_controller.project_document,
    methods=["GET"],
)
judge_bp.add_url_rule(
    "/proyecto/<int:project_id>/evaluar",
    view_func=evaluation_controller.evaluate,
    methods=["GET", "POST"],
)

