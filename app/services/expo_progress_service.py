"""Public, score-free event progress and persistent venue configuration."""
import json
from datetime import datetime, timezone
from sqlalchemy.orm import joinedload
from app.models.project import Project
from app.models.assignment import Assignment
from app.models.category import Category
from app.models.system_setting import SystemSetting
from app.services.evaluation_service import ENGLISH_EVAL_TYPE_CODE, infer_evaluation_type_kind

VENUE_SETTING = "expo_venues"

def venue_config():
    try:
        value = json.loads(SystemSetting.get_value(VENUE_SETTING, "{}"))
        if isinstance(value, dict) and isinstance(value.get("venues", []), list) and isinstance(value.get("projects", {}), dict):
            return {"venues": value.get("venues", []), "projects": value.get("projects", {})}
    except (ValueError, TypeError):
        pass
    return {"venues": [], "projects": {}}

def project_progress(project, exposition_codes, *, include_pending_judges=False):
    # Count distinct evaluators, never assignment rows or duplicate submissions.
    expo = {e.judge_id for e in project.evaluations if e.judge_id and e.evaluation_type in exposition_codes}
    members = {m.id for m in project.members if m.participates_in_english}
    english_judges = {a.judge_id for a in project.assignments if a.status == Assignment.STATUS_CONFIRMED and a.can_evaluate_english and a.judge and a.judge.can_evaluate_english}
    english_pairs = {(e.judge_id, e.project_member_id) for e in project.evaluations if e.evaluation_type == ENGLISH_EVAL_TYPE_CODE and e.project_member_id in members and e.judge_id in english_judges}
    expected = len(members) * max(1, len(english_judges)) if members else 0
    complete = len(expo) == 3 and (not members or bool(english_judges) and len(english_pairs) == expected)
    status = "complete" if complete else "pending" if expo or english_pairs else "not_started"
    if len(expo) > 3:
        status = "review"
    row = {
        "id": project.id, "title": project.title,
        "school": project.institution.name if project.institution else (project.institution_name or "Sin colegio"),
        "category": project.category, "exposition": len(expo), "exposition_expected": 3,
        "english": len(english_pairs), "english_expected": expected,
        "english_participants": len(members), "english_unassigned": bool(members and not english_judges),
        "status": status,
    }
    if include_pending_judges:
        assignments = [a for a in project.assignments if a.status == Assignment.STATUS_CONFIRMED and a.judge]
        expo_assigned = {a.judge_id for a in assignments if a.can_evaluate_exposition}
        row["pending_judges"] = {
            "exposition": [{"name": a.judge.full_name} for a in assignments if a.can_evaluate_exposition and a.judge_id not in expo],
            "english": [{"name": a.judge.full_name, "completed": sum(j == a.judge_id for j, m in english_pairs), "expected": len(members)} for a in assignments if members and a.judge_id in english_judges and sum(j == a.judge_id for j, m in english_pairs) < len(members)],
            "exposition_unassigned": max(0, 3 - len(expo_assigned)),
        }
    return row

def public_progress(*, include_pending_judges=False):
    config = venue_config()
    categories = Category.query.all()
    exposition_codes = {t.code for c in categories for t in (c.rubric_1_evaluation_type, c.rubric_2_evaluation_type) if t and infer_evaluation_type_kind(t) == "exposicion"}
    projects = Project.query.options(joinedload(Project.members), joinedload(Project.evaluations), joinedload(Project.institution), joinedload(Project.assignments).joinedload(Assignment.judge)).filter(
        Project.is_active.is_(True), Project.regional_status.in_([Project.STATUS_APPROVED, Project.STATUS_EVALUATED, Project.STATUS_REGIONAL_WINNER])
    ).order_by(Project.title).all()
    groups = [{"id": v["id"], "name": v["name"], "projects": []} for v in config["venues"]]
    groups.append({"id": "unassigned", "name": "Sin recinto asignado", "projects": []})
    by_id = {v["id"]: v for v in groups}
    rows = []
    for project in projects:
        row = project_progress(project, exposition_codes, include_pending_judges=include_pending_judges)
        group = by_id.get(config["projects"].get(str(project.id)), by_id["unassigned"])
        group["projects"].append(row)
        rows.append(row)
    for group in groups:
        group["complete"] = sum(r["status"] == "complete" for r in group["projects"])
    return {"venues": groups, "total": len(rows), "complete": sum(r["status"] == "complete" for r in rows), "updated_at": datetime.now(timezone.utc).isoformat(), "categories": [{"code": c.code, "name": c.name} for c in categories]}
