import hashlib
import io
import unittest
from pathlib import Path
from unittest.mock import patch

from flask import current_app

from app import create_app
from app.extensions import db
from app.models.institution import Institution
from app.models.institution_api_credential import InstitutionApiCredential
from app.models.category import Category
from app.models.judge import Judge
from app.models.project import Project
from app.models.project_import_event import ProjectImportEvent
from app.models.project_status_history import ProjectStatusHistory
from app.services.regional_project_service import RegionalTransitionError, transition_project


class RegionalFoundationTests(unittest.TestCase):
    def test_api_requires_bearer_credential(self):
        app = create_app()
        app.config["TESTING"] = True

        with app.test_client() as client:
            response = client.post("/api/v1/regional-projects", json={})

        self.assertEqual(401, response.status_code)
        self.assertEqual("missing_credentials", response.get_json()["error"]["code"])

    def test_api_import_is_scoped_and_idempotent(self):
        app = create_app()
        app.config["TESTING"] = True
        token = "regional-test-token"

        with app.app_context():
            school = Institution(code="API-TEST", name="Colegio API", responsible_name="Responsable", responsible_email="api@example.com", is_active=True)
            category = Category.query.filter_by(code="steam").first()
            self.assertIsNotNone(category)
            db.session.add(school)
            db.session.flush()
            db.session.add(InstitutionApiCredential(institution_id=school.id, name="Prueba", token_hash=hashlib.sha256(token.encode()).hexdigest(), token_prefix="regional"))
            db.session.flush()
            payload = {
                "external_project_id": "API-TEST-001",
                "title": "Ganador institucional",
                "team_name": "Equipo API",
                "category_code": category.code,
                "description": "Proyecto enviado por contrato JSON.",
                "students": [{"name": "Estudiante Uno", "email": "student@example.com"}],
                "tutor": {"name": "Tutor Uno", "email": "tutor@example.com"},
            }
            headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": "API-TEST-001"}

            with app.test_client() as client:
                first = client.post("/api/v1/regional-projects", json=payload, headers=headers)
                payload["title"] = "Ganador institucional actualizado"
                second = client.post("/api/v1/regional-projects", json=payload, headers=headers)
                photos = client.post(
                    "/api/v1/regional-projects/API-TEST-001/files",
                    data={"member_photo_1": (io.BytesIO(b"test-image"), "student.jpg")},
                    headers=headers,
                    content_type="multipart/form-data",
                )

            projects = Project.query.filter_by(institution_id=school.id, external_project_id="API-TEST-001").all()
            self.assertEqual(201, first.status_code)
            self.assertEqual(200, second.status_code)
            self.assertEqual("updated", second.get_json()["result"])
            self.assertEqual(200, photos.status_code)
            self.assertEqual(1, photos.get_json()["member_photos_received"])
            self.assertEqual(1, len(projects))
            self.assertEqual("Ganador institucional actualizado", projects[0].title)
            self.assertEqual(Project.ORIGIN_INSTITUTIONAL_API, projects[0].origin)
            self.assertTrue(projects[0].members[0].photo_url)
            (Path(current_app.static_folder) / projects[0].members[0].photo_url).unlink(missing_ok=True)
            ProjectImportEvent.query.filter_by(institution_id=school.id).delete(synchronize_session=False)
            db.session.delete(projects[0])
            InstitutionApiCredential.query.filter_by(institution_id=school.id).delete(synchronize_session=False)
            db.session.delete(school)
            db.session.commit()

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
        self.assertIsNone(school.shield_path)

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

    def test_school_coordinators_are_excluded_from_judge_management(self):
        source = Path("app/controllers/admin_controller.py").read_text(encoding="utf-8")
        bootstrap = Path("app/__init__.py").read_text(encoding="utf-8")
        self.assertIn("Judge.role != Judge.ROLE_SCHOOL_COORDINATOR", source)
        self.assertIn("existing_user.role = Judge.ROLE_SCHOOL_COORDINATOR", source)
        self.assertIn("'school_coordinator'", bootstrap)

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

    def test_evaluated_and_winner_states_are_not_manual_transitions(self):
        admin = Judge(id=1, role=Judge.ROLE_SUPERADMIN, is_admin=True)
        approved = Project(id=31, regional_status=Project.STATUS_APPROVED)
        evaluated = Project(id=32, regional_status=Project.STATUS_EVALUATED)

        with self.assertRaises(RegionalTransitionError):
            transition_project(approved, Project.STATUS_EVALUATED, admin)
        with self.assertRaises(RegionalTransitionError):
            transition_project(evaluated, Project.STATUS_REGIONAL_WINNER, admin)

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

    def test_institutions_workspace_has_clean_text_and_full_width_actions(self):
        source = Path("app/templates/admin/institutions.html").read_text(encoding="utf-8")
        school_source = Path("app/templates/school/dashboard.html").read_text(encoding="utf-8")

        self.assertNotIn("Ã", source)
        self.assertNotIn("Â", source)
        self.assertIn("institution-card", source)
        self.assertNotIn("<details", source)
        self.assertIn("data-dialog-open", source)
        self.assertIn("<dialog", source)
        self.assertNotIn("upload_shield", source)
        self.assertIn("Editar colegio", source)
        self.assertIn("Eliminar colegio", source)
        self.assertIn('name="confirmation_code"', source)
        self.assertIn("institution_shield", school_source)
        self.assertIn("Mi colegio", school_source)
        self.assertIn("Archivos y logística", school_source)
        self.assertIn("member_photo_", school_source)

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
            admin = Judge.query.filter_by(email="review-page-test@example.com").first()
            if admin is None:
                admin = Judge(full_name="Revisor regional", email="review-page-test@example.com", role=Judge.ROLE_SUPERADMIN, password_hash="test-only", is_active_user=True, is_admin=True)
                db.session.add(admin)
                db.session.flush()
            with app.test_client() as client:
                with client.session_transaction() as session:
                    session["_user_id"] = str(admin.id)
                    session["_fresh"] = True
                response = client.get("/admin/revision-regional")
            db.session.delete(admin)
            db.session.commit()

        self.assertEqual(200, response.status_code)
        body = response.get_data(as_text=True)
        self.assertIn("Revisión de proyectos", body)
        self.assertIn("Evaluado automáticamente", body)
        self.assertNotIn("Marcar evaluado", body)
        self.assertNotIn("Declarar ganador", body)
        self.assertIn("no-store", response.headers.get("Cache-Control", ""))

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

    def test_school_registration_reuses_the_complete_official_form(self):
        app = create_app()
        app.config["TESTING"] = True

        with app.app_context():
            school = Institution(code="FORM-OWN", name="Colegio del formulario", responsible_name="Responsable", responsible_email="form@example.com", is_active=True)
            db.session.add(school)
            db.session.flush()
            coordinator = Judge(full_name="Coordinador del formulario", email="form-coordinator@example.com", role=Judge.ROLE_SCHOOL_COORDINATOR, institution_id=school.id, password_hash="test-only", is_active_user=True)
            db.session.add(coordinator)
            db.session.flush()

            with app.test_client() as client:
                with client.session_transaction() as session:
                    session["_user_id"] = str(coordinator.id)
                    session["_fresh"] = True
                response = client.get("/colegio/proyectos/nuevo")

            db.session.rollback()

        body = response.get_data(as_text=True)
        self.assertEqual(200, response.status_code)
        self.assertIn("Registrar proyecto", body)
        self.assertNotIn("Nuevo proyecto ganador", body)
        self.assertIn("Colegio del formulario", body)
        self.assertIn('name="student_1_identity"', body)
        self.assertIn('name="thematic_axis_id"', body)
        self.assertIn('name="project_type_id"', body)
        self.assertIn('name="advisor_identity"', body)
        self.assertIn('name="mentor_has"', body)
        self.assertIn('name="declaration"', body)

    def test_school_coordinator_updates_only_own_institution_profile(self):
        app = create_app()
        app.config["TESTING"] = True

        with app.app_context():
            own_school = Institution(code="PROFILE-OWN", name="Nombre anterior", responsible_name="Responsable", responsible_email="profile-own@example.com", is_active=True)
            other_school = Institution(code="PROFILE-OTHER", name="Colegio sin cambios", responsible_name="Otra persona", responsible_email="profile-other@example.com", is_active=True)
            db.session.add_all([own_school, other_school])
            db.session.flush()
            coordinator = Judge(full_name="Coordinador de perfil", email="profile-coordinator@example.com", role=Judge.ROLE_SCHOOL_COORDINATOR, institution_id=own_school.id, password_hash="test-only", is_active_user=True)
            db.session.add(coordinator)
            db.session.commit()

            with app.test_client() as client:
                with client.session_transaction() as session:
                    session["_user_id"] = str(coordinator.id)
                    session["_fresh"] = True
                response = client.post("/colegio/perfil", data={"name": "Colegio actualizado", "responsible_name": "Nueva responsable", "responsible_email": "nuevo@example.com"})

            db.session.refresh(own_school)
            db.session.refresh(other_school)
            self.assertEqual(302, response.status_code)
            self.assertEqual("Colegio actualizado", own_school.name)
            self.assertEqual("Colegio sin cambios", other_school.name)
            db.session.delete(coordinator)
            db.session.delete(own_school)
            db.session.delete(other_school)
            db.session.commit()

    def test_general_admin_can_impersonate_school_and_restore_session(self):
        app = create_app()
        app.config["TESTING"] = True

        with app.app_context():
            school = Institution(code="IMPERSONATE-TEST", name="Colegio suplantado", responsible_name="Responsable", responsible_email="impersonate-school@example.com", is_active=True, participation_status=Institution.STATUS_ENABLED)
            admin = Judge(full_name="Administrador de prueba", email="impersonate-admin@example.com", role=Judge.ROLE_ADMIN, password_hash="test-only", is_active_user=True, is_admin=True)
            coordinator = Judge(full_name="Coordinación suplantada", email="impersonate-coordinator@example.com", role=Judge.ROLE_SCHOOL_COORDINATOR, institution_ref=school, password_hash="test-only", is_active_user=True)
            db.session.add_all([school, admin, coordinator])
            db.session.commit()

            with app.test_client() as client:
                with client.session_transaction() as client_session:
                    client_session["_user_id"] = str(admin.id)
                    client_session["_fresh"] = True
                started = client.post(f"/admin/colegios/{school.id}/suplantar")
                portal = client.get("/colegio/panel")
                with client.session_transaction() as client_session:
                    self.assertEqual(str(coordinator.id), client_session["_user_id"])
                    self.assertEqual(admin.id, client_session["impersonator_admin_id"])
                stopped = client.post("/auth/salir-suplantacion")
                with client.session_transaction() as client_session:
                    self.assertEqual(str(admin.id), client_session["_user_id"])
                    self.assertNotIn("impersonator_admin_id", client_session)

            self.assertEqual(302, started.status_code)
            self.assertEqual(200, portal.status_code)
            self.assertIn("Sesión de suplantación activa", portal.get_data(as_text=True))
            self.assertEqual(302, stopped.status_code)
            db.session.delete(coordinator)
            db.session.delete(admin)
            db.session.delete(school)
            db.session.commit()


if __name__ == "__main__":
    unittest.main()
