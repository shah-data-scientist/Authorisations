"""Initial schema: simulations + audit_log tables.

Revision ID: 001
Revises:
Create Date: 2026-05-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "simulations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("system_id", sa.Integer(), nullable=False),
        sa.Column("drift_score", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("risk_label", sa.String(length=20), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "review_status",
            sa.String(length=20),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("reviewed_by", sa.String(length=255), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_simulations_employee_id", "simulations", ["employee_id"])
    op.create_index("ix_simulations_review_status", "simulations", ["review_status"])

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=True),
        sa.Column("system_id", sa.Integer(), nullable=True),
        sa.Column("drift_score", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column(
            "performed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_log_employee_id", "audit_log", ["employee_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_log_employee_id", table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_index("ix_simulations_review_status", table_name="simulations")
    op.drop_index("ix_simulations_employee_id", table_name="simulations")
    op.drop_table("simulations")
