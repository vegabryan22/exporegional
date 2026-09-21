from collections import defaultdict
from datetime import datetime

from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models.assignment import Assignment
from app.models.assignment_process import AssignmentProcess, AssignmentProcessItem
from app.models.judge import Judge
from app.models.project import Project


TARGETS = {
    AssignmentProcess.TYPE_DOCUMENTATION: 3,
    AssignmentProcess.TYPE_EXPOSITION: 3,
    AssignmentProcess.TYPE_ENGLISH: 1,
}


def _assignment_covers(assignment, process_type):
    if process_type == AssignmentProcess.TYPE_DOCUMENTATION:
        return bool(assignment.can_evaluate_documentation)
    if process_type == AssignmentProcess.TYPE_EXPOSITION:
        return bool(assignment.can_evaluate_exposition)
    return bool(getattr(assignment, "can_evaluate_english", False))


def _judge_can_cover(judge, process_type):
    if process_type == AssignmentProcess.TYPE_DOCUMENTATION:
        return bool(judge.can_evaluate_documentation)
    if process_type == AssignmentProcess.TYPE_EXPOSITION:
        return bool(judge.can_evaluate_exposition)
    return bool(judge.can_evaluate_english and judge.can_evaluate_exposition)


def generate_process_draft(process_type, *, deadline=None, created_by_id=None):
    if process_type not in AssignmentProcess.VALID_TYPES:
        raise ValueError("Tipo de proceso no válido.")
    if process_type == AssignmentProcess.TYPE_DOCUMENTATION and not deadline:
        raise ValueError("La fecha límite del documento escrito es obligatoria.")

    old_drafts = AssignmentProcess.query.filter_by(
        process_type=process_type,
        status=AssignmentProcess.STATUS_DRAFT,
    ).all()
    for old in old_drafts:
        db.session.delete(old)
    db.session.flush()

    process = AssignmentProcess(
        process_type=process_type,
        deadline=deadline,
        created_by_id=created_by_id,
    )
    db.session.add(process)
    db.session.flush()

    projects = (
        Project.query.options(joinedload(Project.members), joinedload(Project.assignments))
        .filter(Project.is_active == True)  # noqa: E712
        .order_by(Project.created_at.asc(), Project.id.asc())
        .all()
    )
    if process_type == AssignmentProcess.TYPE_ENGLISH:
        projects = [project for project in projects if project.requires_english_evaluation]

    judges = (
        Judge.query.filter(Judge.role == Judge.ROLE_JUDGE, Judge.is_active_user == True)  # noqa: E712
        .order_by(Judge.full_name.asc())
        .all()
    )
    judges = [judge for judge in judges if _judge_can_cover(judge, process_type)]
    target = TARGETS[process_type]
    load = defaultdict(int)
    for assignment in Assignment.query.filter_by(status=Assignment.STATUS_CONFIRMED).all():
        if _assignment_covers(assignment, process_type):
            load[assignment.judge_id] += 1

    missing_projects = []
    for project in projects:
        current = [
            assignment
            for assignment in project.assignments
            if assignment.status == Assignment.STATUS_CONFIRMED and _assignment_covers(assignment, process_type)
        ]
        for assignment in current[:target]:
            db.session.add(
                AssignmentProcessItem(
                    process_id=process.id,
                    judge_id=assignment.judge_id,
                    project_id=project.id,
                )
            )
        needed = max(0, target - len(current))
        used_ids = {assignment.judge_id for assignment in current}
        for _ in range(needed):
            candidates = [
                judge
                for judge in judges
                if judge.id not in used_ids
                and (not judge.institution_id or not project.institution_id or judge.institution_id != project.institution_id)
                and judge.can_evaluate_category(project.category)
            ]
            if not candidates:
                break
            judge = min(candidates, key=lambda row: (load[row.id], (row.full_name or "").casefold(), row.id))
            db.session.add(AssignmentProcessItem(process_id=process.id, judge_id=judge.id, project_id=project.id))
            used_ids.add(judge.id)
            load[judge.id] += 1
        if len(current) + len(used_ids - {assignment.judge_id for assignment in current}) < target:
            missing_projects.append(project.title)

    db.session.flush()
    return process, missing_projects


def approve_process(process, approved_by_id=None):
    if process.status != AssignmentProcess.STATUS_DRAFT:
        raise ValueError("Solo se puede aprobar un borrador.")
    if not process.items:
        raise ValueError("El borrador no contiene nuevas asignaciones.")

    for item in process.items:
        judge = item.judge
        project = item.project
        if judge.institution_id and project.institution_id and judge.institution_id == project.institution_id:
            raise ValueError(f"{judge.full_name} no puede evaluar un proyecto de su propia institución.")
        assignment = Assignment.query.filter_by(judge_id=item.judge_id, project_id=item.project_id).first()
        if not assignment:
            assignment = Assignment(
                judge_id=item.judge_id,
                project_id=item.project_id,
                can_evaluate_documentation=False,
                can_evaluate_exposition=False,
                can_evaluate_english=False,
                status=Assignment.STATUS_CONFIRMED,
            )
            db.session.add(assignment)
        assignment.status = Assignment.STATUS_CONFIRMED
        if process.process_type == AssignmentProcess.TYPE_DOCUMENTATION:
            assignment.can_evaluate_documentation = True
        elif process.process_type == AssignmentProcess.TYPE_EXPOSITION:
            assignment.can_evaluate_exposition = True
        else:
            assignment.can_evaluate_english = True

    db.session.flush()
    affected_projects = {item.project_id for item in process.items}
    target = TARGETS[process.process_type]
    for project_id in affected_projects:
        assignments = Assignment.query.filter_by(project_id=project_id, status=Assignment.STATUS_CONFIRMED).all()
        count = sum(1 for assignment in assignments if _assignment_covers(assignment, process.process_type))
        if count != target:
            raise ValueError(f"La cobertura resultante no es exacta: {count}/{target}.")

    process.status = AssignmentProcess.STATUS_APPROVED
    process.approved_by_id = approved_by_id
    process.approved_at = datetime.now()
    return process
