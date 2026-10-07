from collections import defaultdict
from datetime import datetime

from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models.assignment import Assignment
from app.models.assignment_process import AssignmentProcess, AssignmentProcessItem
from app.models.judge import Judge
from app.models.project import Project
from app.models.system_setting import SystemSetting
from app.models.evaluation import Evaluation
from app.services.expo_attendance_service import present_judge_ids
from app.services.evaluation_service import ENGLISH_EVAL_TYPE_CODE, infer_evaluation_type_kind


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


def generate_process_draft(process_type, *, deadline=None, created_by_id=None, present_only=False):
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
    SystemSetting.set_value(f'expo_present_draft_{process.id}', '1' if present_only else '0')

    projects = (
        Project.query.options(joinedload(Project.members), joinedload(Project.assignments))
        .filter(Project.is_active == True)  # noqa: E712
        .order_by(Project.created_at.asc(), Project.id.asc())
        .all()
    )
    if process_type == AssignmentProcess.TYPE_ENGLISH:
        projects = [project for project in projects if project.requires_english_evaluation]
    if present_only:
        projects = [p for p in projects if p.regional_status in {Project.STATUS_APPROVED,Project.STATUS_EVALUATED,Project.STATUS_REGIONAL_WINNER}]

    judges = (
        Judge.query.filter(Judge.role == Judge.ROLE_JUDGE, Judge.is_active_user == True, Judge.institution_id.isnot(None))  # noqa: E712
        .order_by(Judge.full_name.asc())
        .all()
    )
    judges = [judge for judge in judges if _judge_can_cover(judge, process_type)]
    present_ids = present_judge_ids() if present_only else None
    if present_only:
        if process_type == AssignmentProcess.TYPE_DOCUMENTATION:
            raise ValueError('El registro de llegada solo aplica a exposición e inglés.')
        judges = [judge for judge in judges if judge.id in present_ids]
        SystemSetting.set_value(f'expo_present_draft_{process.id}', '1')
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
            if assignment.status == Assignment.STATUS_CONFIRMED
            and assignment.judge
            and assignment.judge.institution_id
            and project.institution_id
            and assignment.judge.institution_id != project.institution_id
            and _assignment_covers(assignment, process_type)
            and (not present_only or assignment.judge_id in present_ids)
            and (not present_only or assignment.judge.is_active_user and _judge_can_cover(assignment.judge,process_type) and assignment.judge.can_evaluate_category(project.category))
        ]
        if present_only:
            current = current[:target]
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
                and project.institution_id
                and judge.institution_id != project.institution_id
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
    if present_only:
        SystemSetting.set_value(f'expo_missing_draft_{process.id}', str(len(missing_projects)))
    return process, missing_projects


def approve_process(process, approved_by_id=None):
    if process.status != AssignmentProcess.STATUS_DRAFT:
        raise ValueError("Solo se puede aprobar un borrador.")
    if not process.items:
        raise ValueError("El borrador no contiene nuevas asignaciones.")

    present_only = SystemSetting.get_value(f'expo_present_draft_{process.id}', '0') == '1'
    if present_only:
        if SystemSetting.get_value(f'expo_missing_draft_{process.id}', '0') != '0':
            raise ValueError('El borrador tiene proyectos sin cobertura completa. Registra más jueces y regenera la distribución.')
        present_ids = present_judge_ids()
        planned = defaultdict(set)
        for item in process.items:
            if item.judge_id not in present_ids or not item.judge.is_active_user or not _judge_can_cover(item.judge, process.process_type) or not item.judge.can_evaluate_category(item.project.category):
                raise ValueError('Cambió la presencia o disponibilidad de un juez. Genera nuevamente el borrador.')
            planned[item.project_id].add(item.judge_id)
        target = TARGETS[process.process_type]
        if any(len(ids) != target for ids in planned.values()):
            raise ValueError('No se puede aprobar: hay proyectos sin cobertura completa. Registra más jueces compatibles y regenera el borrador.')
        from app.models.category import Category
        codes = {t.code for c in Category.query.all() for t in (c.rubric_1_evaluation_type,c.rubric_2_evaluation_type) if t and infer_evaluation_type_kind(t) == 'exposicion'} if process.process_type == AssignmentProcess.TYPE_EXPOSITION else {ENGLISH_EVAL_TYPE_CODE}
        for evaluation in Evaluation.query.filter(Evaluation.project_id.in_(planned), Evaluation.evaluation_type.in_(codes)).all():
            if evaluation.judge_id not in planned[evaluation.project_id]:
                raise ValueError('Hay evaluaciones guardadas de un juez que se quitaría. Revisa la distribución antes de modificarla.')
        for assignment in Assignment.query.filter(Assignment.project_id.in_(planned)).all():
            if assignment.judge_id not in planned[assignment.project_id]:
                if process.process_type == AssignmentProcess.TYPE_EXPOSITION: assignment.can_evaluate_exposition = False
                else: assignment.can_evaluate_english = False

    for item in process.items:
        judge = item.judge
        project = item.project
        if not judge.institution_id or not project.institution_id:
            raise ValueError(f"No se puede aprobar: {judge.full_name} o el proyecto no tiene colegio vinculado.")
        if judge.institution_id == project.institution_id:
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
