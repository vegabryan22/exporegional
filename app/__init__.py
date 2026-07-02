import json
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from flask import Flask, render_template
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from config import Config
from app.extensions import db, login_manager
from app.services.parameter_service import bootstrap_defaults


DEFAULT_DEPARTMENT_PERMISSIONS = {
    "logistica": ["assignments", "overview", "projects"],
    "datos": ["evaluations", "overview"],
    "diseno": ["academic", "campaigns", "categories", "institution", "overview", "rubrics"],
    "qa": ["logs", "maintenance", "overview"],
}
PERMISSIONS_SETTING_KEY = "permissions_department_modules"
LOCAL_TIMEZONE = ZoneInfo("America/Costa_Rica")


def _run_optional_schema_statement(connection, statement: str, label: str) -> bool:
    try:
        connection.execute(text(statement))
        return True
    except SQLAlchemyError as error:
        print(f"[schema] No se pudo aplicar {label}: {error}")
        return False


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    from app.routes.admin_routes import admin_bp
    from app.routes.auth_routes import auth_bp
    from app.routes.judge_routes import judge_bp
    from app.routes.public_routes import public_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(judge_bp)
    app.register_blueprint(admin_bp)

    with app.app_context():
        from app import models  # noqa: F401

        _initialize_database()

    register_cli(app)
    register_template_filters(app)
    register_context_processors(app)
    register_error_handlers(app)
    return app


def _to_local_datetime(value):
    if not value:
        return None
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(LOCAL_TIMEZONE)


def register_template_filters(app):
    @app.template_filter("local_datetime")
    def local_datetime(value, fmt="%Y-%m-%d %H:%M"):
        local_value = _to_local_datetime(value)
        return local_value.strftime(fmt) if local_value else "N/D"

    @app.template_filter("local_date")
    def local_date(value, fmt="%Y-%m-%d"):
        local_value = _to_local_datetime(value)
        return local_value.strftime(fmt) if local_value else "N/D"

    @app.template_filter("from_json")
    def from_json(value):
        if not value:
            return {}
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return {}


def _is_retryable_schema_error(error: OperationalError) -> bool:
    message = str(error).lower()
    return "concurrent ddl" in message or "deadlock found" in message or "definition is being modified" in message


def _initialize_database(max_attempts: int = 5, retry_delay_seconds: float = 1.5):
    for attempt in range(1, max_attempts + 1):
        try:
            db.create_all()
            ensure_schema_updates()
            bootstrap_defaults(db)
            return
        except OperationalError as error:
            if not _is_retryable_schema_error(error) or attempt == max_attempts:
                raise
            time.sleep(retry_delay_seconds)


def register_cli(app):
    @app.cli.command("create-judge")
    def create_judge():
        from getpass import getpass

        from app.models.judge import Judge

        full_name = input("Nombre completo: ").strip()
        email = input("Correo: ").strip().lower()
        password = getpass("Contraseña: ")

        if Judge.query.filter_by(email=email).first():
            print("Ya existe un juez con ese correo.")
            return

        judge = Judge(full_name=full_name, email=email)
        judge.set_password(password)
        db.session.add(judge)
        db.session.commit()
        print("Juez creado correctamente.")

    @app.cli.command("assign-project")
    def assign_project():
        from app.models.assignment import Assignment
        from app.models.judge import Judge
        from app.models.project import Project

        try:
            judge_id = int(input("ID juez: ").strip())
            project_id = int(input("ID proyecto: ").strip())
        except ValueError:
            print("IDs inválidos.")
            return

        judge = Judge.query.get(judge_id)
        project = Project.query.get(project_id)
        if not judge or not project:
            print("Juez o proyecto no encontrado.")
            return

        exists = Assignment.query.filter_by(judge_id=judge_id, project_id=project_id).first()
        if exists:
            print("La asignación ya existe.")
            return

        db.session.add(Assignment(judge_id=judge_id, project_id=project_id))
        db.session.commit()
        print("Asignación creada.")

    @app.cli.command("create-admin")
    def create_admin():
        from getpass import getpass

        from app.models.judge import Judge

        full_name = input("Nombre completo: ").strip()
        email = input("Correo: ").strip().lower()
        password = getpass("Contraseña: ")

        if Judge.query.filter_by(email=email).first():
            print("Ya existe un usuario con ese correo.")
            return

        admin = Judge(full_name=full_name, email=email, role=Judge.ROLE_SUPERADMIN, is_admin=True)
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        print("Admin creado correctamente.")


