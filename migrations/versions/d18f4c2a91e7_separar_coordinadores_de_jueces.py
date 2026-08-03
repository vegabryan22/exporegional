"""Separar coordinadores de colegio de jueces regionales.

Revision ID: d18f4c2a91e7
Revises: a642ef30c18b
Create Date: 2026-08-03
"""

from alembic import op


revision = "d18f4c2a91e7"
down_revision = "a642ef30c18b"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "UPDATE judges SET role = 'school_coordinator', is_admin = 0, department = NULL "
        "WHERE institution_id IS NOT NULL AND role = 'judge'"
    )


def downgrade():
    # El rol anterior no puede inferirse con seguridad.
    pass
