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


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    return _inspector().has_table(table_name)


def _index_names(table_name: str) -> set[str]:
    if not _has_table(table_name):
        return set()
    return {index["name"] for index in _inspector().get_indexes(table_name)}


def upgrade() -> None:
    if not _has_table("sandbox_runs"):
        op.create_table(
            "sandbox_runs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("run_id", sa.String(length=36), nullable=False),
            sa.Column("failure_fingerprint", sa.String(length=255), nullable=True),
            sa.Column("remediation_type", sa.String(length=50), nullable=True),
            sa.Column("changed_files", sa.JSON(), nullable=False),
            sa.Column("blast_radius_files", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("blast_radius_loc", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("verdict", sa.String(length=16), nullable=False),
            sa.Column("gate_results", sa.JSON(), nullable=True),
            sa.Column("confidence", sa.Numeric(3, 2), nullable=True),
            sa.Column("duration_ms", sa.Integer(), nullable=True),
            sa.Column("container_id", sa.String(length=64), nullable=True),
            sa.Column("logs", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("rollback_notes", sa.Text(), nullable=True),
            sa.CheckConstraint("verdict IN ('green', 'yellow', 'red')", name="sandbox_runs_verdict_check"),
            sa.UniqueConstraint("run_id", name="uq_sandbox_runs_run_id"),
        )

    existing_indexes = _index_names("sandbox_runs")
    if "ix_sandbox_runs_run_id" not in existing_indexes:
        op.create_index("ix_sandbox_runs_run_id", "sandbox_runs", ["run_id"])
    if "idx_sandbox_runs_verdict" not in existing_indexes:
        op.create_index("idx_sandbox_runs_verdict", "sandbox_runs", ["verdict"])
    if "idx_sandbox_runs_fingerprint" not in existing_indexes:
        op.create_index(
            "idx_sandbox_runs_fingerprint",
            "sandbox_runs",
            ["failure_fingerprint"],
        )


def downgrade() -> None:
    existing_indexes = _index_names("sandbox_runs")
    if "idx_sandbox_runs_fingerprint" in existing_indexes:
        op.drop_index("idx_sandbox_runs_fingerprint", table_name="sandbox_runs")
    if "idx_sandbox_runs_verdict" in existing_indexes:
        op.drop_index("idx_sandbox_runs_verdict", table_name="sandbox_runs")
    if "ix_sandbox_runs_run_id" in existing_indexes:
        op.drop_index("ix_sandbox_runs_run_id", table_name="sandbox_runs")
    if _has_table("sandbox_runs"):
        op.drop_table("sandbox_runs")

    op.execute("DROP TYPE IF EXISTS sandboxverdict")
