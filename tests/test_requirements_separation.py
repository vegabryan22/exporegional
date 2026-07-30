import unittest
from pathlib import Path

from sqlalchemy import create_engine, text

from app import _reconcile_existing_logistics_statuses
from app.controllers.admin_controller import (
    ACTION_MODULE_MAP,
    ADMIN_DEPARTMENT_MODULE_ACCESS,
    _build_logistics_pending_report_rows,
    _build_project_logistics_summary,
    _build_tutor_logistics_reminder_payload,
    _sync_project_logistics_status,
)
from app.models.project import Project
from app.models.project_member import ProjectMember


class RequirementsSeparationTest(unittest.TestCase):
    def test_requested_resources_have_their_own_completion_state(self):
        project = Project(
            requirements_summary="corriente, internet",
            required_resources="Mesa de exhibición",
            requirements_status="completo",
            requirements_current_ok=True,
            requirements_internet_ok=False,
            requirements_resources_ok=False,
        )

        self.assertEqual(
            project.requirements_missing_items,
            ["Acceso a internet", "Insumos o recursos detallados"],
        )
        self.assertFalse(project.requirements_complete)

        project.requirements_internet_ok = True
        project.requirements_resources_ok = True

        self.assertTrue(project.requirements_complete)

    def test_logistics_completion_does_not_depend_on_resource_requirements(self):
        project = Project(
            project_document_path="uploads/projects/document.pdf",
            project_logo_path="uploads/projects/logo.png",
            logistics_document_ok=True,
            logistics_logo_ok=True,
            logistics_photos_ok=True,
            logistics_registration_form_signed_ok=True,
            logistics_student_consents_signed_ok=True,
            logistics_requirements_reviewed_ok=False,
        )

        self.assertTrue(project.logistics_requirements_complete)

    def test_logistics_status_is_completed_automatically(self):
        project = Project(
            project_document_path="uploads/projects/document.pdf",
            project_logo_path="uploads/projects/logo.png",
            logistics_document_ok=True,
            logistics_logo_ok=True,
            logistics_photos_ok=True,
            logistics_registration_form_signed_ok=True,
            logistics_student_consents_signed_ok=True,
            logistics_status="pendiente_revision",
        )

        missing_items = _sync_project_logistics_status(project)

        self.assertEqual([], missing_items)
        self.assertEqual("completo", project.logistics_status)

        project.logistics_logo_ok = False
        missing_items = _sync_project_logistics_status(project)

        self.assertIn("logo validado", missing_items)
        self.assertEqual("incompleto", project.logistics_status)

    def test_existing_ready_projects_are_reconciled(self):
        engine = create_engine("sqlite://")
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    CREATE TABLE projects (
                        id INTEGER PRIMARY KEY,
                        project_document_path TEXT,
                        logistics_document_ok INTEGER,
                        project_logo_path TEXT,
                        logistics_logo_ok INTEGER,
                        logistics_photos_ok INTEGER,
                        logistics_registration_form_signed_ok INTEGER,
                        logistics_status TEXT
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    CREATE TABLE project_members (
                        id INTEGER PRIMARY KEY,
                        project_id INTEGER,
                        photo_url TEXT,
                        consent_signed_ok INTEGER
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    INSERT INTO projects VALUES
                        (1, 'document.pdf', 1, 'logo.png', 1, 1, 1, 'pendiente_revision'),
                        (2, 'document.pdf', 1, 'logo.png', 0, 1, 1, 'completo')
                    """
                )
            )
            connection.execute(
                text(
                    """
                    INSERT INTO project_members VALUES
                        (1, 1, 'student.jpg', 1),
                        (2, 2, 'student.jpg', 1)
                    """
                )
            )

            _reconcile_existing_logistics_statuses(connection)
            statuses = {
                row.id: row.logistics_status
                for row in connection.execute(text("SELECT id, logistics_status FROM projects"))
            }

        self.assertEqual("completo", statuses[1])
        self.assertEqual("incompleto", statuses[2])
        engine.dispose()

    def test_logistics_template_does_not_offer_resource_validation(self):
        template = Path("app/templates/admin/projects.html").read_text(encoding="utf-8")
        requirements_template = Path("app/templates/admin/requirements.html").read_text(encoding="utf-8")

        self.assertNotIn('name="logistics_requirements_reviewed_ok"', template)
        self.assertIn('name="requirements_internet_ok"', requirements_template)
        self.assertIn('name="requirements_resources_ok"', requirements_template)

    def test_projects_can_be_filtered_by_advisor(self):
        template = Path("app/templates/admin/projects.html").read_text(encoding="utf-8")

        self.assertIn('id="projects-filter-advisor"', template)
        self.assertIn("data-project-advisor=", template)
        self.assertIn("matchesAdvisor", template)

    def test_project_summary_reports_completed_and_missing_documents(self):
        complete = Project(
            id=1,
            is_active=True,
            logistics_status="completo",
            project_document_path="document.pdf",
            project_logo_path="logo.png",
            logistics_document_ok=True,
            logistics_logo_ok=True,
            logistics_photos_ok=True,
            logistics_registration_form_signed_ok=True,
        )
        pending = Project(id=2, is_active=True, logistics_status="pendiente_revision")
        inactive = Project(id=3, is_active=False, logistics_status="incompleto")

        summary = _build_project_logistics_summary([complete, pending, inactive])

        self.assertEqual(1, summary["completed"])
        self.assertEqual(1, summary["pending"])
        self.assertEqual(1, summary["inactive"])
        self.assertIn("documento digital adjunto", summary["missing_by_project"][2])

    def test_logistics_report_identifies_each_affected_student(self):
        project = Project(
            id=10,
            title="Proyecto de prueba",
            team_name="Equipo ExpoTEC",
            advisor_name="Tutor Ejemplo",
            is_active=True,
            project_document_path="document.pdf",
            project_logo_path="logo.png",
            logistics_document_ok=True,
            logistics_logo_ok=True,
            logistics_photos_ok=False,
            logistics_registration_form_signed_ok=True,
        )
        project.members = [
            ProjectMember(
                full_name="Estudiante Ejemplo",
                section_name="12-1",
                student_number=1,
                photo_url=None,
                consent_signed_ok=True,
            )
        ]

        rows = _build_logistics_pending_report_rows([project], report_type="photo")

        self.assertEqual(1, len(rows))
        self.assertEqual("Fotografía de integrante", rows[0]["pending"])
        self.assertEqual("Estudiante Ejemplo", rows[0]["name"])
        self.assertEqual("12-1", rows[0]["section"])
        self.assertEqual("Proyecto de prueba", rows[0]["project"])
        self.assertEqual("Tutor Ejemplo", rows[0]["tutor"])

    def test_overview_pending_counters_download_reports(self):
        template = Path("app/templates/admin/overview.html").read_text(encoding="utf-8")
        controller = Path("app/controllers/admin_controller.py").read_text(encoding="utf-8")

        self.assertIn("logistics_pending_report_excel", template)
        self.assertIn("Descargar reporte detallado de pendientes", template)
        self.assertNotIn(
            'worksheet.auto_filter.ref = f"A5:E{max(worksheet.max_row, 5)}"',
            controller,
        )

    def test_reminder_center_supports_every_audience(self):
        template = Path("app/templates/admin/logistics_reminder.html").read_text(encoding="utf-8")

        self.assertIn('value="students"', template)
        self.assertIn('value="tutors"', template)
        self.assertIn('value="all"', template)
        self.assertIn('name="project_ids"', template)
        self.assertIn("Correo para tutores", template)
        self.assertIn("reminder-batch-progress", template)
        self.assertIn("var batchSize = 1", template)
        self.assertIn("await fetch", template)

    def test_tutor_reminder_contains_group_and_student_pending_items(self):
        from app import create_app

        app = create_app()
        project = Project(
            id=20,
            title="Proyecto con pendientes",
            team_name="Equipo",
            advisor_name="Tutor Ejemplo",
            is_active=True,
            project_logo_path=None,
            logistics_document_ok=False,
            logistics_registration_form_signed_ok=False,
            logistics_cedula_tutor_ok=False,
        )
        project.members = [
            ProjectMember(
                full_name="Estudiante Ejemplo",
                section_name="12-2",
                student_number=1,
                photo_url=None,
                consent_signed_ok=False,
                cedula_encargado_ok=False,
                cedula_estudiante_ok=False,
            )
        ]

        with app.test_request_context("/admin/proyectos/recordatorio"):
            payload = _build_tutor_logistics_reminder_payload(
                project,
                deadline=None,
                institution_name="ExpoTécnica",
            )

        self.assertIsNotNone(payload)
        self.assertIn("Cédula del tutor", payload["missing_group"])
        self.assertEqual("Estudiante Ejemplo", payload["member_missing"][0]["member"].full_name)
        self.assertIn("Consentimiento informado", payload["member_missing"][0]["items"])

    def test_logistics_department_does_not_receive_requirements_module(self):
        self.assertNotIn("requirements", ADMIN_DEPARTMENT_MODULE_ACCESS["logistica"])
        self.assertEqual(ACTION_MODULE_MAP["update_project_requirements"], "requirements")


if __name__ == "__main__":
    unittest.main()
