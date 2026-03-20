from __future__ import annotations

import argparse

from app import create_app
from app.extensions import db
from app.models.evaluation import Evaluation
from app.models.evaluation_score import EvaluationScore
from sqlalchemy.orm import joinedload


LOW_COMMENTS = [
    "La evaluacion evidencia avances iniciales, pero todavia hay varios aspectos por consolidar.",
    "El proyecto necesita mayor claridad en su planteamiento y en la forma de comunicar resultados.",
    "Se observan oportunidades importantes de mejora en estructura, defensa y evidencia tecnica.",
]

MID_COMMENTS = [
    "El proyecto muestra una base solida con algunos puntos que pueden fortalecerse antes de la fase final.",
    "La propuesta esta bien encaminada y requiere ajustar varios detalles para destacar mejor.",
    "Se aprecia un trabajo consistente, aunque aun hay margen para mejorar profundidad y presentacion.",
]

HIGH_COMMENTS = [
    "El desempeno fue sobresaliente y se observo un dominio claro de la propuesta presentada.",
    "La evidencia tecnica, la comunicacion y la consistencia general fueron muy solidas.",
    "El proyecto destaca por su claridad, orden y nivel de preparacion durante la evaluacion.",
]

LOW_RECOMMENDATIONS = [
    "Reforzar fundamentos, documentacion y preparacion de la presentacion.",
    "Trabajar con mayor profundidad en resultados, conclusiones y defensa del proyecto.",
    "Practicar la exposicion y mejorar la evidencia de implementacion.",
]

MID_RECOMMENDATIONS = [
    "Afinar la presentacion, ordenar mejor la evidencia y fortalecer la argumentacion tecnica.",
    "Mejorar la claridad de resultados y conectar mejor problema, solucion e impacto.",
    "Profundizar en detalles puntuales para elevar la calidad global de la propuesta.",
]

HIGH_RECOMMENDATIONS = [
    "Mantener el nivel mostrado y pulir detalles finales para la presentacion definitiva.",
    "Conservar la consistencia actual y reforzar solo aspectos menores de forma y cierre.",
    "Continuar con el mismo enfoque y preparar una defensa final aun mas precisa.",
]

def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _comment_for(percentage: float) -> tuple[str, str]:
    if percentage < 45:
        idx = int(percentage) % len(LOW_COMMENTS)
        return LOW_COMMENTS[idx], LOW_RECOMMENDATIONS[idx]
    if percentage < 75:
        idx = int(percentage) % len(MID_COMMENTS)
        return MID_COMMENTS[idx], MID_RECOMMENDATIONS[idx]
    idx = int(percentage) % len(HIGH_COMMENTS)
    return HIGH_COMMENTS[idx], HIGH_RECOMMENDATIONS[idx]


def _stable_ratio(evaluation: Evaluation) -> float:
    code = evaluation.evaluation_type or ""
    code_salt = sum((idx + 1) * ord(char) for idx, char in enumerate(code))
    seed = (
        (evaluation.project_id * 97)
        + (evaluation.judge_id * 53)
        + (evaluation.id * 29)
        + code_salt
    )
    normalized = ((seed * 9301) + 49297) % 233280 / 233280
    curved = (normalized ** 0.88) * 0.92 + 0.04
    return _clamp(curved, 0.04, 0.96)


def _build_scores_for_total(evaluation: Evaluation, scores: list[EvaluationScore]) -> list[int]:
    mins = [item.criterion.min_score for item in scores]
    maxes = [item.criterion.max_score for item in scores]
    min_total = sum(mins)
    max_total = sum(maxes)
    if max_total <= min_total:
        return mins[:]

    ratio = _stable_ratio(evaluation)
    target_total = min_total + round((max_total - min_total) * ratio)
    values = mins[:]
    remaining = target_total - min_total
    capacities = [maxes[idx] - mins[idx] for idx in range(len(scores))]
    seed = (evaluation.project_id * 23) + (evaluation.judge_id * 17) + (evaluation.id * 5)
    order = sorted(range(len(scores)), key=lambda idx: ((seed + scores[idx].criterion.id * 7 + idx * 13) % 97, idx))

    while remaining > 0:
        progressed = False
        for idx in order:
            if capacities[idx] <= 0:
                continue
            values[idx] += 1
            capacities[idx] -= 1
            remaining -= 1
            progressed = True
            if remaining == 0:
                break
        if not progressed:
            break

    return values


def rebalance(evaluation_type: str | None = None):
    query = Evaluation.query.options(
        joinedload(Evaluation.scores).joinedload(EvaluationScore.criterion),
    ).order_by(Evaluation.id.asc())
    if evaluation_type:
        query = query.filter(Evaluation.evaluation_type == evaluation_type)
    evaluations = query.all()

    updated = 0
    for evaluation in evaluations:
        scores = sorted(
            [item for item in evaluation.scores if item.criterion is not None],
            key=lambda item: (
                item.criterion.section_sort_order,
                item.criterion.sort_order,
                item.criterion.id,
            ),
        )
        if not scores:
            continue

        total_score = 0
        max_score = 0
        first_four = []
        new_values = _build_scores_for_total(evaluation, scores)

        for position, score_row in enumerate(scores):
            criterion = score_row.criterion
            new_value = new_values[position]
            score_row.score = new_value
            total_score += new_value
            max_score += criterion.max_score
            if len(first_four) < 4:
                first_four.append(new_value)

        percentage = round((total_score / max_score) * 100, 2) if max_score else 0.0
        comments, recommendations = _comment_for(percentage)

        evaluation.criteria_1 = first_four[0] if len(first_four) > 0 else None
        evaluation.criteria_2 = first_four[1] if len(first_four) > 1 else None
        evaluation.criteria_3 = first_four[2] if len(first_four) > 2 else None
        evaluation.criteria_4 = first_four[3] if len(first_four) > 3 else None
        evaluation.max_score = max_score
        evaluation.percentage = percentage
        evaluation.comments = comments
        evaluation.recommendations = recommendations
        updated += 1

    db.session.commit()
    scope = evaluation_type or "all"
    print(f"Evaluaciones rebalanceadas ({scope}): {updated}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--only-type", dest="evaluation_type", default=None)
    args = parser.parse_args()
    app = create_app()
    with app.app_context():
        rebalance(args.evaluation_type)
