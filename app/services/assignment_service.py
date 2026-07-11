from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models.assignment import Assignment
from app.models.evaluation import Evaluation
from app.models.judge import Judge
from app.models.project import Project
from app.services.evaluation_service import (
    ENGLISH_EVAL_TYPE_CODE,
    get_project_available_evaluation_types,
    infer_evaluation_type_kind,
)


def _project_evaluation_codes_by_kind(project, kind: str) -> set[str]:
    codes = set()
    for eval_type in get_project_available_evaluation_types(project):
        if kind == "english":
            if eval_type.code == ENGLISH_EVAL_TYPE_CODE:
                codes.add(eval_type.code)
            continue
        if eval_type.code != ENGLISH_EVAL_TYPE_CODE and infer_evaluation_type_kind(eval_type) == kind:
            codes.add(eval_type.code)
    return codes


def _judge_completed_kind(judge_id: int, project, kind: str) -> bool:
    codes = _project_evaluation_codes_by_kind(project, kind)
    if not codes:
        return False
    return (
        Evaluation.query.filter(
            Evaluation.judge_id == judge_id,
            Evaluation.project_id == project.id,
            Evaluation.evaluation_type.in_(codes),
        ).first()
        is not None
    )


def _candidate_load(judge: Judge) -> int:
    return len({assignment.project_id for assignment in getattr(judge, "assignments", [])})


def _find_reassignment_candidate(project, source_judge_id: int, can_documentation: bool, can_exposition: bool, require_english: bool):
    candidates = (
        Judge.query.options(joinedload(Judge.assignments))
        .filter(
            Judge.id != source_judge_id,
            Judge.role == Judge.ROLE_JUDGE,
            Judge.is_active_user == True,  # noqa: E712
            Judge.attendance_confirmed == True,  # noqa: E712
        )
        .all()
    )

    ranked = []
    for candidate in candidates:
        if can_documentation and not candidate.can_evaluate_documentation:
            continue
        if can_exposition and not candidate.can_evaluate_exposition:
            continue
        if require_english and not candidate.can_evaluate_english:
            continue
        if not candidate.can_evaluate_category(project.category):
            continue

        existing_assignment = next(
            (assignment for assignment in candidate.assignments if assignment.project_id == project.id),
            None,
        )
        adds_new_project = 0 if existing_assignment else 1
        ranked.append((adds_new_project, _candidate_load(candidate), candidate.full_name or "", candidate, existing_assignment))

    if not ranked:
        return None, None
    _adds_new_project, _load, _name, candidate, existing_assignment = sorted(ranked, key=lambda item: item[:3])[0]
    return candidate, existing_assignment


def _apply_reassignment(project, source_assignment: Assignment, can_documentation: bool, can_exposition: bool):
    require_english = bool(can_exposition and getattr(project, "requires_english_evaluation", False))
    candidate, existing_assignment = _find_reassignment_candidate(
        project,
        source_assignment.judge_id,
        can_documentation,
        can_exposition,
        require_english,
    )
    if not candidate:
        return None

    if existing_assignment:
        if can_documentation:
            existing_assignment.can_evaluate_documentation = True
        if can_exposition:
            existing_assignment.can_evaluate_exposition = True
        existing_assignment.status = Assignment.STATUS_CONFIRMED
        existing_assignment.notification_sent_at = None
        existing_assignment.notification_error = None
        return existing_assignment

    replacement = Assignment(
        judge_id=candidate.id,
        project_id=project.id,
        can_evaluate_documentation=can_documentation,
        can_evaluate_exposition=can_exposition,
        status=Assignment.STATUS_CONFIRMED,
        notification_sent_at=None,
        notification_error=None,
    )
    replacement.judge = candidate
    replacement.project = project
    db.session.add(replacement)
    return replacement


def reassign_absent_judge_assignments(judge: Judge) -> dict:
    """Move unfinished assignments from an absent judge to confirmed judges with less load."""
    assignments = (
        Assignment.query.options(
            joinedload(Assignment.project).joinedload(Project.members),
            joinedload(Assignment.judge),
        )
        .filter(Assignment.judge_id == judge.id)
        .all()
    )

    summary = {
        "moved": 0,
        "kept_documentation": 0,
        "kept_exposition": 0,
        "unchanged": 0,
        "moves": [],
        "failed": [],
    }

    for assignment in assignments:
        project = assignment.project
        if not project:
            summary["unchanged"] += 1
            continue

        documentation_done = bool(
            assignment.can_evaluate_documentation
            and _judge_completed_kind(judge.id, project, "documentacion")
        )
        exposition_done = bool(
            assignment.can_evaluate_exposition
            and _judge_completed_kind(judge.id, project, "exposicion")
        )

        move_documentation = bool(assignment.can_evaluate_documentation and not documentation_done)
        move_exposition = bool(assignment.can_evaluate_exposition and not exposition_done)
        keep_documentation = bool(assignment.can_evaluate_documentation and documentation_done)
        keep_exposition = bool(assignment.can_evaluate_exposition and exposition_done)

        if not move_documentation and not move_exposition:
            summary["unchanged"] += 1
            if keep_documentation:
                summary["kept_documentation"] += 1
            if keep_exposition:
                summary["kept_exposition"] += 1
            continue

        replacement = _apply_reassignment(project, assignment, move_documentation, move_exposition)
        if not replacement:
            summary["failed"].append(
                {
                    "project_title": project.title,
                    "scope": _scope_label(move_documentation, move_exposition),
                }
            )
            continue

        summary["moved"] += 1
        summary["moves"].append(
            {
                "project_title": project.title,
                "from_judge_name": judge.full_name,
                "to_judge_name": replacement.judge.full_name if replacement.judge else "",
                "to_judge_email": replacement.judge.email if replacement.judge else "",
                "scope": _scope_label(move_documentation, move_exposition),
                "assignment": replacement,
                "project": project,
                "judge": replacement.judge,
            }
        )
        assignment.can_evaluate_documentation = keep_documentation
        assignment.can_evaluate_exposition = keep_exposition
        assignment.notification_sent_at = None
        assignment.notification_error = None
        if keep_documentation:
            summary["kept_documentation"] += 1
        if keep_exposition:
            summary["kept_exposition"] += 1
        if not assignment.can_evaluate_documentation and not assignment.can_evaluate_exposition:
            db.session.delete(assignment)

    return summary


def _scope_label(can_documentation: bool, can_exposition: bool) -> str:
    if can_documentation and can_exposition:
        return "Documento y exposicion"
    if can_documentation:
        return "Documento escrito"
    if can_exposition:
        return "Exposicion oral"
    return "Sin alcance"
