"""Warnings only: profile changes never delete assignments or saved evaluations."""
from flask import flash
from app.models.assignment import Assignment


def warn_incompatible_assignments(judge):
    assignments = Assignment.query.filter_by(judge_id=judge.id).all()
    incompatible = [a for a in assignments if
                    (a.can_evaluate_documentation and not judge.can_evaluate_documentation) or
                    (a.can_evaluate_exposition and not judge.can_evaluate_exposition) or
                    (a.can_evaluate_english and not judge.can_evaluate_english)]
    if incompatible:
        flash(f"El juez tiene {len(incompatible)} asignación(es) incompatible(s) con su nuevo perfil. "
              "Revisa y reasigna la cobertura en Asignar proyectos. No se borraron asignaciones ni evaluaciones.", "warning")