def register_context_processors(app):
    @app.context_processor
    def inject_institution_info():
        from datetime import date

        from app.models.campaign import Campaign
        from app.models.system_setting import SystemSetting

        active_campaign = (
            Campaign.query.filter(
                Campaign.is_active.is_(True),
                Campaign.start_date <= date.today(),
                Campaign.end_date >= date.today(),
            )
            .order_by(Campaign.start_date.desc())
            .first()
        )

        return {
            "institution": {
                "name": SystemSetting.get_value("school_name", "CTP Roberto Gamboa Valverde"),
                "address": SystemSetting.get_value("school_address", "Direccion institucional no configurada"),
                "phone": SystemSetting.get_value("school_phone", "+506 0000-0000"),
                "email": SystemSetting.get_value("school_email", "direccion@ctprgv.edu"),
                "logo_path": SystemSetting.get_value("school_logo_path", ""),
                "expo_logo_path": SystemSetting.get_value("expo_logo_path", ""),
            },
            "campaign_is_open": active_campaign is not None,
            "site_visibility": {
                "maintenance_enabled": SystemSetting.get_value("maintenance_enabled", "0") == "1",
                "maintenance_message": SystemSetting.get_value(
                    "maintenance_message",
                    "Estamos cargando informacion de proyectos. Vuelve pronto.",
                ),
                "maintenance_image_path": SystemSetting.get_value("maintenance_image_path", ""),
            },
        }


def register_error_handlers(app):
    @app.errorhandler(413)
    def request_entity_too_large(error):
        max_mb = app.config.get("MAX_CONTENT_LENGTH", 0) / (1024 * 1024)
        return (
            render_template(
                "errors/413.html",
                max_upload_mb=round(max_mb, 1) if max_mb else None,
            ),
            413,
        )


