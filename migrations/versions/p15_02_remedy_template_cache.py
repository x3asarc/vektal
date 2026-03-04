"""Add remedy_template_cache table for phase 15 session memory loading.

Revision ID: p15_02_remedy_template_cache
Revises: p15_01_sandbox_runs
Create Date: 2026-03-02 15:02:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "p15_02_remedy_template_cache"
down_revision = "p15_01_sandbox_runs"
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
    if not _has_table("remedy_template_cache"):
        op.create_table(
            "remedy_template_cache",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("template_id", sa.String(length=36), nullable=False),
            sa.Column("fingerprint", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("remedy_payload", sa.Text(), nullable=True),
            sa.Column("confidence", sa.Numeric(3, 2), nullable=False),
            sa.Column("application_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("success_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("affected_files_json", sa.JSON(), nullable=True),
            sa.Column("source_commit_sha", sa.String(length=40), nullable=True),
            sa.Column("last_applied_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("cache_refreshed_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("template_id", name="uq_remedy_template_cache_template_id"),
        )

    existing_indexes = _index_names("remedy_template_cache")
    if "ix_remedy_template_cache_template_id" not in existing_indexes:
        op.create_index(
            "ix_remedy_template_cache_template_id",
            "remedy_template_cache",
            ["template_id"],
        )
    if "ix_remedy_template_cache_fingerprint" not in existing_indexes:
        op.create_index(
            "ix_remedy_template_cache_fingerprint",
            "remedy_template_cache",
            ["fingerprint"],
        )
    if "ix_remedy_template_cache_expires_at" not in existing_indexes:
        op.create_index(
            "ix_remedy_template_cache_expires_at",
            "remedy_template_cache",
            ["expires_at"],
        )
    if "idx_remedy_fingerprint_conf" not in existing_indexes:
        op.create_index(
            "idx_remedy_fingerprint_conf",
            "remedy_template_cache",
            ["fingerprint", "confidence"],
        )
    if "idx_remedy_last_applied" not in existing_indexes:
        op.create_index(
            "idx_remedy_last_applied",
            "remedy_template_cache",
            ["last_applied_at"],
        )


def downgrade() -> None:
    existing_indexes = _index_names("remedy_template_cache")
    if "idx_remedy_last_applied" in existing_indexes:
        op.drop_index("idx_remedy_last_applied", table_name="remedy_template_cache")
    if "idx_remedy_fingerprint_conf" in existing_indexes:
        op.drop_index("idx_remedy_fingerprint_conf", table_name="remedy_template_cache")
    if "ix_remedy_template_cache_expires_at" in existing_indexes:
        op.drop_index("ix_remedy_template_cache_expires_at", table_name="remedy_template_cache")
    if "ix_remedy_template_cache_fingerprint" in existing_indexes:
        op.drop_index("ix_remedy_template_cache_fingerprint", table_name="remedy_template_cache")
    if "ix_remedy_template_cache_template_id" in existing_indexes:
        op.drop_index("ix_remedy_template_cache_template_id", table_name="remedy_template_cache")
    if _has_table("remedy_template_cache"):
        op.drop_table("remedy_template_cache")
