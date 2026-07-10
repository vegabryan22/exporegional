from collections import defaultdict

from sqlalchemy.orm import joinedload

from app.models.assignment import Assignment
from app.models.category import Category
from app.models.evaluation import Evaluation
from app.models.evaluation_type import EvaluationType
from app.models.project import Project


ENGLISH_EVAL_TYPE_CODE = "english_project_performance"


def _normalize_label_source(*values):
    return " ".join(((value or "").strip().lower() for value in values if value)).strip()


def infer_evaluation_type_kind(evaluation_type) -> str | None:
    if not evaluation_type:
        return None

    primary_haystack = _normalize_label_source(
        getattr(evaluation_type, "code", ""),
        getattr(evaluation_type, "name", ""),
    )
    if any(keyword in primary_haystack for keyword in ["exposicion", "exposici", "oral", "presentacion"]):
        return "exposicion"
    if any(keyword in primary_haystack for keyword in ["documento", "documentacion", "documentaci", "informe escrito", "bitacora"]):
        return "documentacion"

    secondary_haystack = _normalize_label_source(
        *[getattr(item, "section_name", "") for item in getattr(evaluation_type, "rubric_criteria", [])],
    )
    if any(keyword in secondary_haystack for keyword in ["exposicion", "exposici", "oral", "presentacion"]):
        return "exposicion"
    if any(keyword in secondary_haystack for keyword in ["documento", "documentacion", "documentaci", "informe escrito", "bitacora"]):
        return "documentacion"
    return None


def _infer_rubric_display_name(evaluation_type, fallback: str) -> str:
    rubric_kind = infer_evaluation_type_kind(evaluation_type)
    if rubric_kind == "documentacion":
        return "Documentacion"
    if rubric_kind == "exposicion":
        return "Exposicion"
    return fallback


def project_has_english_exhibition(project) -> bool:
    return any(getattr(member, "participates_in_english", False) for member in getattr(project, "members", []))


def get_project_category(project):
    category_code = (getattr(project, "category", "") or "").strip().lower()
    if not category_code:
        return None
    return Category.query.filter_by(code=category_code).first()


def get_project_base_evaluation_types(project):
    category = get_project_category(project)
    if not category:
        return []
    result = []
    for item in [category.rubric_1_evaluation_type, category.rubric_2_evaluation_type]:
        if item and item.is_active and item.code not in {row.code for row in result}:
            result.append(item)
    return result


def get_project_available_evaluation_types(project):
    result = list(get_project_base_evaluation_types(project))
    if project_has_english_exhibition(project):
        english_type = EvaluationType.query.filter_by(code=ENGLISH_EVAL_TYPE_CODE, is_active=True).first()
        if english_type and english_type.code not in {row.code for row in result}:
            result.append(english_type)
    return result


def assignment_allows_evaluation_type(assignment, evaluation_type) -> bool:
    if evaluation_type.code == ENGLISH_EVAL_TYPE_CODE:
        judge = getattr(assignment, "judge", None)
        return bool(
            getattr(assignment, "can_evaluate_exposition", True)
            and judge
            and getattr(judge, "can_evaluate_english", False)
        )
    rubric_kind = infer_evaluation_type_kind(evaluation_type)
    if rubric_kind == "documentacion":
        return bool(getattr(assignment, "can_evaluate_documentation", True))
    if rubric_kind == "exposicion":
        return bool(getattr(assignment, "can_evaluate_exposition", True))
    return bool(
        getattr(assignment, "can_evaluate_documentation", True)
        or getattr(assignment, "can_evaluate_exposition", True)
    )


def get_assignment_available_evaluation_types(assignment):
    return [
        eval_type
        for eval_type in get_project_available_evaluation_types(assignment.project)
        if assignment_allows_evaluation_type(assignment, eval_type)
    ]


def get_project_english_members(project):
    return [
        member
        for member in getattr(project, "members", [])
        if getattr(member, "participates_in_english", False)
    ]