def ensure_schema_updates():
    inspector = inspect(db.engine)
    with db.engine.begin() as connection:
        if "campaigns" not in inspector.get_table_names():
            connection.execute(
                text(
                    """
                    CREATE TABLE campaigns (
                        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(180) NOT NULL UNIQUE,
                        start_date DATE NOT NULL,
                        end_date DATE NOT NULL,
                        is_active BOOLEAN NOT NULL DEFAULT 0,
                        notes TEXT NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
            )

        judge_columns = {column["name"] for column in inspector.get_columns("judges")}
        if "is_admin" not in judge_columns:
            connection.execute(text("ALTER TABLE judges ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0"))
        if "is_active_user" not in judge_columns:
            connection.execute(text("ALTER TABLE judges ADD COLUMN is_active_user BOOLEAN NOT NULL DEFAULT 1"))
        if "role" not in judge_columns:
            connection.execute(text("ALTER TABLE judges ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'judge'"))
        if "department" not in judge_columns:
            connection.execute(text("ALTER TABLE judges ADD COLUMN department VARCHAR(40) NULL"))
        if "job_title" not in judge_columns:
            connection.execute(text("ALTER TABLE judges ADD COLUMN job_title VARCHAR(120) NULL"))
        if "identity" not in judge_columns:
            connection.execute(text("ALTER TABLE judges ADD COLUMN identity VARCHAR(40) NULL"))
        if "institution" not in judge_columns:
            connection.execute(text("ALTER TABLE judges ADD COLUMN institution VARCHAR(160) NULL"))
        if "previous_expo" not in judge_columns:
            connection.execute(text("ALTER TABLE judges ADD COLUMN previous_expo VARCHAR(10) NULL"))
        if "phone" not in judge_columns:
            connection.execute(text("ALTER TABLE judges ADD COLUMN phone VARCHAR(40) NULL"))
        if "can_evaluate_documentation" not in judge_columns:
            connection.execute(text("ALTER TABLE judges ADD COLUMN can_evaluate_documentation BOOLEAN NOT NULL DEFAULT 1"))
        if "can_evaluate_exposition" not in judge_columns:
            connection.execute(text("ALTER TABLE judges ADD COLUMN can_evaluate_exposition BOOLEAN NOT NULL DEFAULT 1"))
        if "can_evaluate_english" not in judge_columns:
            connection.execute(text("ALTER TABLE judges ADD COLUMN can_evaluate_english BOOLEAN NOT NULL DEFAULT 0"))
        if "category_scope" not in judge_columns:
            connection.execute(text("ALTER TABLE judges ADD COLUMN category_scope VARCHAR(40) NOT NULL DEFAULT 'ambas'"))
        if "registration_notes" not in judge_columns:
            connection.execute(text("ALTER TABLE judges ADD COLUMN registration_notes TEXT NULL"))
        if "registered_from_public_form" not in judge_columns:
            connection.execute(text("ALTER TABLE judges ADD COLUMN registered_from_public_form BOOLEAN NOT NULL DEFAULT 0"))
        if "must_change_password" not in judge_columns:
            connection.execute(text("ALTER TABLE judges ADD COLUMN must_change_password BOOLEAN NOT NULL DEFAULT 0"))
        if "last_login_at" not in judge_columns:
            connection.execute(text("ALTER TABLE judges ADD COLUMN last_login_at DATETIME NULL"))
        if "attendance_token" not in judge_columns:
            connection.execute(text("ALTER TABLE judges ADD COLUMN attendance_token VARCHAR(64) NULL"))
        if "attendance_confirmed" not in judge_columns:
            connection.execute(text("ALTER TABLE judges ADD COLUMN attendance_confirmed TINYINT(1) NULL"))
        if "needs_parking" not in judge_columns:
            connection.execute(text("ALTER TABLE judges ADD COLUMN needs_parking TINYINT(1) NOT NULL DEFAULT 0"))
        if "attendance_responded_at" not in judge_columns:
            connection.execute(text("ALTER TABLE judges ADD COLUMN attendance_responded_at DATETIME NULL"))
        connection.execute(
            text(
                """
                UPDATE judges
                SET is_active_user = CASE
                    WHEN is_active_user IS NULL THEN 1
                    ELSE is_active_user
                END
                """
            )
        )
        connection.execute(
            text(
                """
                UPDATE judges
                SET role = CASE
                    WHEN role IN ('judge', 'admin', 'superadmin') THEN role
                    WHEN is_admin = 1 THEN 'admin'
                    ELSE 'judge'
                END
                """
            )
        )
        connection.execute(
            text(
                """
                UPDATE judges
                SET
                    can_evaluate_documentation = COALESCE(can_evaluate_documentation, 1),
                    can_evaluate_exposition = COALESCE(can_evaluate_exposition, 1),
                    can_evaluate_english = COALESCE(can_evaluate_english, 0),
                    category_scope = CASE
                        WHEN category_scope IN ('steam', 'emprendimiento', 'ambas') THEN category_scope
                        ELSE 'ambas'
                    END,
                    registered_from_public_form = COALESCE(registered_from_public_form, 0)
                """
            )
        )
        system_tables = set(inspector.get_table_names())
        judge_availability_backfill_done = False
        if "system_settings" in system_tables:
            judge_availability_backfill_done = bool(
                connection.execute(
                    text("SELECT value FROM system_settings WHERE `key` = 'judge_availability_backfill_20260611'")
                ).scalar()
            )

        if not judge_availability_backfill_done:
            connection.execute(
                text(
                    """
                    UPDATE judges
                    SET
                        can_evaluate_english = CASE
                            WHEN LOWER(COALESCE(registration_notes, '')) LIKE '%ingles=si%'
                            THEN 1
                            ELSE COALESCE(can_evaluate_english, 0)
                        END,
                        category_scope = CASE
                            WHEN LOWER(COALESCE(registration_notes, '')) LIKE '%areas=%steam%emprend%' THEN 'ambas'
                            WHEN LOWER(COALESCE(registration_notes, '')) LIKE '%areas=%emprend%steam%' THEN 'ambas'
                            WHEN LOWER(COALESCE(registration_notes, '')) LIKE '%areas=%steam%' THEN 'steam'
                            WHEN LOWER(COALESCE(registration_notes, '')) LIKE '%areas=%emprend%' THEN 'emprendimiento'
                            WHEN category_scope IN ('steam', 'emprendimiento', 'ambas') THEN category_scope
                            ELSE 'ambas'
                        END
                    WHERE registered_from_public_form = 1
                       OR registration_notes IS NOT NULL
                    """
                )
            )

        if not judge_availability_backfill_done and "system_audit_logs" in system_tables:
            connection.execute(
                text(
                    """
                    UPDATE judges
                    SET can_evaluate_english = 1
                    WHERE EXISTS (
                        SELECT 1
                        FROM system_audit_logs
                        WHERE system_audit_logs.entity = 'judge'
                          AND system_audit_logs.entity_id = judges.id
                          AND LOWER(COALESCE(system_audit_logs.detail, '')) LIKE '%ingles=si%'
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    UPDATE judges
                    SET category_scope = 'ambas'
                    WHERE EXISTS (
                        SELECT 1
                        FROM system_audit_logs
                        WHERE system_audit_logs.entity = 'judge'
                          AND system_audit_logs.entity_id = judges.id
                          AND LOWER(COALESCE(system_audit_logs.detail, '')) LIKE '%areas=%steam%emprend%'
                    )
                    OR EXISTS (
                        SELECT 1
                        FROM system_audit_logs
                        WHERE system_audit_logs.entity = 'judge'
                          AND system_audit_logs.entity_id = judges.id
                          AND LOWER(COALESCE(system_audit_logs.detail, '')) LIKE '%areas=%emprend%steam%'
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    UPDATE judges
                    SET category_scope = 'steam'
                    WHERE category_scope = 'ambas'
                      AND EXISTS (
                        SELECT 1
                        FROM system_audit_logs
                        WHERE system_audit_logs.entity = 'judge'
                          AND system_audit_logs.entity_id = judges.id
                          AND LOWER(COALESCE(system_audit_logs.detail, '')) LIKE '%areas=%steam%'
                          AND LOWER(COALESCE(system_audit_logs.detail, '')) NOT LIKE '%emprend%'
                      )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    UPDATE judges
                    SET category_scope = 'emprendimiento'
                    WHERE category_scope = 'ambas'
                      AND EXISTS (
                        SELECT 1
                        FROM system_audit_logs
                        WHERE system_audit_logs.entity = 'judge'
                          AND system_audit_logs.entity_id = judges.id
                          AND LOWER(COALESCE(system_audit_logs.detail, '')) LIKE '%areas=%emprend%'
                          AND LOWER(COALESCE(system_audit_logs.detail, '')) NOT LIKE '%steam%'
                      )
                    """
                )
            )
        if not judge_availability_backfill_done and "system_settings" in system_tables:
            updated_settings = connection.execute(
                text(
                    """
                    UPDATE system_settings
                    SET value = '1', updated_at = CURRENT_TIMESTAMP
                    WHERE `key` = 'judge_availability_backfill_20260611'
                    """
                )
            ).rowcount
            if not updated_settings:
                connection.execute(
                    text(
                        """
                        INSERT INTO system_settings (`key`, value, updated_at)
                        VALUES ('judge_availability_backfill_20260611', '1', CURRENT_TIMESTAMP)
                        """
                    )
                )
        if "assignments" in system_tables:
            assignment_columns = {column["name"] for column in inspector.get_columns("assignments")}
            if "can_evaluate_documentation" not in assignment_columns:
                connection.execute(
                    text("ALTER TABLE assignments ADD COLUMN can_evaluate_documentation BOOLEAN NOT NULL DEFAULT 1")
                )
            if "can_evaluate_exposition" not in assignment_columns:
                connection.execute(
                    text("ALTER TABLE assignments ADD COLUMN can_evaluate_exposition BOOLEAN NOT NULL DEFAULT 1")
                )
            connection.execute(
                text(
                    """
                    UPDATE assignments
                    SET
                        can_evaluate_documentation = COALESCE(can_evaluate_documentation, 1),
                        can_evaluate_exposition = COALESCE(can_evaluate_exposition, 1)
                    """
                )
            )

        if "system_settings" in system_tables:
            existing_permissions = connection.execute(
                text("SELECT `key` FROM system_settings WHERE `key` = :key LIMIT 1"),
                {"key": PERMISSIONS_SETTING_KEY},
            ).first()
            if not existing_permissions:
                connection.execute(
                    text(
                        """
                        INSERT INTO system_settings (`key`, `value`, updated_at)
                        VALUES (:key, :value, CURRENT_TIMESTAMP)
                        """
                    ),
                    {
                        "key": PERMISSIONS_SETTING_KEY,
                        "value": json.dumps(DEFAULT_DEPARTMENT_PERMISSIONS, ensure_ascii=True),
                    },
                )
        connection.execute(
            text(
                """
                UPDATE judges
                SET is_admin = CASE
                    WHEN role IN ('admin', 'superadmin') THEN 1
                    ELSE 0
                END
                """
            )
        )

        project_columns = {column["name"] for column in inspector.get_columns("projects")}
        category_columns = {column["name"] for column in inspector.get_columns("categories")}
        if "rubric_1_evaluation_type_id" not in category_columns:
            connection.execute(text("ALTER TABLE categories ADD COLUMN rubric_1_evaluation_type_id INT NULL"))
        if "rubric_2_evaluation_type_id" not in category_columns:
            connection.execute(text("ALTER TABLE categories ADD COLUMN rubric_2_evaluation_type_id INT NULL"))
        category_column = next((column for column in inspector.get_columns("projects") if column["name"] == "category"), None)
        if category_column and "enum" in str(category_column["type"]).lower():
            connection.execute(text("ALTER TABLE projects MODIFY COLUMN category VARCHAR(60) NOT NULL"))
        if "category" in project_columns:
            connection.execute(text("UPDATE projects SET category='emprendimiento' WHERE category=''"))
        if "representative_phone" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN representative_phone VARCHAR(40) NULL"))
        if "institution_name" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN institution_name VARCHAR(180) NULL"))
        if "grade_level" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN grade_level VARCHAR(60) NULL"))
        if "specialty" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN specialty VARCHAR(120) NULL"))
        if "advisor_name" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN advisor_name VARCHAR(120) NULL"))
        if "advisor_email" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN advisor_email VARCHAR(120) NULL"))
        if "advisor_phone" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN advisor_phone VARCHAR(40) NULL"))
        if "advisor_birth_date" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN advisor_birth_date DATE NULL"))
        if "advisor_gender" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN advisor_gender VARCHAR(20) NULL"))
        if "advisor_specialty" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN advisor_specialty VARCHAR(140) NULL"))
        if "mentor_name" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN mentor_name VARCHAR(120) NULL"))
        if "mentor_identity" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN mentor_identity VARCHAR(40) NULL"))
        if "mentor_birth_date" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN mentor_birth_date DATE NULL"))
        if "mentor_gender" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN mentor_gender VARCHAR(20) NULL"))
        if "mentor_specialty" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN mentor_specialty VARCHAR(140) NULL"))
        if "mentor_email" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN mentor_email VARCHAR(120) NULL"))
        if "mentor_phone" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN mentor_phone VARCHAR(40) NULL"))
        if "project_objective" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN project_objective TEXT NULL"))
        if "expected_impact" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN expected_impact TEXT NULL"))
        if "required_resources" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN required_resources TEXT NULL"))
        if "project_start_date" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN project_start_date DATE NULL"))
        if "project_end_date" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN project_end_date DATE NULL"))
        if "consent_terms" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN consent_terms BOOLEAN NOT NULL DEFAULT 0"))
        if "registration_date" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN registration_date DATE NULL"))
        if "advisor_identity" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN advisor_identity VARCHAR(40) NULL"))
        if "requirements_summary" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN requirements_summary TEXT NULL"))
        if "requirements_other" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN requirements_other VARCHAR(255) NULL"))
        if "section_id" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN section_id INT NULL"))
        if "specialty_id" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN specialty_id INT NULL"))
        if "thematic_axis_id" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN thematic_axis_id INT NULL"))
        if "project_type_id" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN project_type_id INT NULL"))
        if "workshop_id" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN workshop_id INT NULL"))
        if "project_document_path" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN project_document_path VARCHAR(300) NULL"))
        if "campaign_id" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN campaign_id INT NULL"))
        if "project_logo_path" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN project_logo_path VARCHAR(300) NULL"))
        if "is_active" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1"))
        if "logistics_status" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN logistics_status VARCHAR(40) NOT NULL DEFAULT 'pendiente_revision'"))
        if "logistics_notes" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN logistics_notes TEXT NULL"))
        if "logistics_document_ok" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN logistics_document_ok BOOLEAN NOT NULL DEFAULT 0"))
        if "logistics_logo_ok" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN logistics_logo_ok BOOLEAN NOT NULL DEFAULT 0"))
        if "logistics_photos_ok" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN logistics_photos_ok BOOLEAN NOT NULL DEFAULT 0"))
        if "logistics_registration_form_signed_ok" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN logistics_registration_form_signed_ok BOOLEAN NOT NULL DEFAULT 0"))
        if "logistics_student_consents_signed_ok" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN logistics_student_consents_signed_ok BOOLEAN NOT NULL DEFAULT 0"))
        if "logistics_cedula_tutor_ok" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN logistics_cedula_tutor_ok BOOLEAN NOT NULL DEFAULT 0"))
        if "logistics_requirements_reviewed_ok" not in project_columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN logistics_requirements_reviewed_ok BOOLEAN NOT NULL DEFAULT 0"))
        if "logistics_status" in project_columns:
            connection.execute(text("UPDATE projects SET is_active = 0 WHERE logistics_status = 'retirado'"))
            connection.execute(text("UPDATE projects SET logistics_status = 'incompleto' WHERE logistics_status = 'retirado'"))
            connection.execute(text("UPDATE projects SET logistics_status = 'pendiente_revision' WHERE logistics_status = 'inscrito'"))
            connection.execute(text("UPDATE projects SET logistics_status = 'pendiente_revision' WHERE logistics_status = 'revision_logistica'"))

        evaluation_columns_info = inspector.get_columns("evaluations")
        evaluation_columns = {column["name"] for column in evaluation_columns_info}
        evaluation_columns_by_name = {column["name"]: column for column in evaluation_columns_info}
        evaluation_fks = inspector.get_foreign_keys("evaluations")
        for fk_column, referred_table, constraint_name in [
            ("judge_id", "judges", "fk_evaluations_judge_set_null"),
            ("project_id", "projects", "fk_evaluations_project_set_null"),
        ]:
            fk = next(
                (
                    item
                    for item in evaluation_fks
                    if item.get("referred_table") == referred_table
                    and item.get("constrained_columns") == [fk_column]
                ),
                None,
            )
            fk_ondelete = str((fk or {}).get("options", {}).get("ondelete") or "").upper()
            fk_column_info = evaluation_columns_by_name.get(fk_column, {})
            needs_nullable = fk_column_info.get("nullable") is False
            needs_set_null_fk = fk and fk_ondelete != "SET NULL"

            if fk and (needs_nullable or needs_set_null_fk):
                connection.execute(text(f"ALTER TABLE evaluations DROP FOREIGN KEY {fk['name']}"))
                fk = None

            if needs_nullable:
                connection.execute(text(f"ALTER TABLE evaluations MODIFY COLUMN {fk_column} INT NULL"))

            if fk is None:
                connection.execute(
                    text(
                        f"""
                        ALTER TABLE evaluations
                        ADD CONSTRAINT {constraint_name}
                        FOREIGN KEY ({fk_column}) REFERENCES {referred_table} (id)
                        ON DELETE SET NULL
                        """
                    )
                )

        evaluation_type_columns = {column["name"] for column in inspector.get_columns("evaluation_types")}
        if "scale_labels" not in evaluation_type_columns:
            connection.execute(text("ALTER TABLE evaluation_types ADD COLUMN scale_labels TEXT NULL"))
        if "description" not in evaluation_type_columns:
            connection.execute(text("ALTER TABLE evaluation_types ADD COLUMN description TEXT NULL"))
        evaluation_type_column = next(
            (column for column in inspector.get_columns("evaluations") if column["name"] == "evaluation_type"),
            None,
        )
        if evaluation_type_column and "enum" in str(evaluation_type_column["type"]).lower():
            connection.execute(text("ALTER TABLE evaluations MODIFY COLUMN evaluation_type VARCHAR(60) NOT NULL"))

        for criteria_name in ["criteria_1", "criteria_2", "criteria_3", "criteria_4"]:
            if criteria_name in evaluation_columns:
                connection.execute(text(f"ALTER TABLE evaluations MODIFY COLUMN {criteria_name} INT NULL"))
        if "recommendations" not in evaluation_columns:
            connection.execute(text("ALTER TABLE evaluations ADD COLUMN recommendations TEXT NULL"))
        if "max_score" not in evaluation_columns:
            connection.execute(text("ALTER TABLE evaluations ADD COLUMN max_score INT NULL"))
        if "percentage" not in evaluation_columns:
            connection.execute(text("ALTER TABLE evaluations ADD COLUMN percentage FLOAT NULL"))
        if "project_member_id" not in evaluation_columns:
            connection.execute(text("ALTER TABLE evaluations ADD COLUMN project_member_id INT NULL"))
            evaluation_columns.add("project_member_id")

        evaluation_fks = inspector.get_foreign_keys("evaluations")
        member_fk = next(
            (
                item
                for item in evaluation_fks
                if item.get("referred_table") == "project_members"
                and item.get("constrained_columns") == ["project_member_id"]
            ),
            None,
        )
        if member_fk is None and "project_member_id" in evaluation_columns:
            _run_optional_schema_statement(
                connection,
                """
                ALTER TABLE evaluations
                ADD CONSTRAINT fk_evaluations_project_member_set_null
                FOREIGN KEY (project_member_id) REFERENCES project_members (id)
                ON DELETE SET NULL
                """,
                "fk evaluations.project_member_id",
            )

        evaluation_unique_constraints = inspector.get_unique_constraints("evaluations")
        legacy_eval_unique = next(
            (
                item
                for item in evaluation_unique_constraints
                if item.get("name") == "uq_eval_type_per_judge_project"
                or item.get("column_names") == ["judge_id", "project_id", "evaluation_type"]
            ),
            None,
        )
        member_eval_unique = next(
            (
                item
                for item in evaluation_unique_constraints
                if item.get("name") == "uq_eval_type_per_judge_project_member"
                or item.get("column_names")
                == ["judge_id", "project_id", "evaluation_type", "project_member_id"]
            ),
            None,
        )
        if legacy_eval_unique:
            _run_optional_schema_statement(
                connection,
                f"ALTER TABLE evaluations DROP INDEX `{legacy_eval_unique['name']}`",
                "indice unico anterior de evaluaciones",
            )
        if member_eval_unique is None and "project_member_id" in evaluation_columns:
            _run_optional_schema_statement(
                connection,
                """
                ALTER TABLE evaluations
                ADD CONSTRAINT uq_eval_type_per_judge_project_member
                UNIQUE (judge_id, project_id, evaluation_type, project_member_id)
                """,
                "indice unico por integrante evaluado",
            )

        if "project_members" in inspector.get_table_names():
            member_columns = {column["name"] for column in inspector.get_columns("project_members")}
            if "student_number" not in member_columns:
                connection.execute(text("ALTER TABLE project_members ADD COLUMN student_number INT NOT NULL DEFAULT 1"))
            if "identity_number" not in member_columns:
                connection.execute(text("ALTER TABLE project_members ADD COLUMN identity_number VARCHAR(40) NULL"))
            if "birth_date" not in member_columns:
                connection.execute(text("ALTER TABLE project_members ADD COLUMN birth_date DATE NULL"))
            if "gender" not in member_columns:
                connection.execute(text("ALTER TABLE project_members ADD COLUMN gender VARCHAR(20) NULL"))
            if "specialty_id" not in member_columns:
                connection.execute(text("ALTER TABLE project_members ADD COLUMN specialty_id INT NULL"))
            if "specialty" not in member_columns:
                connection.execute(text("ALTER TABLE project_members ADD COLUMN specialty VARCHAR(140) NULL"))
            if "section_name" not in member_columns:
                connection.execute(text("ALTER TABLE project_members ADD COLUMN section_name VARCHAR(30) NULL"))
            if "has_dining_scholarship" not in member_columns:
                connection.execute(
                    text("ALTER TABLE project_members ADD COLUMN has_dining_scholarship BOOLEAN NOT NULL DEFAULT 0")
                )
            if "participates_in_english" not in member_columns:
                connection.execute(
                    text("ALTER TABLE project_members ADD COLUMN participates_in_english BOOLEAN NOT NULL DEFAULT 0")
                )
            if "phone" not in member_columns:
                connection.execute(text("ALTER TABLE project_members ADD COLUMN phone VARCHAR(40) NULL"))
            if "email" not in member_columns:
                connection.execute(text("ALTER TABLE project_members ADD COLUMN email VARCHAR(120) NULL"))
            if "role" in member_columns:
                connection.execute(text("ALTER TABLE project_members MODIFY COLUMN role VARCHAR(120) NULL"))
            if "photo_url" in member_columns:
                connection.execute(text("ALTER TABLE project_members MODIFY COLUMN photo_url VARCHAR(300) NULL"))

        if "rubric_criteria" in inspector.get_table_names():
            rubric_columns = {column["name"] for column in inspector.get_columns("rubric_criteria")}
            if "section_name" not in rubric_columns:
                connection.execute(text("ALTER TABLE rubric_criteria ADD COLUMN section_name VARCHAR(180) NULL"))
            if "section_sort_order" not in rubric_columns:
                connection.execute(text("ALTER TABLE rubric_criteria ADD COLUMN section_sort_order INT NOT NULL DEFAULT 0"))
            if "name" in rubric_columns:
                connection.execute(text("ALTER TABLE rubric_criteria MODIFY COLUMN name VARCHAR(500) NOT NULL"))

        if "project_document_revisions" not in inspector.get_table_names():
            connection.execute(
                text(
                    """
                    CREATE TABLE project_document_revisions (
                        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        project_id INT NOT NULL,
                        document_path VARCHAR(300) NOT NULL,
                        justification TEXT NOT NULL,
                        submitted_by_name VARCHAR(120) NOT NULL,
                        status VARCHAR(20) NOT NULL DEFAULT 'pendiente',
                        admin_notes TEXT NULL,
                        reviewed_by_id INT NULL,
                        reviewed_at DATETIME NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_doc_revision_project (project_id),
                        INDEX idx_doc_revision_status (status),
                        CONSTRAINT fk_doc_revision_project FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
                        CONSTRAINT fk_doc_revision_reviewer FOREIGN KEY (reviewed_by_id) REFERENCES judges (id) ON DELETE SET NULL
                    )
                    """
                )
            )

        if "assignments" in inspector.get_table_names():
            assignment_columns = [c["name"] for c in inspector.get_columns("assignments")]
            if "status" not in assignment_columns:
                _run_optional_schema_statement(
                    connection,
                    "ALTER TABLE assignments ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'confirmed'",
                    "assignments.status",
                )
                _run_optional_schema_statement(
                    connection,
                    "CREATE INDEX IF NOT EXISTS idx_assignments_status ON assignments (status)",
                    "assignments.status index",
                )

        if "project_document_revisions" in inspector.get_table_names():
            doc_rev_columns = [c["name"] for c in inspector.get_columns("project_document_revisions")]
            if "replaced_document_path" not in doc_rev_columns:
                _run_optional_schema_statement(
                    connection,
                    "ALTER TABLE project_document_revisions ADD COLUMN replaced_document_path VARCHAR(300) NULL",
                    "project_document_revisions.replaced_document_path",
                )
            if "notification_sent" not in doc_rev_columns:
                _run_optional_schema_statement(
                    connection,
                    "ALTER TABLE project_document_revisions ADD COLUMN notification_sent TINYINT(1) NOT NULL DEFAULT 0",
                    "project_document_revisions.notification_sent",
                )

        if "project_member_changes" in inspector.get_table_names():
            member_change_fks = inspector.get_foreign_keys("project_member_changes")
            member_fk = next(
                (
                    fk
                    for fk in member_change_fks
                    if fk.get("referred_table") == "project_members" and fk.get("constrained_columns") == ["member_id"]
                ),
                None,
            )
            member_fk_ondelete = (member_fk or {}).get("options", {}).get("ondelete")
            if member_fk and str(member_fk_ondelete).upper() != "SET NULL":
                fk_name = member_fk["name"]
                connection.execute(text(f"ALTER TABLE project_member_changes DROP FOREIGN KEY {fk_name}"))
                connection.execute(
                    text(
                        """
                        ALTER TABLE project_member_changes
                        ADD CONSTRAINT project_member_changes_ibfk_2
                        FOREIGN KEY (member_id) REFERENCES project_members (id)
                        ON DELETE SET NULL
                        """
                    )
                )

        if "project_members" in inspector.get_table_names():
            pm_cols = {c["name"] for c in inspector.get_columns("project_members")}
            if "consent_signed_ok" not in pm_cols:
                _run_optional_schema_statement(
                    connection,
                    "ALTER TABLE project_members ADD COLUMN consent_signed_ok TINYINT(1) NOT NULL DEFAULT 0",
                    "project_members.consent_signed_ok",
                )
            if "cedula_copies_ok" not in pm_cols:
                _run_optional_schema_statement(
                    connection,
                    "ALTER TABLE project_members ADD COLUMN cedula_copies_ok TINYINT(1) NOT NULL DEFAULT 0",
                    "project_members.cedula_copies_ok",
                )

        if "project_member_edit_requests" in inspector.get_table_names():
            mer_cols = {c["name"] for c in inspector.get_columns("project_member_edit_requests")}
            if "justification" not in mer_cols:
                _run_optional_schema_statement(
                    connection,
                    "ALTER TABLE project_member_edit_requests ADD COLUMN justification TEXT NULL",
                    "project_member_edit_requests.justification",
                )
