"""Sincroniza estados regionales derivados de las evaluaciones."""

from collections import defaultdict

from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models.assignment import Assignment
from app.models.evaluation import Evaluation
from app.models.project import Project
from app.models.project_status_history import ProjectStatusHistory
from app.services.evaluation_service import (
    get_project_evaluations_summary,
    project_evaluation_count_summary,
    project_evaluation_target_summary,
)


DERIVED_STATUSES = {
    Project.STATUS_APPROVED,
    Project.STATUS_EVALUATED,
    Project.STATUS_REGIONAL_WINNER,
}


def _set_derived_status(project, target_status, note):
    source_status = project.regional_status
    if source_status == target_status:
        return False
    project.regional_status = target_status
    db.session.add(
        ProjectStatusHistory(
            project=project,
            from_status=source_status,
            to_status=target_status,
            changed_by_id=None,
            notes=note,
        )
    )
    return True


def sync_regional_outcomes():
    """Marca evaluados y ganadores sin intervención administrativa manual."""
    projects = (
        Project.query.options(
            joinedload(Project.assignments).joinedload(Assignment.judge),
            joinedload(Project.evaluations).joinedload(Evaluation.project_member),
            joinedload(Project.members),
        )
        .filter(Project.is_active.is_(True), Project.regional_status != Project.STATUS_DRAFT)
        .all()
    )
    changed = False
    completion = {}

    for project in projects:
        if project.regional_status not in DERIVED_STATUSES:
            continue
        target = project_evaluation_target_summary(project)
        count = project_evaluation_count_summary(project)
        expected = target["expected_evaluations"]
        completed = count["completed_evaluations"]
        is_complete = (
            expected > 0
            and count["completed_documentation_evaluations"] >= target["expected_documentation_evaluations"]
            and count["completed_exposition_evaluations"] >= target["expected_exposition_evaluations"]
        )
        completion[project.id] = {
            "expected": expected,
            "completed": completed,
            "is_complete": is_complete,
        }
        target_status = Project.STATUS_EVALUATED if is_complete else Project.STATUS_APPROVED
        changed |= _set_derived_status(
            project,
            target_status,
            "Estado sincronizado automáticamente según evaluaciones completas.",
        )

    by_category = defaultdict(list)
    for project in projects:
        by_category[(project.category or "").strip().lower()].append(project)

    for category_code, category_projects in by_category.items():
        if not category_code or not category_projects or not all(completion.get(row.id, {}).get("is_complete", False) for row in category_projects):
            continue
        scored = []
        for project in category_projects:
            grade = get_project_evaluations_summary(project).get("final_grade")
            if grade is not None:
                scored.append((grade, project))
        if len(scored) != len(category_projects):
            continue
        best_grade = max(grade for grade, _ in scored)
        leaders = [project for grade, project in scored if grade == best_grade]
        if len(leaders) != 1:
            continue
        winner = leaders[0]
        changed |= _set_derived_status(
            winner,
            Project.STATUS_REGIONAL_WINNER,
            f"Ganador automático de la categoría {category_code} con nota {best_grade:.2f}.",
        )

    return {"changed": changed, "completion": completion}
