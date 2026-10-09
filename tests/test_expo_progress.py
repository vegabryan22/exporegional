import unittest
from types import SimpleNamespace as Row
from app.services.expo_progress_service import project_progress
from app.models.assignment import Assignment
from app.services.evaluation_service import ENGLISH_EVAL_TYPE_CODE

class ExpoProgressTest(unittest.TestCase):
    def test_venue_editor_groups_by_linked_school_and_alphabetical_project(self):
        from app.services.expo_progress_service import group_venue_projects
        school = Row(id=2,name='CTP Águila')
        projects = [Row(id=1,title='Zeta',institution=school,institution_name='Dato manual antiguo'),
                    Row(id=2,title='Árbol',institution=school,institution_name='Otro dato'),
                    Row(id=3,title='Proyecto',institution=Row(id=1,name='CTP Zeta'),institution_name=''),
                    Row(id=4,title='Sin vínculo',institution=None,institution_name=None)]
        groups = group_venue_projects(projects)
        self.assertEqual(['CTP Águila','CTP Zeta','Sin colegio vinculado'],[g['name'] for g in groups])
        self.assertEqual(['Árbol','Zeta'],[p.title for p in groups[0]['projects']])
        self.assertEqual('2',groups[0]['id'])

    def project(self, english=False):
        return Row(id=1, title="Proyecto", institution=Row(name="Colegio"), category="steam", members=[Row(id=10, participates_in_english=english)], assignments=[], evaluations=[])

    def exposition(self, project):
        project.evaluations = [Row(judge_id=i, evaluation_type="expo", project_member_id=None) for i in (1, 2, 3)]

    def test_three_distinct_evaluators_and_duplicate_submission(self):
        project = self.project()
        self.exposition(project)
        project.evaluations.append(project.evaluations[0])
        row = project_progress(project, {"expo"})
        self.assertEqual(3, row["exposition"])
        self.assertEqual("complete", row["status"])
        self.assertNotIn("evaluations", row)

    def test_english_without_assigned_judge_is_pending(self):
        project = self.project(True)
        self.exposition(project)
        row = project_progress(project, {"expo"})
        self.assertEqual(3, row["english_expected"])
        self.assertTrue(row["english_unassigned"])
        self.assertNotEqual("complete", row["status"])

    def test_draft_and_unrelated_english_evaluations_do_not_complete_project(self):
        project = self.project(True)
        self.exposition(project)
        project.assignments = [Row(judge_id=4, status=Assignment.STATUS_DRAFT, can_evaluate_english=True, judge=Row(can_evaluate_english=True))]
        project.evaluations.append(Row(judge_id=4, evaluation_type=ENGLISH_EVAL_TYPE_CODE, project_member_id=10))
        self.assertEqual(0, project_progress(project, {"expo"})["english"])
        project.assignments[0].status = Assignment.STATUS_CONFIRMED
        self.assertEqual("pending", project_progress(project, {"expo"})["status"])
        project.members.append(Row(id=11, participates_in_english=True))
        row = project_progress(project, {"expo"})
        self.assertEqual((1, 6), (row["english"], row["english_expected"]))
        self.assertEqual("pending", row["status"])

    def test_each_student_requires_three_distinct_english_judges(self):
        project = self.project(True)
        self.exposition(project)
        project.members.append(Row(id=11,participates_in_english=True))
        project.assignments = [Row(judge_id=j,status=Assignment.STATUS_CONFIRMED,can_evaluate_english=True,judge=Row(can_evaluate_english=True)) for j in (4,5,6)]
        project.evaluations.extend(Row(judge_id=j,evaluation_type=ENGLISH_EVAL_TYPE_CODE,project_member_id=m) for j in (4,5,6) for m in (10,11))
        row = project_progress(project,{'expo'})
        self.assertEqual((6,6),(row['english'],row['english_expected']))
        self.assertEqual('complete',row['status'])
        project.evaluations.pop()
        self.assertEqual('pending',project_progress(project,{'expo'})['status'])

    def test_fourth_exposition_evaluation_requires_review(self):
        project = self.project()
        self.exposition(project)
        project.evaluations.append(Row(judge_id=4, evaluation_type="expo", project_member_id=None))
        self.assertEqual("review", project_progress(project, {"expo"})["status"])

    def test_pending_names_are_private_and_include_partial_english(self):
        project = self.project(True)
        project.members.append(Row(id=11, participates_in_english=True))
        project.assignments = [Row(judge_id=4, status=Assignment.STATUS_CONFIRMED, can_evaluate_exposition=True, can_evaluate_english=True, judge=Row(full_name="Juez pendiente", can_evaluate_english=True))]
        project.evaluations = [Row(judge_id=4, evaluation_type=ENGLISH_EVAL_TYPE_CODE, project_member_id=10)]
        self.assertNotIn("pending_judges", project_progress(project, {"expo"}))
        row = project_progress(project, {"expo"}, include_pending_judges=True)
        self.assertEqual([{"name": "Juez pendiente"}], row["pending_judges"]["exposition"])
        self.assertEqual(2, row["pending_judges"]["exposition_unassigned"])
        self.assertEqual((1, 2), (row["pending_judges"]["english"][0]["completed"], row["pending_judges"]["english"][0]["expected"]))
        project.evaluations.extend([Row(judge_id=4, evaluation_type="expo", project_member_id=None), Row(judge_id=4, evaluation_type=ENGLISH_EVAL_TYPE_CODE, project_member_id=11)])
        row = project_progress(project, {"expo"}, include_pending_judges=True)
        self.assertEqual([], row["pending_judges"]["exposition"])
        self.assertEqual([], row["pending_judges"]["english"])

if __name__ == "__main__":
    unittest.main()
