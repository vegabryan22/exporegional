from collections import OrderedDict
from datetime import datetime, timedelta, timezone

from flask import abort, current_app, flash, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models.assignment import Assignment
from app.models.category import Category
from app.models.evaluation import Evaluation
from app.models.evaluation_score import EvaluationScore
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.system_setting import SystemSetting
from app.services.audit_service import log_event
from app.services.evaluation_service import (
    ENGLISH_EVAL_TYPE_CODE,
    assignment_allows_evaluation_type,
    get_assignment_evaluation_entries,
    get_assignment_available_evaluation_types,
    get_project_available_evaluation_types,
    get_project_evaluations_summary,
    infer_evaluation_type_kind,
)
from app.services.parameter_service import get_active_evaluation_types, get_active_rubrics_map
from app.services.regional_outcome_service import sync_regional_outcomes


def _str_to_bool(value) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "si", "sí", "on"}


def _scope_from_form(value: str) -> tuple[bool, bool]:
    normalized = (value or "ambas").strip().lower()
    if normalized == "documento":
        return True, False
    if normalized == "exposicion":
        return False, True
    return True, True


def _category_scope_from_form(value: str) -> str:
    normalized = (value or "ambas").strip().lower()
    if normalized in {"steam", "emprendimiento", "ambas"}:
        return normalized
    return "ambas"


def _validate_score(raw_value, min_score: int, max_score: int):
    try:
        number = int(raw_value)
    except (ValueError, TypeError):
        return None
    return number if min_score <= number <= max_score else None


def _resolve_scale(eval_type_obj, criteria):
    if not criteria:
        return [], {}
    max_score = max(item.max_score for item in criteria)
    min_score = min(item.min_score for item in criteria)
    scale_options = list(range(max_score, min_score - 1, -1))
    score_labels = eval_type_obj.get_scale_labels()
    if not score_labels and max_score == 3 and min_score == 0:
        score_labels = {3: "Logrado", 2: "Parcialmente logrado", 1: "No logrado", 0: "Ausente"}
    return scale_options, score_labels


def _expo_submission_gate(eval_type_obj):
    is_expo_type = (
        getattr(eval_type_obj, "code", "") == ENGLISH_EVAL_TYPE_CODE
        or infer_evaluation_type_kind(eval_type_obj) == "exposicion"
    )
    if not is_expo_type:
        return {"locked": False, "open_date": None, "open_date_raw": ""}

    raw_date = (SystemSetting.get_value("expo_evaluation_open_date", "") or "").strip()
    if not raw_date:
        return {"locked": False, "open_date": None, "open_date_raw": ""}

    try:
        open_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
    except ValueError:
        return {"locked": False, "open_date": None, "open_date_raw": raw_date}

    return {
        "locked": (datetime.now(timezone.utc) - timedelta(hours=6)).date() < open_date,
        "open_date": open_date,
        "open_date_raw": raw_date,
    }


@login_required
def dashboard():
    assignments = (
        Assignment.query.filter_by(judge_id=current_user.id, status=Assignment.STATUS_CONFIRMED)
        .join(Project, Project.id == Assignment.project_id)
        .order_by(Project.created_at.desc())
        .all()
    )
    evaluation_map = {
        (e.project_id, e.evaluation_type, e.project_member_id or 0): e
        for e in Evaluation.query.filter_by(judge_id=current_user.id).all()
    }
    category_map = {category.code: category.name for category in Category.query.all()}
    project_eval_types = {}
    project_eval_entries = {}
    project_summaries = {}
    pending_document_entries = []
    for assignment in assignments:
        project_eval_types[assignment.project_id] = get_assignment_available_evaluation_types(assignment)
        project_eval_entries[assignment.project_id] = get_assignment_evaluation_entries(assignment)
        project_summaries[assignment.project_id] = get_project_evaluations_summary(assignment.project)
        for eval_entry in project_eval_entries[assignment.project_id]:
            if infer_evaluation_type_kind(eval_entry.get("type")) != "documentacion":
                continue
            eval_key = (assignment.project_id, eval_entry["code"], eval_entry.get("project_member_id") or 0)
            if eval_key not in evaluation_map:
                pending_document_entries.append({"assignment": assignment, "entry": eval_entry})
    return render_template(
        "judge/dashboard.html",
        assignments=assignments,
        evaluation_map=evaluation_map,
        category_map=category_map,
        project_eval_types=project_eval_types,
        project_eval_entries=project_eval_entries,
        project_summaries=project_summaries,
        pending_document_entries=pending_document_entries,
        document_reminder_deadline=SystemSetting.get_value("document_evaluation_reminder_deadline", ""),
    )


