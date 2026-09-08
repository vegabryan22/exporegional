"""Agregar responsables institucionales para formularios ExpoTEC.

Revision ID: c72e94a01f36
Revises: b91d2e73a4c1
"""

from alembic import op
import sqlalchemy as sa


revision = "c72e94a01f36"
down_revision = "b91d2e73a4c1"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("institutions")}
    with op.batch_alter_table("institutions") as batch_op:
        if "director_name" not in columns:
            batch_op.add_column(sa.Column("director_name", sa.String(length=160), nullable=True))
        if "director_email" not in columns:
            batch_op.add_column(sa.Column("director_email", sa.String(length=160), nullable=True))
        if "technical_coordinator_name" not in columns:
            batch_op.add_column(sa.Column("technical_coordinator_name", sa.String(length=160), nullable=True))
        if "technical_coordinator_email" not in columns:
            batch_op.add_column(sa.Column("technical_coordinator_email", sa.String(length=160), nullable=True))


def downgrade():
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("institutions")}
    with op.batch_alter_table("institutions") as batch_op:
        for column_name in (
            "technical_coordinator_email",
            "technical_coordinator_name",
            "director_email",
            "director_name",
        ):
            if column_name in columns:
                batch_op.drop_column(column_name)
