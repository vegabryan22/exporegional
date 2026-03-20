from __future__ import annotations

from app import create_app
from app.extensions import db
from app.models.evaluation import Evaluation
from app.models.evaluation_score import EvaluationScore
from app.models.evaluation_type import EvaluationType
from app.models.project import Project
from app.services.evaluation_service import get_project_available_evaluation_types


COMMENTS = [
    "La presentacion evidencia dominio general del proyecto.",
    "Se observa una propuesta clara con margen de mejora en la argumentacion.",
    "El equipo muestra buena preparacion y consistencia tecnica.",
    "La solucion responde bien al problema planteado y puede fortalecerse en detalles de implementacion.",
]

RECOMMENDATIONS = [
    "Fortalecer la justificacion tecnica y practicar la defensa oral.",
    "Mejorar la evidencia visual del proceso y ordenar mejor los hallazgos.",
    "Profundizar en pruebas, resultados y conclusiones para la exposicion final.",
    "Refinar la documentacion para mostrar mejor el impacto del proyecto.",
]


def _score_for(project_id: int, judge_id: int, eval_type_id: int, criterion_id: int, min_score: int, max_score: int) -> int:
    span = max_score - min_score + 1
    seed = (project_id * 17) + (judge_id * 11) + (eval_type_id * 7) + (criterion_id * 3)
    return min_score + (seed % span)


def seed():
    evaluation_types = {
        item.code: item
        for item in EvaluationType.query.filter_by(is_active=True).all()
    }
    criteria_by_type = {
        item.code: sorted(
            [criterion for criterion in item.rubric_criteria if criterion.is_active],
            key=lambda criterion: (criterion.section_sort_order, criterion.sort_order, criterion.id),
        )
        for item in evaluation_types.values()
    }

    created = 0
    skipped = 0
    projects = Project.query.order_by(Project.id.asc()).all()
    for project in projects:
        available_types = get_project_available_evaluation_types(project)
        if not available_types:
            continue

        existing_codes_by_judge = {}
        for evaluation in project.evaluations:
            existing_codes_by_judge.setdefault(evaluation.judge_id, set()).add(evaluation.evaluation_type)

        for assignment in project.assignments:
            judge_id = assignment.judge_id
            for eval_type in available_types:
                if eval_type.code in existing_codes_by_judge.get(judge_id, set()):
                    skipped += 1
                    continue

                criteria = criteria_by_type.get(eval_type.code, [])
                if not criteria:
                    skipped += 1
                    continue

                scores = []
                total_score = 0
                max_score = 0
                for criterion in criteria:
                    value = _score_for(
                        project_id=project.id,
                        judge_id=judge_id,
                        eval_type_id=eval_type.id,
                        criterion_id=criterion.id,
                        min_score=criterion.min_score,
                        max_score=criterion.max_score,
                    )
                    total_score += value
                    max_score += criterion.max_score
                    scores.append(
                        EvaluationScore(
                            rubric_criterion_id=criterion.id,
                            score=value,
                            observation=f"Punto observado en {criterion.name.lower()[:90]}.",
                        )
                    )

                percentage = round((total_score / max_score) * 100, 2) if max_score else 0
                evaluation = Evaluation(
                    judge_id=judge_id,
                    project_id=project.id,
                    evaluation_type=eval_type.code,
                    criteria_1=scores[0].score if len(scores) > 0 else None,
                    criteria_2=scores[1].score if len(scores) > 1 else None,
                    criteria_3=scores[2].score if len(scores) > 2 else None,
                    criteria_4=scores[3].score if len(scores) > 3 else None,
                    comments=COMMENTS[(project.id + judge_id) % len(COMMENTS)],
                    recommendations=RECOMMENDATIONS[(project.id + eval_type.id) % len(RECOMMENDATIONS)],
                    max_score=max_score,
                    percentage=percentage,
                )
                db.session.add(evaluation)
                db.session.flush()
                for score in scores:
                    score.evaluation_id = evaluation.id
                    db.session.add(score)

                existing_codes_by_judge.setdefault(judge_id, set()).add(eval_type.code)
                created += 1

    db.session.commit()
    print(f"Evaluaciones creadas: {created}")
    print(f"Combinaciones omitidas por existir o no tener rubrica activa: {skipped}")
    print(f"Total evaluaciones ahora: {Evaluation.query.count()}")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        seed()