@login_required
def profile():
    if request.method != "POST":
        return redirect(url_for("judge.dashboard"))

    current_user.can_evaluate_documentation, current_user.can_evaluate_exposition = _scope_from_form(
        request.form.get("judge_evaluation_scope")
    )
    current_user.can_evaluate_english = _str_to_bool(request.form.get("judge_can_evaluate_english"))
    current_user.category_scope = _category_scope_from_form(request.form.get("judge_category_scope"))
    current_user.job_title = request.form.get("judge_job_title", "").strip()
    current_user.institution = request.form.get("judge_institution", "").strip()
    current_user.phone = request.form.get("judge_phone", "").strip()
    db.session.commit()
    log_event(
        "judge.profile.update",
        "judge",
        entity_id=current_user.id,
        detail=(
            f"Disponibilidad actualizada por juez: categoria={current_user.category_scope}, "
            f"ingles={current_user.can_evaluate_english}, alcance={current_user.evaluation_scope_label}"
        ),
    )
    flash("Disponibilidad actualizada correctamente.", "success")
    return redirect(url_for("judge.dashboard"))


@login_required
def project_document(project_id: int):
    project = Project.query.get_or_404(project_id)
    assignment = Assignment.query.filter_by(
        judge_id=current_user.id,
        project_id=project_id,
        status=Assignment.STATUS_CONFIRMED,
    ).first()
    if not assignment:
        abort(403, "No tienes permiso para ver este documento.")
    if not project.project_document_path:
        abort(404, "Este proyecto no tiene documento adjunto.")

    document_path = project.project_document_path.strip().lstrip("/\\").replace("\\", "/")
    if not document_path:
        abort(404, "Este proyecto no tiene documento adjunto.")
    return send_from_directory(current_app.static_folder, document_path, as_attachment=False)


