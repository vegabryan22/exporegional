import unittest
from pathlib import Path

from app.controllers.admin_controller import (
    ACTION_MODULE_MAP,
    ADMIN_DEPARTMENT_MODULE_ACCESS,
    _sync_project_logistics_status,
)
from app.models.project import Project


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

    def test_logistics_template_does_not_offer_resource_validation(self):
        template = Path("app/templates/admin/projects.html").read_text(encoding="utf-8")
        requirements_template = Path("app/templates/admin/requirements.html").read_text(encoding="utf-8")

        self.assertNotIn('name="logistics_requirements_reviewed_ok"', template)
        self.assertIn('name="requirements_internet_ok"', requirements_template)
        self.assertIn('name="requirements_resources_ok"', requirements_template)

    def test_logistics_department_does_not_receive_requirements_module(self):
        self.assertNotIn("requirements", ADMIN_DEPARTMENT_MODULE_ACCESS["logistica"])
        self.assertEqual(ACTION_MODULE_MAP["update_project_requirements"], "requirements")


if __name__ == "__main__":
    unittest.main()
