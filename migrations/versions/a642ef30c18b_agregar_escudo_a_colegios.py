"""agregar escudo a colegios

Revision ID: a642ef30c18b
Revises: 27d8823019dd
Create Date: 2026-08-03
"""
from alembic import op
import sqlalchemy as sa


revision = "a642ef30c18b"
down_revision = "27d8823019dd"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("institutions", sa.Column("shield_path", sa.String(length=300), nullable=True))


def downgrade():
    op.drop_column("institutions", "shield_path")