@login_required
def evaluate(project_id: int):
    eval_type = request.args.get("type", "").strip()
    project_member_id = request.args.get("member_id", default=0, type=int) or None
    project = Project.query.get_or_404(project_id)
    evaluation_types = get_project_available_evaluation_types(project)
    eval_type_map = {item.code: item for item in evaluation_types}

    if eval_type not in eval_type_map:
        abort(400, "Tipo de evaluacion invalido.")

    assignment = Assignment.query.filter_by(
        judge_id=current_user.id,
        project_id=project_id,
        status=Assignment.STATUS_CONFIRMED,
    ).first()
    if not assignment:
        abort(403, "No tienes permiso para evaluar este proyecto.")
    if not assignment_allows_evaluation_type(assignment, eval_type_map[eval_type]):
        abort(403, "No tienes permiso para registrar este tipo de evaluacion.")

    project_member = None
    if eval_type == ENGLISH_EVAL_TYPE_CODE:
        if not current_user.can_evaluate_english:
            abort(403, "No tienes permiso para evaluar exposicion en ingles.")
        if not project_member_id:
            abort(400, "Selecciona el estudiante que expone en ingles.")
        project_member = ProjectMember.query.filter_by(id=project_member_id, project_id=project.id).first_or_404()
        if not project_member.participates_in_english:
            abort(400, "Este estudiante no esta marcado para exposicion en ingles.")

    rubric_map = get_active_rubrics_map()
    criteria = rubric_map.get(eval_type, [])
    if not criteria:
        abort(400, "No hay rubricas configuradas para este tipo de evaluacion.")
    scale_options, score_labels = _resolve_scale(eval_type_map[eval_type], criteria)
    criteria_sections = OrderedDict()
    for criterion in criteria:
        section_name = criterion.section_name or "General"
        criteria_sections.setdefault(section_name, []).append(criterion)

    existing = Evaluation.query.filter_by(
        judge_id=current_user.id,
        project_id=project_id,
        evaluation_type=eval_type,
        project_member_id=project_member.id if project_member else None,
    ).first()

    if existing:
        flash("Ya registraste esta evaluacion.", "error")
        return redirect(url_for("judge.dashboard"))

    submission_gate = _expo_submission_gate(eval_type_map[eval_type])

    if request.method == "POST":
        if submission_gate["locked"]:
            flash(
                f"La evaluacion de exposicion se habilita el {submission_gate['open_date'].strftime('%d/%m/%Y')}. Puedes ver la rubrica, pero no registrar calificacion antes de esa fecha.",
                "error",
            )
            redirect_args = {"project_id": project.id, "type": eval_type}
            if project_member:
                redirect_args["member_id"] = project_member.id
            return redirect(url_for("judge.evaluate", **redirect_args))

        total_score = 0
        max_score = 0
        scores = []
        for criterion in criteria:
            score = _validate_score(
                request.form.get(f"criterion_{criterion.id}"), criterion.min_score, criterion.max_score
            )
            if score is None:
                flash(
                    f"El criterio '{criterion.name}' debe estar entre {criterion.min_score} y {criterion.max_score}.",
                    "error",
                )
                return render_template(
                    "judge/evaluate.html",
                    project=project,
                    eval_type=eval_type,
                    eval_type_name=eval_type_map[eval_type].name,
                    criteria=criteria,
                    criteria_sections=criteria_sections,
                    score_labels=score_labels,
                    scale_options=scale_options,
                    project_member=project_member,
                    submission_gate=submission_gate,
                )
            total_score += score
            max_score += criterion.max_score
            scores.append(
                EvaluationScore(
                    rubric_criterion_id=criterion.id,
                    score=score,
                    observation=request.form.get(f"observation_{criterion.id}", "").strip(),
                )
            )

        comments = request.form.get("comments", "").strip()
        recommendations = request.form.get("recommendations", "").strip()
        percentage = round((total_score / max_score) * 100, 2) if max_score else 0

        evaluation = Evaluation(
            judge_id=current_user.id,
            project_id=project.id,
            project_member_id=project_member.id if project_member else None,
            evaluation_type=eval_type,
            criteria_1=scores[0].score if len(scores) > 0 else None,
            criteria_2=scores[1].score if len(scores) > 1 else None,
            criteria_3=scores[2].score if len(scores) > 2 else None,
            criteria_4=scores[3].score if len(scores) > 3 else None,
            comments=comments,
            recommendations=recommendations,
            max_score=max_score,
            percentage=percentage,
        )
        db.session.add(evaluation)
        db.session.flush()
        for item in scores:
            item.evaluation_id = evaluation.id
            db.session.add(item)
        log_event(
            "judge.evaluation.create",
            "evaluation",
            entity_id=evaluation.id,
            detail=(
                f"Evaluacion registrada: proyecto=#{project.id} '{project.title}', "
                f"juez={current_user.full_name}, tipo={eval_type}, "
                f"integrante={project_member.full_name if project_member else 'proyecto'}, porcentaje={percentage}"
            ),
        )
        db.session.flush()
        db.session.expire_all()
        sync_regional_outcomes()
        db.session.commit()
        flash("Evaluacion registrada correctamente.", "success")
        return redirect(url_for("judge.dashboard"))

    return render_template(
        "judge/evaluate.html",
        project=project,
        eval_type=eval_type,
        eval_type_name=eval_type_map[eval_type].name,
        criteria=criteria,
        criteria_sections=criteria_sections,
        score_labels=score_labels,
        scale_options=scale_options,
        project_member=project_member,
        submission_gate=submission_gate,
    )
