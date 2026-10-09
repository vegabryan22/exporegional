import json
import unittest
from unittest.mock import patch
from io import BytesIO
from pypdf import PdfReader
from tests import test_expo_attendance as fixtures
from app.models.system_setting import SystemSetting
from app.services.venue_access_service import access_token, resolve_access, change_access, scoped_progress, serializer, access_url
from app.services.venue_access_pdf import build_access_card, build_access_cards
from werkzeug.exceptions import NotFound


class VenueAccessTest(unittest.TestCase):
    # Reuse the database fixture without collecting its test methods again.
    setUp = fixtures.ExpoAttendanceTest.setUp
    tearDown = fixtures.ExpoAttendanceTest.tearDown
    def test_capability_lifecycle_and_scope(self):
        self.app.config['SECRET_KEY'] = 'test-key'
        venue = {'id':'one','name':'P1-A4','responsible':'Carlos Ticas'}
        change_access(venue, 'access_enable')
        def save():
            SystemSetting.set_value('expo_venues', json.dumps({'venues':[venue, {'id':'two','name':'Other'}], 'projects':{}}))
        save()
        token = access_token(venue)
        self.assertEqual(22,len(token))
        self.assertEqual(token,access_token(venue))
        legacy = serializer().dumps({'venue':venue['id'],'nonce':venue['access_nonce']})
        self.assertEqual('one',resolve_access(legacy)['id'])
        self.assertEqual('one', resolve_access(token)['id'])
        with self.assertRaises(NotFound): resolve_access(token + 'invalid')
        with self.assertRaises(NotFound): resolve_access('á'*22)
        with patch('app.services.venue_access_service.public_progress', return_value={'venues':[{'id':'one','projects':[{'status':'pending'}]}, {'id':'two','projects':[{'status':'complete','secret':'other judge'}]}], 'total':2,'complete':1}):
            data = scoped_progress(venue)
            self.assertEqual(1,data['total']); self.assertEqual(0,data['complete'])
            self.assertNotIn('other judge',json.dumps(data))
        change_access(venue,'access_rotate'); save()
        with self.assertRaises(NotFound): resolve_access(token)
        with self.assertRaises(NotFound): resolve_access(legacy)
        replacement = access_token(venue)
        self.assertEqual('one',resolve_access(replacement)['id'])
        change_access(venue,'access_revoke'); save()
        self.assertIsNone(access_token(venue))
        with self.assertRaises(NotFound): resolve_access(replacement)

    def test_anonymous_scoped_endpoints_and_revocation(self):
        from app.routes.public_routes import public_bp
        self.app.config['SECRET_KEY'] = 'test-key'
        self.app.register_blueprint(public_bp)
        venue = {'id':'one','name':'P1-A4'}
        change_access(venue,'access_enable')
        SystemSetting.set_value('expo_venues',json.dumps({'venues':[venue,{'id':'two','name':'Private other venue'}],'projects':{str(self.project.id):'one'}}))
        token = access_token(venue)
        client = self.app.test_client()
        with self.app.test_request_context():
            self.assertTrue(access_url(venue).endswith('/r/' + token))
        response = client.get('/expo/recinto/' + token + '/datos')
        self.assertEqual(200,response.status_code)
        self.assertEqual(['one'],[v['id'] for v in response.json['venues']])
        self.assertNotIn('access_nonce',response.get_data(as_text=True))
        self.assertIn('no-store',response.headers['Cache-Control'])
        self.assertEqual('no-referrer',response.headers['Referrer-Policy'])
        response = client.get('/expo/recinto/' + token + '/pdf')
        self.assertEqual(200,response.status_code)
        self.assertEqual('application/pdf',response.mimetype)
        change_access(venue,'access_revoke')
        SystemSetting.set_value('expo_venues',json.dumps({'venues':[venue],'projects':{}}))
        self.assertEqual(404,client.get('/expo/recinto/' + token + '/datos').status_code)

    def test_print_card(self):
        data = build_access_card({'name':'P1-A4','responsible':'Carlos Ticas'},'https://example.test/expo/recinto/test').getvalue()
        reader = PdfReader(BytesIO(data))
        self.assertEqual(1,len(reader.pages))
        self.assertIn('Carlos Ticas',reader.pages[0].extract_text())
        self.assertIn('P1-A4',reader.pages[0].extract_text())
        long_card = build_access_card({'name':'Recinto de proyectos innovadores '*3,'responsible':'Nombre completo del responsable '*3},'https://example.test/test')
        self.assertEqual(1,len(PdfReader(long_card).pages))

    def test_card_embeds_both_configured_logos(self):
        values = {'school_logo_path':'judge_invitation/school_crest.jpg','expo_logo_path':'judge_invitation/mep_logo.png'}
        with patch('app.services.venue_access_pdf.SystemSetting.get_value',side_effect=lambda key,default='':values.get(key,default)):
            reader = PdfReader(build_access_card({'name':'P1-A4','responsible':'Carlos Ticas'},'https://example.test/venue'))
        self.assertEqual(2,len(reader.pages[0].images))
        self.assertEqual(1,len(reader.pages))

    def test_logo_path_cannot_escape_static_root(self):
        from app.services.venue_access_pdf import _brand_logo
        with patch('app.services.venue_access_pdf.SystemSetting.get_value',return_value='../../config.py'):
            self.assertIsNone(_brand_logo('school_logo_path'))

    def test_bulk_enable_preserves_active_links_and_reopens_manager(self):
        from app.extensions import db, login_manager
        from app.models.judge import Judge
        from app.routes.admin_routes import admin_bp
        from app.routes.public_routes import public_bp
        from app.services.expo_progress_service import venue_config
        from app.routes.auth_routes import auth_bp
        from flask import g
        login_manager.init_app(self.app)
        self.app.secret_key = 'test'
        self.app.register_blueprint(admin_bp)
        self.app.register_blueprint(public_bp)
        self.app.register_blueprint(auth_bp)
        admin = Judge(full_name='Administrador',email='admin@test',password_hash='test',role=Judge.ROLE_SUPERADMIN)
        db.session.add(admin)
        first = {'id':'one','name':'P1-A4','responsible':'Carlos Ticas'}
        second = {'id':'two','name':'P1-A5','responsible':'Cinthia Díaz'}
        change_access(first,'access_enable')
        original = access_token(first)
        SystemSetting.set_value('expo_venues',json.dumps({'venues':[first,second],'projects':{str(self.project.id):'one'}}))
        db.session.commit()
        client = self.app.test_client()
        self.assertEqual(302,client.get('/admin/recintos/tarjetas.pdf').status_code)
        g.pop('_login_user',None)
        with client.session_transaction() as session:
            session['_user_id'] = str(admin.id); session['_fresh'] = True
            session['venue_access_csrf'] = 'csrf-test'
        self.assertEqual(400,client.post('/admin/recintos',data={'action':'access_enable_all'}).status_code)
        response = client.post('/admin/recintos',data={'action':'access_enable_all','access_csrf':'csrf-test'})
        self.assertEqual(302,response.status_code)
        self.assertTrue(response.location.endswith('#manage-venues'))
        config = venue_config()
        self.assertEqual(original,access_token(config['venues'][0]))
        self.assertTrue(config['venues'][1].get('access_nonce'))
        self.assertEqual({str(self.project.id):'one'},config['projects'])
        tokens = [access_token(v) for v in config['venues']]
        client.post('/admin/recintos',data={'action':'access_enable_all','access_csrf':'csrf-test'})
        self.assertEqual(tokens,[access_token(v) for v in venue_config()['venues']])
        response = client.get('/admin/recintos/tarjetas.pdf')
        self.assertEqual(200,response.status_code)
        self.assertEqual('application/pdf',response.mimetype)
        self.assertIn('no-store',response.headers['Cache-Control'])
        reader = PdfReader(BytesIO(response.data))
        self.assertIn('Carlos Ticas',reader.pages[0].extract_text())
        self.assertIn('Cinthia',reader.pages[0].extract_text())
        response = client.post('/admin/recintos',data={'action':'access_revoke','venue_id':'two','access_csrf':'csrf-test'})
        self.assertTrue(response.location.endswith('#manage-venues'))
        response = client.get('/admin/recintos/tarjetas.pdf')
        self.assertNotIn('Cinthia',PdfReader(BytesIO(response.data)).pages[0].extract_text())
        client.post('/admin/recintos',data={'action':'access_revoke','venue_id':'one','access_csrf':'csrf-test'})
        response = client.get('/admin/recintos/tarjetas.pdf')
        self.assertEqual(302,response.status_code)
        self.assertTrue(response.location.endswith('#manage-venues'))
        self.assertTrue(all(not v.get('access_nonce') for v in venue_config()['venues']))

    def test_card_sheets_pagination(self):
        entries = [({'name':f'P1-A{i}','responsible':f'Responsable {i}'},f'https://event.test/r/{i:022d}') for i in range(11)]
        reader = PdfReader(build_access_cards(entries))
        self.assertEqual(2,len(reader.pages))
        text = '\n'.join(page.extract_text() for page in reader.pages)
        for i in range(11):
            self.assertEqual(1,text.count(f'Responsable {i}\n'))
        self.assertIn('tamaño real',text)
        self.assertIn('90 × 55 mm',text)
        with self.assertRaises(ValueError): build_access_cards([])


if __name__ == '__main__':
    unittest.main()
