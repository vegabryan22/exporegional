import json
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
    _build_exposition_usher_report_rows,
    _build_advisor_stats,
    _person_name_title,
    _project_report_rows,
    _sync_project_logistics_status,
    _sync_project_photo_validation,
)
from app.controllers.project_controller import _build_requirement_items
from app.models.assignment import Assignment
from app.models.judge import Judge
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.tutor import Tutor


class RequirementsSeparationTest(unittest.TestCase):
    def test_tutor_statistics_centralize_projects_students_and_pending_work(self):
        complete = Project(
            id=31,
            title="Proyecto completo",
            team_name="Equipo A",
            advisor_name="MARÍA ELENA DEL RÍO",
            advisor_identity="123456789",
            advisor_email="tutora@example.com",
            advisor_phone="88880000",
            advisor_specialty="Informática",
            category="steam",
            is_active=True,
            logistics_status="completo",
            requirements_status="completo",
            project_document_path="document.pdf",
            project_logo_path="logo.png",
            logistics_document_ok=True,
            logistics_logo_ok=True,
            logistics_photos_ok=True,
            logistics_registration_form_signed_ok=True,
        )
        complete.members = [
            ProjectMember(full_name="Estudiante", student_number=1, section_name="12-1", photo_url="student.jpg", consent_signed_ok=True)
        ]
        pending = Project(
            id=32,
            title="Proyecto pendiente",
            team_name="Equipo B",
            advisor_name="María Elena del Río",
            advisor_identity="123456789",
            advisor_email="tutora@example.com",
            category="emprendimiento",
            is_active=True,
            logistics_status="incompleto",
            requirements_status="pendiente_revision",
        )
        pending.members = [ProjectMember(full_name="Otro", student_number=1, section_name="11-2")]

        tutors = _build_advisor_stats([complete, pending])

        self.assertEqual(1, len(tutors))
        self.assertEqual("María Elena del Río", tutors[0]["name"])
        self.assertEqual(2, tutors[0]["total"])
        self.assertEqual(2, tutors[0]["students"])
        self.assertEqual(1, tutors[0]["completed"])
        self.assertEqual(1, tutors[0]["pending"])
        self.assertEqual("11-2, 12-1", tutors[0]["sections_label"])

    def test_tutors_page_has_filters_statistics_and_excel(self):
        template = Path("app/templates/admin/tutors.html").read_text(encoding="utf-8")

        self.assertIn("tutors_summary", template)
        self.assertIn("tutors-filter-text", template)
        self.assertIn("tutors_report_excel", template)
        self.assertIn('name="action" value="update_advisor"', template)
        self.assertIn('name="action" value="toggle_tutor"', template)

    def test_registration_uses_private_central_tutor_catalog(self):
        template = Path("app/templates/public/register_project.html").read_text(encoding="utf-8")

        self.assertIn('name="tutor_mode" value="existing"', template)
        self.assertIn('name="tutor_id"', template)
        self.assertIn("Registrar otro tutor", template)
        self.assertIn("La información privada permanece protegida", template)
        self.assertNotIn("tutor.identity_number", template)
        self.assertNotIn("tutor.birth_date", template)
        self.assertEqual("tutors", Tutor.__tablename__)
        self.assertIn("toggle_tutor", ACTION_MODULE_MAP)

    def test_member_photos_are_validated_automatically(self):
        project = Project(logistics_photos_ok=False)
        project.members = [
            ProjectMember(full_name="Estudiante uno", student_number=1, photo_url="uploads/uno.jpg"),
            ProjectMember(full_name="Estudiante dos", student_number=2, photo_url="uploads/dos.jpg"),
        ]

        self.assertTrue(_sync_project_photo_validation(project))
        self.assertTrue(project.logistics_photos_ok)

        project.members[1].photo_url = None

        self.assertFalse(_sync_project_photo_validation(project))
        self.assertFalse(project.logistics_photos_ok)

    def test_person_names_are_exported_with_natural_capitalization(self):
        self.assertEqual("María José de la Cruz", _person_name_title("MARÍA JOSÉ DE LA CRUZ"))
        self.assertEqual("Ana-María del Río", _person_name_title("ana-maría DEL RÍO"))

    def test_projects_report_contains_projects_and_members(self):
        project = Project(
            id=7,
            title="Proyecto de prueba",
            team_name="Equipo",
            representative_name="JUAN CARLOS DE LA O",
            representative_email="representante@example.com",
            advisor_name="MARÍA ELENA DEL RÍO",
            category="steam",
            description="Descripción",
            is_active=True,
            logistics_status="completo",
            requirements_status="completo",
        )
        project.members = [
            ProjectMember(
                student_number=1,
                full_name="ANA SOFÍA DE LOS ÁNGELES",
                section_name="12-1",
                specialty="Redes",
            )
        ]

        projects, members = _project_report_rows([project], {"steam": "STEAM"})

        self.assertEqual("Juan Carlos de la O", projects[0]["representative"])
        self.assertEqual("María Elena del Río", projects[0]["advisor"])
        self.assertEqual("Ana Sofía de los Ángeles", members[0]["name"])
        self.assertEqual("12-1", members[0]["section"])

    def test_projects_page_links_general_excel_report(self):
        template = Path("app/templates/admin/projects.html").read_text(encoding="utf-8")

        self.assertIn("projects_report_excel", template)
        self.assertIn("Reporte de proyectos inscritos", template)
        self.assertIn("Descargar Excel", template)

    def test_registration_builds_structured_requirement_items(self):
        form_data = {
            "requirement_item_name": ["Mesa de exhibición", "Extensión eléctrica"],
            "requirement_item_quantity": ["2", "1"],
            "requirement_item_unit": ["unidades", "unidad"],
            "requirement_item_notes": ["De 1,80 m", "De 10 metros"],
        }

        items = _build_requirement_items(form_data)

        self.assertEqual(2, len(items))
        self.assertEqual("Mesa de exhibición", items[0]["name"])
        self.assertEqual("2", items[0]["quantity"])
        self.assertEqual("unidades", items[0]["unit"])
        self.assertFalse(items[0]["confirmed"])

    def test_legacy_resource_text_is_preserved_for_detailing(self):
        project = Project(
            required_resources="Son tres estudiantes",
            requirements_resources_ok=False,
        )

        self.assertEqual(1, len(project.detailed_requirement_items))
        self.assertEqual("Son tres estudiantes", project.detailed_requirement_items[0]["name"])
        self.assertTrue(project.detailed_requirement_items[0]["legacy"])
        self.assertIn("pendiente de desglosar", project.detailed_requirement_items[0]["notes"])

    def test_requested_resources_have_their_own_completion_state(self):
        project = Project(
            requirements_summary="corriente, internet",
            requirements_items_json=json.dumps(
                [
                    {
                        "id": "item-1",
                        "name": "Mesa de exhibición",
                        "quantity": "2",
                        "unit": "unidades",
                        "notes": "De 1,80 m",
                        "confirmed": False,
                    }
                ]
            ),
            requirements_status="completo",
            requirements_current_ok=True,
            requirements_internet_ok=False,
        )

        self.assertEqual(
            project.requirements_missing_items,
            ["Acceso a internet", "Insumos pendientes: Mesa de exhibición"],
        )
        self.assertFalse(project.requirements_complete)

        project.requirements_internet_ok = True
        project.requirements_items_json = json.dumps(
            [
                {
                    "id": "item-1",
                    "name": "Mesa de exhibición",
                    "quantity": "2",
                    "unit": "unidades",
                    "notes": "De 1,80 m",
                    "confirmed": True,
                }
            ]
        )

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
        project.members = [
            ProjectMember(
                full_name="Estudiante listo",
                student_number=1,
                photo_url="uploads/student.jpg",
                consent_signed_ok=True,
            )
        ]

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
                        (2, 'document.pdf', 1, 'logo.png', 0, 1, 1, 'completo'),
                        (3, 'document.pdf', 1, 'logo.png', 1, 0, 1, 'incompleto')
                    """
                )
            )
            connection.execute(
                text(
                    """
                    INSERT INTO project_members VALUES
                        (1, 1, 'student.jpg', 1),
                        (2, 2, 'student.jpg', 1),
                        (3, 3, 'student.jpg', 1)
                    """
                )
            )

            _reconcile_existing_logistics_statuses(connection)
            rows = connection.execute(
                text("SELECT id, logistics_status, logistics_photos_ok FROM projects")
            )
            statuses = {row.id: row.logistics_status for row in rows}
            photo_flags = {
                row.id: row.logistics_photos_ok
                for row in connection.execute(text("SELECT id, logistics_photos_ok FROM projects"))
            }

        self.assertEqual("completo", statuses[1])
        self.assertEqual("incompleto", statuses[2])
        self.assertEqual("completo", statuses[3])
        self.assertEqual(1, photo_flags[3])
        engine.dispose()

    def test_logistics_template_does_not_offer_resource_validation(self):
        template = Path("app/templates/admin/projects.html").read_text(encoding="utf-8")
        requirements_template = Path("app/templates/admin/requirements.html").read_text(encoding="utf-8")

        self.assertNotIn('name="logistics_requirements_reviewed_ok"', template)
        self.assertIn('name="requirements_internet_ok"', requirements_template)
        self.assertIn('name="requirement_item_confirmed"', requirements_template)
        self.assertIn("Detalle de insumos y materiales", requirements_template)

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

    def test_usher_report_contains_only_confirmed_exposition_assignments(self):
        exposition_judge = Judge(
            id=1,
            full_name="Juez Exposición",
            email="expo@example.com",
            phone="8888-8888",
            role=Judge.ROLE_JUDGE,
            password_hash="test",
            is_active_user=True,
            attendance_confirmed=True,
        )
        documentation_judge = Judge(
            id=2,
            full_name="Juez Documentación",
            email="doc@example.com",
            role=Judge.ROLE_JUDGE,
            password_hash="test",
            is_active_user=True,
            attendance_confirmed=True,
        )
        project = Project(
            id=30,
            title="Proyecto para exposición",
            team_name="Equipo",
            category="steam",
            is_active=True,
        )
        exposition_assignment = Assignment(
            judge_id=1,
            project_id=30,
            status=Assignment.STATUS_CONFIRMED,
            can_evaluate_documentation=True,
            can_evaluate_exposition=True,
        )
        exposition_assignment.judge = exposition_judge
        documentation_assignment = Assignment(
            judge_id=2,
            project_id=30,
            status=Assignment.STATUS_CONFIRMED,
            can_evaluate_documentation=True,
            can_evaluate_exposition=False,
        )
        documentation_assignment.judge = documentation_judge

        rows = _build_exposition_usher_report_rows(
            {
                "projects": [project],
                "assignments": [exposition_assignment, documentation_assignment],
                "category_map": {"steam": "STEAM"},
            }
        )

        self.assertEqual(1, len(rows))
        self.assertEqual("Juez Exposición", rows[0]["judge"])
        self.assertEqual("Proyecto para exposición", rows[0]["project"])
        self.assertEqual("", rows[0]["location"])

    def test_assignments_page_links_usher_report(self):
        template = Path("app/templates/admin/assignments.html").read_text(encoding="utf-8")

        self.assertIn("exposition_usher_report_excel", template)
        self.assertIn("Excel edecanes · exposición", template)

    def test_logistics_department_does_not_receive_requirements_module(self):
        self.assertNotIn("requirements", ADMIN_DEPARTMENT_MODULE_ACCESS["logistica"])
        self.assertEqual(ACTION_MODULE_MAP["update_project_requirements"], "requirements")


if __name__ == "__main__":
    unittest.main()
