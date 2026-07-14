from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models.assignment import Assignment
from app.models.evaluation import Evaluation
from app.models.judge import Judge
from app.models.project import Project
from app.services.evaluation_service import (
    ENGLISH_EVAL_TYPE_CODE,
    get_assignment_evaluation_entries,
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


def _target_can_receive_assignment(target_judge: Judge, project, can_documentation: bool, can_exposition: bool) -> bool:
    if not target_judge or not getattr(target_judge, "is_active_user", False):
        return False
    if getattr(target_judge, "role", None) != Judge.ROLE_JUDGE:
        return False
    if not target_judge.can_evaluate_category(project.category):
        return False
    if can_documentation and not target_judge.can_evaluate_documentation:
        return False
    if can_exposition and not target_judge.can_evaluate_exposition:
        return False
    if can_exposition and getattr(project, "requires_english_evaluation", False) and not target_judge.can_evaluate_english:
        return False
    return bool(can_documentation or can_exposition)


def _assignment_has_completed_entries(assignment: Assignment, judge_id: int, entries: list[dict]) -> bool:
    if not entries:
        return False
    project_evaluations = getattr(assignment.project, "evaluations", []) or []
    for entry in entries:
        entry_member_id = entry.get("project_member_id") or None
        if any(
            evaluation.judge_id == judge_id
            and evaluation.evaluation_type == entry["code"]
            and (evaluation.project_member_id or None) == entry_member_id
            and evaluation.percentage is not None
            for evaluation in project_evaluations
        ):
            return True
    return False


def _assignment_scope_completion(assignment: Assignment) -> tuple[bool, bool]:
    doc_entries = []
    expo_entries = []
    for entry in get_assignment_evaluation_entries(assignment):
        eval_type = entry.get("type")
        if entry["code"] == ENGLISH_EVAL_TYPE_CODE:
            expo_entries.append(entry)
            continue
        kind = infer_evaluation_type_kind(eval_type)
        if kind == "documentacion":
            doc_entries.append(entry)
        elif kind == "exposicion":
            expo_entries.append(entry)

    documentation_done = bool(
        assignment.can_evaluate_documentation
        and doc_entries
        and _assignment_has_completed_entries(assignment, assignment.judge_id, doc_entries)
    )
    exposition_done = bool(
        assignment.can_evaluate_exposition
        and expo_entries
        and _assignment_has_completed_entries(assignment, assignment.judge_id, expo_entries)
    )
    return documentation_done, exposition_done


def _apply_reassignment_to_target(
    target_judge: Judge,
    project,
    source_assignment: Assignment,
    can_documentation: bool,
    can_exposition: bool,
):
    if not _target_can_receive_assignment(target_judge, project, can_documentation, can_exposition):
        return None

    existing_assignment = Assignment.query.filter_by(
        judge_id=target_judge.id,
        project_id=project.id,
    ).first()
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
        judge_id=target_judge.id,
        project_id=project.id,
        can_evaluate_documentation=can_documentation,
        can_evaluate_exposition=can_exposition,
        status=Assignment.STATUS_CONFIRMED,
        notification_sent_at=None,
        notification_error=None,
    )
    replacement.judge = target_judge
    replacement.project = project
    db.session.add(replacement)
    return replacement


def balance_assignments_to_judge(target_judge: Judge, max_projects: int = 3) -> dict:
    """Move unfinished compatible assignment scopes to a low-load judge."""
    active_assignments = (
        Assignment.query.options(
            joinedload(Assignment.project).joinedload(Project.members),
            joinedload(Assignment.project).joinedload(Project.evaluations),
            joinedload(Assignment.judge),
        )
        .join(Project, Assignment.project_id == Project.id)
        .filter(Project.is_active == True)  # noqa: E712
        .all()
    )
    active_judges = (
        Judge.query.options(joinedload(Judge.assignments))
        .filter(
            Judge.role == Judge.ROLE_JUDGE,
            Judge.is_active_user == True,  # noqa: E712
        )
        .all()
    )
    load_by_judge = {}
    for assignment in active_assignments:
        load_by_judge.setdefault(assignment.judge_id, set()).add(assignment.project_id)

    target_load = len(load_by_judge.get(target_judge.id, set()))
    average_load = (len(active_assignments) + len(active_judges) - 1) // len(active_judges) if active_judges else 0
    desired_load = min(max_projects, max(1, average_load))
    remaining_slots = max(0, desired_load - target_load)

    summary = {
        "moved": 0,
        "unchanged": 0,
        "moves": [],
        "failed": [],
        "target_load_before": target_load,
        "target_load_after": target_load,
    }
    if remaining_slots <= 0:
        return summary

    source_assignments = sorted(
        [
            assignment
            for assignment in active_assignments
            if assignment.judge_id != target_judge.id
            and assignment.project
            and assignment.judge
            and assignment.judge.is_active_user
            and assignment.project_id not in load_by_judge.get(target_judge.id, set())
        ],
        key=lambda assignment: (
            -len(load_by_judge.get(assignment.judge_id, set())),
            assignment.project.title.lower() if assignment.project else "",
            assignment.id,
        ),
    )

    for assignment in source_assignments:
        if summary["moved"] >= remaining_slots:
            break
        source_load = len(load_by_judge.get(assignment.judge_id, set()))
        target_load = len(load_by_judge.get(target_judge.id, set()))
        if source_load <= target_load:
            continue

        project = assignment.project
        documentation_done, exposition_done = _assignment_scope_completion(assignment)
        move_documentation = bool(assignment.can_evaluate_documentation and not documentation_done)
        move_exposition = bool(assignment.can_evaluate_exposition and not exposition_done)
        if not move_documentation and not move_exposition:
            summary["unchanged"] += 1
            continue

        if not _target_can_receive_assignment(target_judge, project, move_documentation, move_exposition):
            summary["failed"].append(
                {
                    "project_title": project.title,
                    "scope": _scope_label(move_documentation, move_exposition),
                }
            )
            continue

        replacement = _apply_reassignment_to_target(
            target_judge,
            project,
            assignment,
            move_documentation,
            move_exposition,
        )
        if not replacement:
            summary["failed"].append(
                {
                    "project_title": project.title,
                    "scope": _scope_label(move_documentation, move_exposition),
                }
            )
            continue

        keep_documentation = bool(assignment.can_evaluate_documentation and documentation_done)
        keep_exposition = bool(assignment.can_evaluate_exposition and exposition_done)
        assignment.can_evaluate_documentation = keep_documentation
        assignment.can_evaluate_exposition = keep_exposition
        assignment.notification_sent_at = None
        assignment.notification_error = None
        if not assignment.can_evaluate_documentation and not assignment.can_evaluate_exposition:
            db.session.delete(assignment)
            load_by_judge.get(assignment.judge_id, set()).discard(project.id)

        load_by_judge.setdefault(target_judge.id, set()).add(project.id)
        summary["moved"] += 1
        summary["moves"].append(
            {
                "project_title": project.title,
                "from_judge_name": assignment.judge.full_name if assignment.judge else "",
                "to_judge_name": target_judge.full_name,
                "to_judge_email": target_judge.email,
                "scope": _scope_label(move_documentation, move_exposition),
                "assignment": replacement,
                "project": project,
                "judge": target_judge,
            }
        )

    summary["target_load_after"] = len(load_by_judge.get(target_judge.id, set()))
    return summary


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
