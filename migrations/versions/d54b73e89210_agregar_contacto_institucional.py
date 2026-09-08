"""Agregar contacto propio del centro educativo.

Revision ID: d54b73e89210
Revises: c72e94a01f36
"""

from alembic import op
import sqlalchemy as sa


revision = "d54b73e89210"
down_revision = "c72e94a01f36"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("institutions")}
    with op.batch_alter_table("institutions") as batch_op:
        if "institutional_phone" not in columns:
            batch_op.add_column(sa.Column("institutional_phone", sa.String(length=40), nullable=True))
        if "institutional_email" not in columns:
            batch_op.add_column(sa.Column("institutional_email", sa.String(length=160), nullable=True))


def downgrade():
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("institutions")}
    with op.batch_alter_table("institutions") as batch_op:
        if "institutional_email" in columns:
            batch_op.drop_column("institutional_email")
        if "institutional_phone" in columns:
            batch_op.drop_column("institutional_phone")