def build_evaluation_entry(evaluation_type, project_member=None):
    member_id = getattr(project_member, "id", None)
    member_name = getattr(project_member, "full_name", None)
    key = f"{evaluation_type.code}:{member_id or 0}"
    label = evaluation_type.short_name
    if evaluation_type.code == ENGLISH_EVAL_TYPE_CODE and member_name:
        label = f"{evaluation_type.short_name} - {member_name}"
    return {
        "key": key,
        "code": evaluation_type.code,
        "type": evaluation_type,
        "label": label,
        "short_name": evaluation_type.short_name,
        "project_member": project_member,
        "project_member_id": member_id,
        "project_member_name": member_name,
    }


def get_assignment_evaluation_entries(assignment):
    entries = []
    for eval_type in get_assignment_available_evaluation_types(assignment):
        if eval_type.code == ENGLISH_EVAL_TYPE_CODE:
            for member in get_project_english_members(assignment.project):
                entries.append(build_evaluation_entry(eval_type, member))
        else:
            entries.append(build_evaluation_entry(eval_type))
    return entries


def get_project_available_evaluation_entries(project):
    entries = []
    for eval_type in get_project_available_evaluation_types(project):
        if eval_type.code == ENGLISH_EVAL_TYPE_CODE:
            for member in get_project_english_members(project):
                entries.append(build_evaluation_entry(eval_type, member))
        else:
            entries.append(build_evaluation_entry(eval_type))
    return entries


def get_project_evaluations_summary(project):
    category = get_project_category(project)
    if not category:
        return {"final_grade": None, "english_score": None}

    weighted_types = [
        category.rubric_1_evaluation_type.code if category.rubric_1_evaluation_type else None,
        category.rubric_2_evaluation_type.code if category.rubric_2_evaluation_type else None,
    ]
    weighted_scores = []
    for eval_type_code in weighted_types:
        if not eval_type_code:
            continue
        evaluations = Evaluation.query.filter_by(project_id=project.id, evaluation_type=eval_type_code).all()
        values = [item.percentage for item in evaluations if item.percentage is not None]
        if values:
            weighted_scores.append(sum(values) / len(values))

    english_score = None
    if project_has_english_exhibition(project):
        english_evaluations = Evaluation.query.filter_by(project_id=project.id, evaluation_type=ENGLISH_EVAL_TYPE_CODE).all()
        english_values = [item.percentage for item in english_evaluations if item.percentage is not None]
        if english_values:
            english_score = round(sum(english_values) / len(english_values), 2)

    final_grade = round(sum(weighted_scores) / len(weighted_scores), 2) if len(weighted_scores) == 2 else None
    return {"final_grade": final_grade, "english_score": english_score}


def _average_percentage(evaluations, eval_type_code):
    values = [item.percentage for item in evaluations if item.evaluation_type == eval_type_code and item.percentage is not None]
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def _project_summary_from_loaded(project, category):
    if not category:
        return {
            "final_grade": None,
            "english_score": None,
            "rubric_1_score": None,
            "rubric_2_score": None,
            "rubric_1_label": "Rubrica 1",
            "rubric_2_label": "Rubrica 2",
            "rubric_1_weight_percentage": None,
            "rubric_2_weight_percentage": None,
        }

    rubric_1_eval_type = category.rubric_1_evaluation_type
    rubric_2_eval_type = category.rubric_2_evaluation_type
    rubric_1_code = category.rubric_1_evaluation_type.code if category.rubric_1_evaluation_type else None
    rubric_2_code = category.rubric_2_evaluation_type.code if category.rubric_2_evaluation_type else None
    rubric_1_score = _average_percentage(project.evaluations, rubric_1_code) if rubric_1_code else None
    rubric_2_score = _average_percentage(project.evaluations, rubric_2_code) if rubric_2_code else None

    weighted_scores = [score for score in [rubric_1_score, rubric_2_score] if score is not None]
    final_grade = round(sum(weighted_scores) / len(weighted_scores), 2) if len(weighted_scores) == 2 else None

    english_score = None
    if project_has_english_exhibition(project):
        english_score = _average_percentage(project.evaluations, ENGLISH_EVAL_TYPE_CODE)

    active_weight_count = len([code for code in [rubric_1_code, rubric_2_code] if code])
    per_rubric_weight = round(100 / active_weight_count, 2) if active_weight_count else None

    return {
        "final_grade": final_grade,
        "english_score": english_score,
        "rubric_1_score": rubric_1_score,
        "rubric_2_score": rubric_2_score,
        "rubric_1_label": _infer_rubric_display_name(rubric_1_eval_type, "Rubrica 1"),
        "rubric_2_label": _infer_rubric_display_name(rubric_2_eval_type, "Rubrica 2"),
        "rubric_1_weight_percentage": per_rubric_weight if rubric_1_code else None,
        "rubric_2_weight_percentage": per_rubric_weight if rubric_2_code else None,
    }


