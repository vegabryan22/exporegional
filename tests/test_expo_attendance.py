import json
import unittest
from flask import Flask
from app.extensions import db
from app import models
from app.models.judge import Judge
from app.models.institution import Institution
from app.models.project import Project
from app.models.assignment import Assignment
from app.models.assignment_process import AssignmentProcess
from app.models.system_setting import SystemSetting
from app.models.evaluation import Evaluation
from app.models.project_member import ProjectMember
from app.services.expo_attendance_service import presence_key, exposition_judges, invitation_pdf
from app.services.assignment_process_service import generate_process_draft, approve_process

class ExpoAttendanceTest(unittest.TestCase):
    def setUp(self):
        self.app = Flask('app')
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        db.init_app(self.app)
        self.ctx = self.app.app_context(); self.ctx.push(); db.create_all()
        schools = [Institution(code=str(i),name=f'Colegio {i}',responsible_name='Persona',responsible_email=f'{i}@school.test') for i in (1,2)]
        db.session.add_all(schools); db.session.flush()
        self.project = Project(title='Proyecto',team_name='Equipo',representative_name='Estudiante',representative_email='student@test',description='Prueba',category='steam',institution_id=schools[0].id,regional_status=Project.STATUS_APPROVED,is_active=True)
        db.session.add(self.project)
        self.judges = [Judge(full_name=f'Juez {i}',email=f'{i}@test',password_hash='test',institution_id=schools[1].id,can_evaluate_exposition=True,is_active_user=True,role=Judge.ROLE_JUDGE) for i in range(4)]
        db.session.add_all(self.judges); db.session.flush()

    def tearDown(self):
        db.session.remove(); db.drop_all(); self.ctx.pop()

    def present(self, judges):
        SystemSetting.set_value(presence_key(),json.dumps({str(j.id):{'present':True} for j in judges}))
        db.session.flush()

    def test_invitation_does_not_require_confirmation_or_presence(self):
        self.assertEqual(4,len(exposition_judges()))
        self.assertIsNone(self.judges[0].attendance_confirmed)
        self.assertTrue(invitation_pdf(self.judges[0]).startswith(b'%PDF'))
        self.judges[0].can_evaluate_exposition = False; db.session.flush()
        self.assertEqual(3,len(exposition_judges()))

    def test_present_draft_replaces_absent_expo_but_preserves_documentation(self):
        absent = self.judges[-1]
        old = Assignment(judge_id=absent.id,project_id=self.project.id,can_evaluate_exposition=True,can_evaluate_documentation=True,status=Assignment.STATUS_CONFIRMED)
        db.session.add(old); db.session.flush()
        self.present(self.judges[:3])
        process,missing = generate_process_draft(AssignmentProcess.TYPE_EXPOSITION,present_only=True)
        self.assertFalse(missing)
        self.assertEqual({j.id for j in self.judges[:3]}, {i.judge_id for i in process.items})
        approve_process(process)
        self.assertFalse(old.can_evaluate_exposition)
        self.assertTrue(old.can_evaluate_documentation)
        self.assertEqual(3,sum(a.can_evaluate_exposition for a in Assignment.query.filter_by(project_id=self.project.id,status=Assignment.STATUS_CONFIRMED)))

    def test_presence_change_and_incomplete_draft_block_approval(self):
        self.present(self.judges[:3])
        process,_ = generate_process_draft(AssignmentProcess.TYPE_EXPOSITION,present_only=True)
        self.present(self.judges[:2])
        with self.assertRaises(ValueError): approve_process(process)
        process,missing = generate_process_draft(AssignmentProcess.TYPE_EXPOSITION,present_only=True)
        self.assertTrue(missing)
        with self.assertRaises(ValueError): approve_process(process)

    def test_same_school_judge_never_assigned(self):
        self.judges[0].institution_id = self.project.institution_id
        self.present(self.judges)
        process,missing = generate_process_draft(AssignmentProcess.TYPE_EXPOSITION,present_only=True)
        self.assertFalse(missing)
        self.assertNotIn(self.judges[0].id,{i.judge_id for i in process.items})

    def test_redistribution_cannot_remove_saved_english_evaluation(self):
        for judge in self.judges: judge.can_evaluate_english = True
        member = ProjectMember(project=self.project,full_name='Estudiante',participates_in_english=True)
        db.session.add(member); db.session.flush()
        absent = self.judges[-1]
        db.session.add(Evaluation(project_id=self.project.id,project_member_id=member.id,judge_id=absent.id,evaluation_type='english_project_performance'))
        self.present(self.judges[:1])
        process,missing = generate_process_draft(AssignmentProcess.TYPE_ENGLISH,present_only=True)
        self.assertFalse(missing)
        with self.assertRaisesRegex(ValueError,'evaluaciones guardadas'): approve_process(process)

    def test_venue_crud_preserves_assigned_projects(self):
        from app.extensions import login_manager
        from app.routes.admin_routes import admin_bp
        from app.services.expo_progress_service import venue_config, VENUE_SETTING
        login_manager.init_app(self.app)
        self.app.secret_key = 'test'
        self.app.register_blueprint(admin_bp)
        admin = Judge(full_name='Administrador',email='admin@test',password_hash='test',role=Judge.ROLE_SUPERADMIN)
        db.session.add(admin); db.session.commit()
        client = self.app.test_client()
        with client.session_transaction() as session:
            session['_user_id'] = str(admin.id); session['_fresh'] = True
        self.assertEqual(302,client.post('/admin/recintos',data={'action':'create','name':'Recinto de prueba','responsible':'Persona'}).status_code)
        config = venue_config(); venue_id = config['venues'][0]['id']
        client.post('/admin/recintos',data={'action':'update','venue_id':venue_id,'name':'Nombre corregido','responsible':'Otra persona'})
        self.assertEqual('Nombre corregido',venue_config()['venues'][0]['name'])
        config = venue_config(); config['projects'][str(self.project.id)] = venue_id
        SystemSetting.set_value(VENUE_SETTING,json.dumps(config)); db.session.commit()
        client.post('/admin/recintos',data={'action':'delete','venue_id':venue_id})
        self.assertEqual(1,len(venue_config()['venues']))
        self.assertEqual(venue_id,venue_config()['projects'][str(self.project.id)])
        client.post('/admin/recintos',data={'action':'save','venue_'+str(self.project.id):''})
        client.post('/admin/recintos',data={'action':'delete','venue_id':venue_id})
        self.assertEqual([],venue_config()['venues'])

    def english_only_judge(self):
        judge = self.judges[0]
        judge.can_evaluate_documentation = False
        judge.can_evaluate_exposition = False
        judge.can_evaluate_english = True
        db.session.add(ProjectMember(project=self.project, full_name='Estudiante inglés', participates_in_english=True))
        db.session.flush()
        return judge

    def test_english_only_automatic_process_and_presence(self):
        judge = self.english_only_judge()
        self.assertEqual('Solo inglés', judge.evaluation_scope_label)
        self.assertIn(judge, exposition_judges())
        self.present(self.judges)
        spanish, missing = generate_process_draft(AssignmentProcess.TYPE_EXPOSITION, present_only=True)
        self.assertFalse(missing)
        self.assertNotIn(judge.id, {item.judge_id for item in spanish.items})
        english, missing = generate_process_draft(AssignmentProcess.TYPE_ENGLISH, present_only=True)
        self.assertFalse(missing)
        self.assertEqual({judge.id}, {item.judge_id for item in english.items})
        approve_process(english)
        assignment = Assignment.query.filter_by(judge_id=judge.id, project_id=self.project.id).one()
        self.assertTrue(assignment.can_evaluate_english)
        self.assertFalse(assignment.can_evaluate_exposition)
        self.assertFalse(assignment.can_evaluate_documentation)

    def test_english_only_absence_school_and_missing_coverage(self):
        judge = self.english_only_judge()
        self.present(self.judges)
        judge.attendance_confirmed = False
        _, missing = generate_process_draft(AssignmentProcess.TYPE_ENGLISH, present_only=True)
        self.assertTrue(missing)
        judge.attendance_confirmed = True
        judge.institution_id = self.project.institution_id
        _, missing = generate_process_draft(AssignmentProcess.TYPE_ENGLISH, present_only=True)
        self.assertTrue(missing)
        judge.institution_id = self.judges[1].institution_id
        self.present(self.judges[1:])
        _, missing = generate_process_draft(AssignmentProcess.TYPE_ENGLISH, present_only=True)
        self.assertTrue(missing)

    def test_profile_change_blocks_old_draft_even_without_presence_filter(self):
        process, _ = generate_process_draft(AssignmentProcess.TYPE_EXPOSITION)
        judge = process.items[0].judge
        judge.can_evaluate_documentation = False
        judge.can_evaluate_exposition = False
        judge.can_evaluate_english = True
        with self.assertRaisesRegex(ValueError, 'ya no puede evaluar'):
            approve_process(process)

    def test_legacy_automatic_assignment_keeps_english_separate(self):
        from app.controllers.admin_controller import _auto_assign_judges, _trim_excess_draft_scopes
        judge = self.english_only_judge()
        created, _ = _auto_assign_judges(3, False)
        self.assertGreater(created, 0)
        assignment = Assignment.query.filter_by(judge_id=judge.id, project_id=self.project.id).one()
        self.assertTrue(assignment.can_evaluate_english)
        self.assertFalse(assignment.can_evaluate_exposition)
        self.assertFalse(assignment.can_evaluate_documentation)
        _trim_excess_draft_scopes([assignment]); db.session.flush()
        self.assertIsNotNone(db.session.get(Assignment, assignment.id))

    def test_manual_assignment_enforces_profile_and_allows_english(self):
        from app.controllers.admin_controller import _assignment_compatibility_error, _assignment_scope_valid, _apply_assignment_scope, _judge_scope_from_value
        from app.services.evaluation_service import assignment_allows_evaluation_type, ENGLISH_EVAL_TYPE_CODE
        from types import SimpleNamespace
        judge = self.english_only_judge()
        self.assertEqual((False, False, 'Solo inglés'), _judge_scope_from_value('Solo inglés'))
        with self.app.test_request_context('/', method='POST', data={'assignment_scope': 'ingles'}):
            self.assertTrue(_assignment_scope_valid(False, False))
            self.assertFalse(_assignment_compatibility_error(judge, self.project, False, False))
            self.assertTrue(_assignment_compatibility_error(judge, self.project, False, True))
            self.assertTrue(_assignment_compatibility_error(judge, self.project, True, False))
            assignment = Assignment(judge=judge, project=self.project)
            _apply_assignment_scope(assignment, False, False)
            self.assertTrue(assignment_allows_evaluation_type(assignment, SimpleNamespace(code=ENGLISH_EVAL_TYPE_CODE)))
            # Even an old assignment with Spanish permissions must not bypass the new profile.
            assignment.can_evaluate_exposition = True
            assignment.can_evaluate_documentation = True
            self.assertFalse(assignment_allows_evaluation_type(assignment, SimpleNamespace(code='exposicion')))
            self.assertFalse(assignment_allows_evaluation_type(assignment, SimpleNamespace(code='documentacion')))
            self.assertFalse(assignment_allows_evaluation_type(assignment, SimpleNamespace(code='rubrica_general')))

    def test_admin_can_edit_existing_judge_to_english_only_without_losing_history(self):
        from flask_login import login_user
        from app.extensions import login_manager
        from app.controllers.admin_controller import _handle_action
        login_manager.init_app(self.app)
        self.app.secret_key = 'test'
        judge = self.judges[0]
        admin = Judge(full_name='Administrador', email='admin@test', password_hash='test', role=Judge.ROLE_SUPERADMIN)
        old = Assignment(judge=judge, project=self.project, can_evaluate_exposition=True, status=Assignment.STATUS_CONFIRMED)
        evaluation = Evaluation(judge=judge, project=self.project, evaluation_type='expo', percentage=80)
        db.session.add_all([admin, old, evaluation]); db.session.commit()
        with self.app.test_request_context('/', method='POST', data={
            'judge_id': judge.id, 'judge_full_name': judge.full_name, 'judge_email': judge.email,
            'judge_role': Judge.ROLE_JUDGE, 'judge_school_id': judge.institution_id,
            'judge_evaluation_scope': 'ingles', 'judge_is_active_user': '1',
        }):
            login_user(admin)
            _handle_action('pool_update_judge')
            self.assertTrue(judge.english_only)
            self.assertEqual(1, Assignment.query.filter_by(judge_id=judge.id).count())
            self.assertEqual(80, evaluation.percentage)
            self.assertTrue(any('incompatible' in msg for _, msg in __import__('flask').get_flashed_messages(with_categories=True)))

    def test_recording_arrival_preserves_operational_filters(self):
        from app.extensions import login_manager
        from app.routes.admin_routes import admin_bp
        login_manager.init_app(self.app)
        self.app.secret_key = 'test'
        self.app.register_blueprint(admin_bp)
        admin = Judge(full_name='Administrador', email='admin@test', password_hash='test', role=Judge.ROLE_SUPERADMIN)
        db.session.add(admin); db.session.commit()
        client = self.app.test_client()
        with client.session_transaction() as session:
            session['_user_id'] = str(admin.id); session['_fresh'] = True
        response = client.post('/admin/expo/jueces', data={
            'action':'presence', 'judge_id':self.judges[0].id, 'present':'1',
            'filter_presence':'no', 'filter_response':'yes', 'filter_q':'Juez',
        })
        self.assertEqual(302, response.status_code)
        self.assertIn('filter_presence=no', response.location)
        self.assertIn('filter_response=yes', response.location)
        self.assertIn('filter_q=Juez', response.location)

if __name__ == '__main__': unittest.main()
