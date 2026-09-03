"""Agregar jornada a coordinadores y proyectos.

Revision ID: f4a7c921de10
Revises: d18f4c2a91e7
Create Date: 2026-09-03
"""

from alembic import op
import sqlalchemy as sa


revision = "f4a7c921de10"
down_revision = "d18f4c2a91e7"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    judge_columns = {column["name"] for column in inspector.get_columns("judges")}
    judge_indexes = {index["name"] for index in inspector.get_indexes("judges")}
    with op.batch_alter_table("judges") as batch_op:
        if "shift" not in judge_columns:
            batch_op.add_column(sa.Column("shift", sa.String(length=20), nullable=True))
        if "ix_judges_shift" not in judge_indexes:
            batch_op.create_index("ix_judges_shift", ["shift"], unique=False)

    inspector = sa.inspect(op.get_bind())
    project_columns = {column["name"] for column in inspector.get_columns("projects")}
    project_indexes = {index["name"] for index in inspector.get_indexes("projects")}
    with op.batch_alter_table("projects") as batch_op:
        if "shift" not in project_columns:
            batch_op.add_column(sa.Column("shift", sa.String(length=20), nullable=True))
        if "ix_projects_shift" not in project_indexes:
            batch_op.create_index("ix_projects_shift", ["shift"], unique=False)


def downgrade():
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_index("ix_projects_shift")
        batch_op.drop_column("shift")
    with op.batch_alter_table("judges") as batch_op:
        batch_op.drop_index("ix_judges_shift")
        batch_op.drop_column("shift")