def build_admin_evaluation_overview():
    categories = (
        Category.query.options(
            joinedload(Category.rubric_1_evaluation_type),
            joinedload(Category.rubric_2_evaluation_type),
        )
        .order_by(Category.sort_order.asc(), Category.name.asc())
        .all()
    )
    category_map = {category.code: category for category in categories}
    projects = (
        Project.query.options(
            joinedload(Project.members),
            joinedload(Project.assignments).joinedload(Assignment.judge),
            joinedload(Project.evaluations).joinedload(Evaluation.judge),
            joinedload(Project.evaluations).joinedload(Evaluation.project_member),
        )
        .filter(Project.is_active.is_(True))
        .order_by(Project.created_at.desc())
        .all()
    )

    project_rows = []
    winner_candidates = defaultdict(list)
    english_ranking = []
    completed_projects = 0
    total_expected_evaluations = 0
    total_completed_evaluations = 0
    total_expected_english_evaluations = 0
    total_completed_english_evaluations = 0

    for project in projects:
        category = category_map.get((project.category or "").strip().lower())
        available_types = get_project_available_evaluation_types(project)
        assigned_judges = len(project.assignments)
        expected_entries = [
            entry
            for assignment in project.assignments
            for entry in get_assignment_evaluation_entries(assignment)
        ]
        expected_english_evaluations = len([entry for entry in expected_entries if entry["code"] == ENGLISH_EVAL_TYPE_CODE])
        expected_evaluations = len(expected_entries) - expected_english_evaluations
        completed_english_evaluations = len(
            [evaluation for evaluation in project.evaluations if evaluation.evaluation_type == ENGLISH_EVAL_TYPE_CODE]
        )
        completed_evaluations = len(project.evaluations) - completed_english_evaluations
        total_expected_evaluations += expected_evaluations
        total_completed_evaluations += completed_evaluations
        total_expected_english_evaluations += expected_english_evaluations
        total_completed_english_evaluations += completed_english_evaluations

        eval_counts = defaultdict(int)
        for evaluation in project.evaluations:
            eval_counts[evaluation.evaluation_type] += 1

        summary = _project_summary_from_loaded(project, category)
        if expected_evaluations and completed_evaluations >= expected_evaluations:
            completed_projects += 1

        progress_by_type = []
        for eval_type in available_types:
            completed_for_type = eval_counts.get(eval_type.code, 0)
            if eval_type.code == ENGLISH_EVAL_TYPE_CODE:
                english_member_count = len(get_project_english_members(project))
                expected_for_type = sum(
                    english_member_count
                    for assignment in project.assignments
                    if assignment_allows_evaluation_type(assignment, eval_type)
                )
            else:
                expected_for_type = len(
                    [
                        assignment
                        for assignment in project.assignments
                        if assignment_allows_evaluation_type(assignment, eval_type)
                    ]
                )
            average_score = _average_percentage(project.evaluations, eval_type.code)
            progress_by_type.append(
                {
                    "code": eval_type.code,
                    "name": eval_type.name,
                    "completed": completed_for_type,
                    "expected": expected_for_type,
                    "average_score": average_score,
                    "english_member_count": len(get_project_english_members(project))
                    if eval_type.code == ENGLISH_EVAL_TYPE_CODE
                    else None,
                }
            )

        evaluation_records = sorted(
            [
                {
                    "id": evaluation.id,
                    "judge_name": evaluation.judge.full_name if evaluation.judge else "N/D",
                    "evaluation_type": next(
                        (item.name for item in available_types if item.code == evaluation.evaluation_type),
                        evaluation.evaluation_type,
                    ),
                    "project_member_name": evaluation.project_member.full_name if evaluation.project_member else None,
                    "percentage": evaluation.percentage,
                    "created_at": evaluation.created_at,
                }
                for evaluation in project.evaluations
            ],
            key=lambda item: (
                item["evaluation_type"].lower(),
                item["judge_name"].lower(),
                item["id"],
            ),
        )

        row = {
            "project": project,
            "category": category,
            "assigned_judges": assigned_judges,
            "expected_evaluations": expected_evaluations,
            "completed_evaluations": completed_evaluations,
            "completion_percentage": round((completed_evaluations / expected_evaluations) * 100, 2)
            if expected_evaluations
            else 0,
            "available_types": available_types,
            "progress_by_type": progress_by_type,
            "evaluation_records": evaluation_records,
            "english_member_count": len(get_project_english_members(project)),
            "english_members": get_project_english_members(project),
            **summary,
        }
        project_rows.append(row)

        if category and summary["final_grade"] is not None:
            winner_candidates[category.code].append(row)

        english_type = next((item for item in available_types if item.code == ENGLISH_EVAL_TYPE_CODE), None)
        if english_type:
            for member in get_project_english_members(project):
                member_values = [
                    evaluation.percentage
                    for evaluation in project.evaluations
                    if evaluation.evaluation_type == ENGLISH_EVAL_TYPE_CODE
                    and evaluation.project_member_id == member.id
                    and evaluation.percentage is not None
                ]
                if member_values:
                    english_ranking.append(
                        {
                            "project": project,
                            "category": category,
                            "member": member,
                            "english_score": round(sum(member_values) / len(member_values), 2),
                            "completed_evaluations": len(member_values),
                            "expected_evaluations": len(
                                [
                                    assignment
                                    for assignment in project.assignments
                                    if assignment_allows_evaluation_type(assignment, english_type)
                                ]
                            ),
                        }
                    )

    category_winners = []
    for category in categories:
        ranked_rows = sorted(
            winner_candidates.get(category.code, []),
            key=lambda item: (
                -(item["final_grade"] or -1),
                -(item["completion_percentage"] or 0),
                item["project"].title.lower(),
            ),
        )
        winner = ranked_rows[0] if ranked_rows else None
        runner_up = ranked_rows[1] if len(ranked_rows) > 1 else None
        category_winners.append(
            {
                "category": category,
                "winner": winner,
                "runner_up": runner_up,
                "project_count": len(ranked_rows),
            }
        )

    english_ranking.sort(
        key=lambda item: (
            -(item["english_score"] or -1),
            -(item["completed_evaluations"] or 0),
            (getattr(item.get("member"), "full_name", "") or "").lower(),
            item["project"].title.lower(),
        )
    )

    summary_cards = {
        "projects": len(project_rows),
        "completed_projects": completed_projects,
        "expected_evaluations": total_expected_evaluations,
        "completed_evaluations": total_completed_evaluations,
        "expected_english_evaluations": total_expected_english_evaluations,
        "completed_english_evaluations": total_completed_english_evaluations,
        "completion_percentage": round((total_completed_evaluations / total_expected_evaluations) * 100, 2)
        if total_expected_evaluations
        else 0,
    }

    return {
        "summary_cards": summary_cards,
        "project_rows": project_rows,
        "category_winners": category_winners,
        "english_ranking": english_ranking,
    }
