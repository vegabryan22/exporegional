"""Agregar nivel normalizado a integrantes.

Revision ID: b91d2e73a4c1
Revises: a61d8e40c7b2
"""

from alembic import op
import sqlalchemy as sa


revision = "b91d2e73a4c1"
down_revision = "a61d8e40c7b2"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("project_members") as batch_op:
        batch_op.add_column(sa.Column("level_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_project_members_level_id", ["level_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_project_members_level_id_levels",
            "levels",
            ["level_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    # Conserva correctamente el nivel de registros heredados como 11-1, 12-2, etc.
    op.execute(
        sa.text(
            """
            UPDATE project_members pm
            JOIN levels l ON l.code = SUBSTRING_INDEX(pm.section_name, '-', 1)
            SET pm.level_id = l.id
            WHERE pm.level_id IS NULL AND pm.section_name IS NOT NULL
            """
        )
    )


def downgrade():
    with op.batch_alter_table("project_members") as batch_op:
        batch_op.drop_constraint("fk_project_members_level_id_levels", type_="foreignkey")
        batch_op.drop_index("ix_project_members_level_id")
        batch_op.drop_column("level_id")
