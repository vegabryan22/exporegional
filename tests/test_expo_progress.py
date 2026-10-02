import unittest
from types import SimpleNamespace as Row
from app.services.expo_progress_service import project_progress
from app.models.assignment import Assignment
from app.services.evaluation_service import ENGLISH_EVAL_TYPE_CODE

class ExpoProgressTest(unittest.TestCase):
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
        self.assertEqual(1, row["english_expected"])
        self.assertTrue(row["english_unassigned"])
        self.assertNotEqual("complete", row["status"])

    def test_draft_and_unrelated_english_evaluations_do_not_complete_project(self):
        project = self.project(True)
        self.exposition(project)
        project.assignments = [Row(judge_id=4, status=Assignment.STATUS_DRAFT, can_evaluate_english=True, judge=Row(can_evaluate_english=True))]
        project.evaluations.append(Row(judge_id=4, evaluation_type=ENGLISH_EVAL_TYPE_CODE, project_member_id=10))
        self.assertEqual(0, project_progress(project, {"expo"})["english"])
        project.assignments[0].status = Assignment.STATUS_CONFIRMED
        self.assertEqual("complete", project_progress(project, {"expo"})["status"])
        project.members.append(Row(id=11, participates_in_english=True))
        row = project_progress(project, {"expo"})
        self.assertEqual((1, 2), (row["english"], row["english_expected"]))
        self.assertEqual("pending", row["status"])

    def test_fourth_exposition_evaluation_requires_review(self):
        project = self.project()
        self.exposition(project)
        project.evaluations.append(Row(judge_id=4, evaluation_type="expo", project_member_id=None))
        self.assertEqual("review", project_progress(project, {"expo"})["status"])

if __name__ == "__main__":
    unittest.main()
