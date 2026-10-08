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

if __name__ == '__main__': unittest.main()
