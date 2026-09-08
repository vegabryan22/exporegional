"""Derivar coordinación institucional desde la cuenta de jornada.

Revision ID: e83c61f40a27
Revises: d54b73e89210
"""

from alembic import op
import sqlalchemy as sa


revision = "e83c61f40a27"
down_revision = "d54b73e89210"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("institutions")}
    with op.batch_alter_table("institutions") as batch_op:
        if "technical_coordinator_email" in columns:
            batch_op.drop_column("technical_coordinator_email")
        if "technical_coordinator_name" in columns:
            batch_op.drop_column("technical_coordinator_name")


def downgrade():
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("institutions")}
    with op.batch_alter_table("institutions") as batch_op:
        if "technical_coordinator_name" not in columns:
            batch_op.add_column(sa.Column("technical_coordinator_name", sa.String(length=160), nullable=True))
        if "technical_coordinator_email" not in columns:
            batch_op.add_column(sa.Column("technical_coordinator_email", sa.String(length=160), nullable=True))
