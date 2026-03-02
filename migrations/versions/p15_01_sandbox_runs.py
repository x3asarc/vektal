"""Add sandbox_runs table for phase 15 verification metadata.

Revision ID: p15_01_sandbox_runs
Revises: g14_2_03_schema_json
Create Date: 2026-03-02 15:01:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "p15_01_sandbox_runs"
down_revision = "g14_2_03_schema_json"
branch_labels = None
depends_on = None


def upgrade() -> None:
    sandbox_verdict = sa.Enum("green", "yellow", "red", name="sandboxverdict")
    sandbox_verdict.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "sandbox_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("failure_fingerprint", sa.String(length=255), nullable=True),
        sa.Column("remediation_type", sa.String(length=50), nullable=True),
        sa.Column("changed_files", sa.JSON(), nullable=False),
        sa.Column("blast_radius_files", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("blast_radius_loc", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("verdict", sandbox_verdict, nullable=False),
        sa.Column("gate_results", sa.JSON(), nullable=True),
        sa.Column("confidence", sa.Numeric(3, 2), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("container_id", sa.String(length=64), nullable=True),
        sa.Column("logs", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rollback_notes", sa.Text(), nullable=True),
        sa.UniqueConstraint("run_id", name="uq_sandbox_runs_run_id"),
    )

    op.create_index("ix_sandbox_runs_run_id", "sandbox_runs", ["run_id"])
    op.create_index("idx_sandbox_runs_verdict", "sandbox_runs", ["verdict"])
    op.create_index(
        "idx_sandbox_runs_fingerprint",
        "sandbox_runs",
        ["failure_fingerprint"],
    )


def downgrade() -> None:
    op.drop_index("idx_sandbox_runs_fingerprint", table_name="sandbox_runs")
    op.drop_index("idx_sandbox_runs_verdict", table_name="sandbox_runs")
    op.drop_index("ix_sandbox_runs_run_id", table_name="sandbox_runs")
    op.drop_table("sandbox_runs")

    sandbox_verdict = sa.Enum("green", "yellow", "red", name="sandboxverdict")
    sandbox_verdict.drop(op.get_bind(), checkfirst=True)
