import unittest
from pathlib import Path
from types import SimpleNamespace as Row
from pypdf import PdfReader
from tests.test_winners_acta import fixture
from app.services.closing_awards_service import closing_awards, closing_awards_pdf


def awards_fixture():
    data = fixture()
    winner = data['category_winners'][0]['winner']
    data['category_winners'][0]['runner_up'] = {'project':Row(title='Segundo proyecto STEAM',institution=Row(name='CTP Aserrí'),members=[Row(id=3,student_number=1,full_name='Mauricio Antonio González Salas')]),'final_grade':95}
    data['english_ranking'] = [
        {'project':winner['project'],'member':winner['project'].members[0]},
        {'project':data['category_winners'][1]['winner']['project'],'member':Row(full_name='Estudiante reconocido en inglés')},
        {'project':winner['project'],'member':Row(full_name='Tercer puesto no premiado')},
    ]
    return data


class ClosingAwardsTest(unittest.TestCase):
    def test_matches_certificate_awards_and_english_is_individual_and_last(self):
        data = closing_awards(awards_fixture())
        rows = data['award_rows']
        self.assertTrue(data['is_final'])
        self.assertEqual(5,len(rows))
        self.assertEqual(['category']*3+['english']*2,[r['kind'] for r in rows])
        self.assertEqual('CTP Máximo Quesada',rows[0]['school'])
        self.assertEqual('Segundo lugar',rows[1]['place'])
        self.assertEqual(['Ana María Pérez'],rows[-2]['students'])
        self.assertEqual('Mención de honor',rows[-1]['place'])
        self.assertNotIn('Tercer puesto no premiado',str(rows))

    def test_pdf_contains_requested_columns_and_real_student_names(self):
        reader = PdfReader(closing_awards_pdf(closing_awards(awards_fixture())))
        text = '\n'.join(p.extract_text() for p in reader.pages)
        for name in ['Categoría','Colegio','Puesto','Nombre del proyecto','Estudiantes','Mauricio Antonio González Salas','Mención de honor']:
            self.assertIn(name,text)
        self.assertNotIn('Nombre y apellidos estudiante',text)
        self.assertNotIn('Tercer puesto no premiado',text)
        self.assertGreater(text.rindex('Mención de honor'),text.rindex('Proyecto Emprendimiento')-100)

    def test_incomplete_evaluations_mark_list_provisional(self):
        overview = awards_fixture(); overview['summary_cards']['completed_english_evaluations'] = 1
        data = closing_awards(overview)
        self.assertFalse(data['is_final'])
        text = ''.join(p.extract_text() for p in PdfReader(closing_awards_pdf(data)).pages)
        self.assertIn('RESULTADOS PROVISIONALES',text)


if __name__ == '__main__':
    import sys
    if '--preview' in sys.argv:
        target = Path('tmp/pdfs'); target.mkdir(parents=True,exist_ok=True)
        (target/'closing-awards.pdf').write_bytes(closing_awards_pdf(closing_awards(awards_fixture())).getvalue())
        print('Synthetic closure list generated for visual review')
    else:
        unittest.main()
