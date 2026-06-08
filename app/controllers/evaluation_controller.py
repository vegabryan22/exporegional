from collections import OrderedDict

from flask import abort, current_app, flash, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models.assignment import Assignment
from app.models.category import Category
from app.models.evaluation import Evaluation
from app.models.evaluation_score import EvaluationScore
from app.models.project import Project
from app.services.audit_service import log_event
from app.services.evaluation_service import get_project_available_evaluation_types, get_project_evaluations_summary
from app.services.parameter_service import get_active_evaluation_types, get_active_rubrics_map


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


@login_required
def dashboard():
    assignments = (
        Assignment.query.filter_by(judge_id=current_user.id)
        .join(Project, Project.id == Assignment.project_id)
        .order_by(Project.created_at.desc())
        .all()
    )
    evaluation_map = {
        (e.project_id, e.evaluation_type): e
        for e in Evaluation.query.filter_by(judge_id=current_user.id).all()
    }
    category_map = {category.code: category.name for category in Category.query.all()}
    project_eval_types = {}
    project_summaries = {}
    for assignment in assignments:
        project_eval_types[assignment.project_id] = get_project_available_evaluation_types(assignment.project)
        project_summaries[assignment.project_id] = get_project_evaluations_summary(assignment.project)
    return render_template(
        "judge/dashboard.html",
        assignments=assignments,
        evaluation_map=evaluation_map,
        category_map=category_map,
        project_eval_types=project_eval_types,
        project_summaries=project_summaries,
    )


@login_required
def project_document(project_id: int):
    project = Project.query.get_or_404(project_id)
    assignment = Assignment.query.filter_by(judge_id=current_user.id, project_id=project_id).first()
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
    project = Project.query.get_or_404(project_id)
    evaluation_types = get_project_available_evaluation_types(project)
    eval_type_map = {item.code: item for item in evaluation_types}

    if eval_type not in eval_type_map:
        abort(400, "Tipo de evaluacion invalido.")

    rubric_map = get_active_rubrics_map()
    criteria = rubric_map.get(eval_type, [])
    if not criteria:
        abort(400, "No hay rubricas configuradas para este tipo de evaluacion.")
    scale_options, score_labels = _resolve_scale(eval_type_map[eval_type], criteria)
    criteria_sections = OrderedDict()
    for criterion in criteria:
        section_name = criterion.section_name or "General"
        criteria_sections.setdefault(section_name, []).append(criterion)

    assignment = Assignment.query.filter_by(judge_id=current_user.id, project_id=project_id).first()
    if not assignment:
        abort(403, "No tienes permiso para evaluar este proyecto.")
    existing = Evaluation.query.filter_by(
        judge_id=current_user.id,
        project_id=project_id,
        evaluation_type=eval_type,
    ).first()

    if existing:
        flash("Ya registraste esta evaluacion.", "error")
        return redirect(url_for("judge.dashboard"))

    if request.method == "POST":
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
                f"juez={current_user.full_name}, tipo={eval_type}, porcentaje={percentage}"
            ),
        )
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
    )
