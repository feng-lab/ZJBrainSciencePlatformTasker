"""create task tables

Revision ID: 383fd5a1b634
Revises: 
Create Date: 2023-09-26 11:19:55.686251

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "383fd5a1b634"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "task_template",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("create_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("modified_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", sa.Enum("executable", "python", name="type"), nullable=False),
        sa.Column("executable", sa.JSON(), nullable=False),
        sa.Column("environment", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "task",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("create_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("modified_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("argument", sa.JSON(), nullable=False),
        sa.Column("environment", sa.JSON(), nullable=False),
        sa.Column("retry_times", sa.Integer(), nullable=False),
        sa.Column("template", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(("template",), ["task_template.id"], name="fk_task_task_template_id_template"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "task_run",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("create_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("modified_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("index", sa.Integer(), nullable=False),
        sa.Column(
            "status", sa.Enum("pending", "running", "success", "failed", "canceled", name="status"), nullable=False
        ),
        sa.Column("start_at", sa.DateTime(), nullable=True),
        sa.Column("end_at", sa.DateTime(), nullable=True),
        sa.Column("task", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ("task",), ["task.id"], name="fk_task_run_task_id_task", onupdate="CASCADE", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("task_run")
    op.drop_table("task")
    op.drop_table("task_template")
