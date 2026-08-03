"""Crea diez colegios provisionales sin duplicar registros existentes."""

from app import create_app
from app.extensions import db
from app.models.institution import Institution


def seed():
    created = []
    for number in range(1, 11):
        code = f"REG-{number:03d}"
        if Institution.query.filter_by(code=code).first():
            continue
        db.session.add(
            Institution(
                code=code,
                name=f"Colegio participante {number:02d}",
                responsible_name="Pendiente de completar",
                responsible_email=f"pendiente{number:02d}@exporegional.local",
                participation_status=Institution.STATUS_INVITED,
                is_active=True,
                uses_institutional_platform=False,
            )
        )
        created.append(code)
    db.session.commit()
    return created


if __name__ == "__main__":
    application = create_app()
    with application.app_context():
        rows = seed()
        print(f"Colegios provisionales creados: {len(rows)}")
