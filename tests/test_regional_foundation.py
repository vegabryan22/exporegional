import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_app
from app.extensions import db
from app.models.institution import Institution
from app.models.judge import Judge
from app.models.project import Project
from app.models.project_status_history import ProjectStatusHistory
from app.services.regional_project_service import RegionalTransitionError, transition_project


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

    def test_school_coordinator_can_only_submit_own_project(self):
        coordinator = Judge(id=20, role=Judge.ROLE_SCHOOL_COORDINATOR, institution_id=7)
        project = Project(id=30, institution_id=7, regional_status=Project.STATUS_DRAFT)

        with patch.object(db.session, "add"):
            history = transition_project(project, Project.STATUS_SUBMITTED, coordinator, "Listo")

        self.assertEqual(Project.STATUS_SUBMITTED, project.regional_status)
        self.assertEqual(Project.STATUS_DRAFT, history.from_status)
        self.assertEqual(20, history.changed_by_id)

    def test_school_coordinator_cannot_submit_another_school_project(self):
        coordinator = Judge(id=20, role=Judge.ROLE_SCHOOL_COORDINATOR, institution_id=7)
        project = Project(id=30, institution_id=8, regional_status=Project.STATUS_DRAFT)

        with self.assertRaises(RegionalTransitionError):
            transition_project(project, Project.STATUS_SUBMITTED, coordinator)

    def test_regional_admin_can_review_and_approve_in_sequence(self):
        admin = Judge(id=1, role=Judge.ROLE_SUPERADMIN, is_admin=True)
        project = Project(id=30, regional_status=Project.STATUS_SUBMITTED)

        with patch.object(db.session, "add"):
            transition_project(project, Project.STATUS_RECEIVED, admin)
            transition_project(project, Project.STATUS_UNDER_REVIEW, admin)
            transition_project(project, Project.STATUS_APPROVED, admin)

        self.assertEqual(Project.STATUS_APPROVED, project.regional_status)
        self.assertEqual(1, project.approved_by_id)

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

    def test_regional_review_page_renders_for_admin(self):
        app = create_app()
        app.config["TESTING"] = True

        with app.app_context():
            admin = Judge(full_name="Revisor regional", email="review-page-test@example.com", role=Judge.ROLE_SUPERADMIN, password_hash="test-only", is_active_user=True, is_admin=True)
            db.session.add(admin)
            db.session.flush()
            with app.test_client() as client:
                with client.session_transaction() as session:
                    session["_user_id"] = str(admin.id)
                    session["_fresh"] = True
                response = client.get("/admin/revision-regional")
            db.session.rollback()

        self.assertEqual(200, response.status_code)
        self.assertIn("Bandeja de revisión regional", response.get_data(as_text=True))

    def test_school_dashboard_is_scoped_to_coordinator_institution(self):
        app = create_app()
        app.config["TESTING"] = True

        with app.app_context():
            own_school = Institution(code="TEST-OWN", name="Colegio propio", responsible_name="Responsable", responsible_email="own@example.com", is_active=True)
            other_school = Institution(code="TEST-OTHER", name="Colegio ajeno", responsible_name="Responsable", responsible_email="other@example.com", is_active=True)
            db.session.add_all([own_school, other_school])
            db.session.flush()
            coordinator = Judge(full_name="Coordinador", email="scope-test@example.com", role=Judge.ROLE_SCHOOL_COORDINATOR, institution_id=own_school.id, password_hash="test-only", is_active_user=True)
            own_project = Project(title="Proyecto visible", team_name="Equipo A", representative_name="Estudiante", representative_email="a@example.com", institution_id=own_school.id, institution_name=own_school.name, category="steam", description="Visible", regional_status=Project.STATUS_DRAFT)
            other_project = Project(title="Proyecto oculto", team_name="Equipo B", representative_name="Estudiante", representative_email="b@example.com", institution_id=other_school.id, institution_name=other_school.name, category="steam", description="Oculto", regional_status=Project.STATUS_DRAFT)
            db.session.add_all([coordinator, own_project, other_project])
            db.session.flush()

            with app.test_client() as client:
                with client.session_transaction() as session:
                    session["_user_id"] = str(coordinator.id)
                    session["_fresh"] = True
                response = client.get("/colegio/panel")

            db.session.rollback()

        body = response.get_data(as_text=True)
        self.assertEqual(200, response.status_code)
        self.assertIn("Proyecto visible", body)
        self.assertNotIn("Proyecto oculto", body)


if __name__ == "__main__":
    unittest.main()
