from flask import Blueprint

from app.controllers import auth_controller

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

auth_bp.add_url_rule("/login", view_func=auth_controller.login, methods=["GET", "POST"])
auth_bp.add_url_rule("/cambiar-contrasena", view_func=auth_controller.change_password, methods=["GET", "POST"])
auth_bp.add_url_rule("/logout", view_func=auth_controller.logout, methods=["POST"])
auth_bp.add_url_rule("/salir-suplantacion", endpoint="stop_impersonation", view_func=auth_controller.stop_impersonation, methods=["POST"])
