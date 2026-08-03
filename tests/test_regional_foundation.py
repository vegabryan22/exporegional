import unittest
from pathlib import Path

from app import create_app
from app.extensions import db
from app.models.institution import Institution
from app.models.judge import Judge
from app.models.project import Project
from app.models.project_status_history import ProjectStatusHistory


class RegionalFoundationTests(unittest.TestCase):
    def test_institution_exposes_regional_participation_fields(self):
        school = Institution(
            code="CTP-001",
            name="Colegio de prueba",
            responsible_name="Responsable",
            responsible_email="responsable@example.com",
            participation_status=Institution.STATUS_ENABLED,
            uses_institutional_platform=True,
        )

        self.assertEqual("Habilitado", school.participation_status_label)
        self.assertTrue(school.uses_institutional_platform)

    def test_project_origin_and_status_labels(self):
        project = Project(
            origin=Project.ORIGIN_INSTITUTIONAL_API,
            regional_status=Project.STATUS_RECEIVED,
        )

        self.assertEqual("Importación institucional", project.origin_label)
        self.assertEqual("Recibido", project.regional_status_label)

    def test_school_coordinator_is_a_distinct_role(self):
        user = Judge(role=Judge.ROLE_SCHOOL_COORDINATOR)

        self.assertEqual("Coordinador de colegio", user.role_label)
        self.assertFalse(user.has_admin_access)

    def test_status_history_model_is_linked_to_project(self):
        history = ProjectStatusHistory(from_status=Project.STATUS_DRAFT, to_status=Project.STATUS_SUBMITTED)

        self.assertEqual(Project.STATUS_SUBMITTED, history.to_status)

    def test_visible_branding_no_longer_names_the_original_school(self):
        paths = [
            Path("app/templates/base.html"),
            Path("app/templates/public/home_intro.html"),
            Path("app/templates/public/home_projects.html"),
            Path("app/templates/auth/login.html"),
        ]
        visible_source = "\n".join(path.read_text(encoding="utf-8") for path in paths)

        self.assertNotIn("Roberto Gamboa", visible_source)
        self.assertNotIn("CTPRGV", visible_source)
        self.assertIn("ExpoTécnica Regional", visible_source)

    def test_institutions_admin_page_renders(self):
        app = create_app()
        app.config["TESTING"] = True

        with app.app_context():
            admin = Judge(
                full_name="Administrador regional de prueba",
                email="regional-page-test@example.com",
                role=Judge.ROLE_SUPERADMIN,
                password_hash="test-only",
                is_active_user=True,
                is_admin=True,
            )
            db.session.add(admin)
            db.session.flush()

            with app.test_client() as client:
                with client.session_transaction() as session:
                    session["_user_id"] = str(admin.id)
                    session["_fresh"] = True
                response = client.get("/admin/colegios")

            db.session.rollback()

        self.assertEqual(200, response.status_code)
        self.assertIn("Colegios participantes", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
