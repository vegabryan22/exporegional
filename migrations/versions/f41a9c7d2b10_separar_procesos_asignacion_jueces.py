"""Separar procesos de asignacion de jueces.

Revision ID: f41a9c7d2b10
Revises: e83c61f40a27
"""

from alembic import op
import sqlalchemy as sa


revision = "f41a9c7d2b10"
down_revision = "e83c61f40a27"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    assignment_columns = {column["name"] for column in inspector.get_columns("assignments")}
    if "can_evaluate_english" not in assignment_columns:
        with op.batch_alter_table("assignments") as batch_op:
            batch_op.add_column(sa.Column("can_evaluate_english", sa.Boolean(), nullable=False, server_default=sa.false()))
        op.execute(
            "UPDATE assignments SET can_evaluate_english = 1 "
            "WHERE can_evaluate_exposition = 1 AND judge_id IN "
            "(SELECT id FROM judges WHERE can_evaluate_english = 1)"
        )

    tables = set(inspector.get_table_names())
    if "assignment_processes" not in tables:
        op.create_table(
            "assignment_processes",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("process_type", sa.String(length=20), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
            sa.Column("deadline", sa.DateTime(), nullable=True),
            sa.Column("created_by_id", sa.Integer(), nullable=True),
            sa.Column("approved_by_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("approved_at", sa.DateTime(), nullable=True),
            sa.Column("sent_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["approved_by_id"], ["judges.id"]),
            sa.ForeignKeyConstraint(["created_by_id"], ["judges.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_assignment_processes_process_type", "assignment_processes", ["process_type"])
        op.create_index("ix_assignment_processes_status", "assignment_processes", ["status"])

    inspector = sa.inspect(op.get_bind())
    if "assignment_process_items" not in set(inspector.get_table_names()):
        op.create_table(
            "assignment_process_items",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("process_id", sa.Integer(), nullable=False),
            sa.Column("judge_id", sa.Integer(), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=False),
            sa.Column("notification_sent_at", sa.DateTime(), nullable=True),
            sa.Column("notification_error", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["judge_id"], ["judges.id"]),
            sa.ForeignKeyConstraint(["process_id"], ["assignment_processes.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("process_id", "judge_id", "project_id", name="uq_assignment_process_item"),
        )


def downgrade():
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "assignment_process_items" in tables:
        op.drop_table("assignment_process_items")
    if "assignment_processes" in tables:
        op.drop_index("ix_assignment_processes_status", table_name="assignment_processes")
        op.drop_index("ix_assignment_processes_process_type", table_name="assignment_processes")
        op.drop_table("assignment_processes")
    assignment_columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("assignments")}
    if "can_evaluate_english" in assignment_columns:
        with op.batch_alter_table("assignments") as batch_op:
            batch_op.drop_column("can_evaluate_english")
