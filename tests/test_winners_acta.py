import unittest
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace as Row
from unittest.mock import patch
from zipfile import ZipFile
from xml.etree import ElementTree as ET
from flask import Flask
from app.controllers import admin_controller as controller


def fixture():
    def winner(title, school, score):
        return {'project':Row(title=title,institution=Row(name=school),institution_name='Dato antiguo',thematic_axis=Row(name='Innovación tecnológica'),members=[Row(id=1,student_number=1,full_name='Ana María Pérez'),Row(id=2,student_number=2,full_name='Luis Diego Arce')]),'final_grade':score}
    return {'summary_cards':{'projects':2,'completed_projects':2,'expected_english_evaluations':3,'completed_english_evaluations':3},'category_winners':[
        {'category':Row(code='steam',name='STEAM'),'winner':winner('Proyecto STEAM','CTP Máximo Quesada',97.5)},
        {'category':Row(code='emprendimiento',name='Emprendimiento'),'winner':winner('Proyecto Emprendimiento','CTP José Albertazzi Avendaño',96.75)}]}


def generate(overview=None):
    app = Flask('app')
    settings = {'expotec_event_date':'2026-10-09','expotec_school_year':'2026','school_name':'CORVEC Unidos por la Excelencia'}
    with app.test_request_context('/?numero=07&hora=15:30'), patch.object(controller,'build_admin_evaluation_overview',return_value=overview or fixture()), patch.object(controller.SystemSetting,'get_value',side_effect=lambda key,default='':settings.get(key,default)):
        return controller._build_winners_acta_docx()


class WinnersActaTest(unittest.TestCase):
    def test_regional_acta_uses_original_template_and_linked_schools(self):
        result = generate()
        with ZipFile(result) as output, ZipFile(controller.WINNERS_ACTA_TEMPLATE) as source:
            root = ET.fromstring(output.read('word/document.xml'))
            text = ' '.join(n.text or '' for n in root.iter('{'+controller.WORD_NS+'}t'))
            self.assertIn('Acta N° 07 -2026',text)
            self.assertIn('regional',text)
            self.assertNotIn('etapa institucional',text)
            self.assertIn('CTP Máximo Quesada',text)
            self.assertIn('CTP José Albertazzi Avendaño',text)
            self.assertNotIn('Dato antiguo',text)
            self.assertIn('97.50',text)
            self.assertIn('15:30',text)
            self.assertEqual(set(source.namelist()),set(output.namelist()))
            for name in source.namelist():
                if name not in {'word/document.xml','word/header1.xml'}:
                    self.assertEqual(source.read(name),output.read(name),name)

    def test_final_acta_requires_complete_english_and_base_evaluations(self):
        for key in ['completed_projects','completed_english_evaluations']:
            data = fixture(); data['summary_cards'][key] = 0
            with self.assertRaises(ValueError): generate(data)

    def test_student_lines_match_actual_member_count_without_example_labels(self):
        for count in (1,2,3):
            data = fixture()
            for category in data['category_winners']:
                category['winner']['project'].members = [Row(id=i,student_number=i,full_name=f'Estudiante Real Apellido {i}') for i in range(1,count+1)]
            with ZipFile(generate(data)) as document:
                root = ET.fromstring(document.read('word/document.xml'))
            texts = [''.join(n.text or '' for n in p.iter('{'+controller.WORD_NS+'}t')) for p in controller._word_paragraphs(root)]
            self.assertFalse(any('Nombre y apellidos estudiante' in text for text in texts))
            self.assertEqual(2*count,sum(text.startswith('Estudiante Real Apellido') for text in texts))
            self.assertFalse(any(text.startswith('___') for text in texts if 'Director' not in text and 'Coordinación' not in text and 'Presidente' not in text))
            for i in range(1,count+1):
                self.assertEqual(2,texts.count(f'Estudiante Real Apellido {i}'))

    def test_acta_rejects_invalid_member_counts(self):
        for count in (0,4):
            data = fixture()
            data['category_winners'][0]['winner']['project'].members = [Row(id=i,student_number=i,full_name='Persona') for i in range(count)]
            with self.assertRaises(ValueError): generate(data)


if __name__ == '__main__':
    import sys
    if '--preview' in sys.argv:
        directory = Path('tmp/pdfs'); directory.mkdir(parents=True,exist_ok=True)
        (directory/'acta-regional.docx').write_bytes(generate().getvalue())
        for count in (1,3):
            data = fixture()
            for category in data['category_winners']:
                category['winner']['project'].members = [Row(id=i,student_number=i,full_name=f'Estudiante Real Apellido {i}') for i in range(1,count+1)]
            (directory/f'acta-regional-{count}-integrantes.docx').write_bytes(generate(data).getvalue())
        print('Synthetic regional acta generated for visual review')
    else:
        unittest.main()
