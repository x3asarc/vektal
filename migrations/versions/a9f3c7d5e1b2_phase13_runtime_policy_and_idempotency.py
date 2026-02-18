"""Phase 13 runtime policy and idempotency ledger

Revision ID: a9f3c7d5e1b2
Revises: d4e5f6a7b8c9
Create Date: 2026-02-16 20:35:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "a9f3c7d5e1b2"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assistant_runtime_policies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scope_kind", sa.String(length=32), nullable=False, server_default="global"),
        sa.Column("provider_name", sa.String(length=64), nullable=True),
        sa.Column("skill_name", sa.String(length=96), nullable=True),
        sa.Column("policy_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("changed_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("breaker_state", sa.String(length=16), nullable=False, server_default="closed"),
        sa.Column("breaker_error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("breaker_request_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("breaker_consecutive_successes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("breaker_last_failure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("breaker_last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("breaker_opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("breaker_error_rate_threshold", sa.Float(), nullable=False, server_default="0.25"),
        sa.Column("breaker_latency_p95_tier12_seconds", sa.Float(), nullable=False, server_default="15.0"),
        sa.Column("breaker_latency_p95_tier3_seconds", sa.Float(), nullable=False, server_default="45.0"),
        sa.Column("breaker_window_seconds", sa.Integer(), nullable=False, server_default="300"),
        sa.Column("breaker_min_sample_size", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("breaker_open_cooldown_seconds", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("breaker_half_open_successes", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("retry_policy_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "scope_kind IN ('global', 'provider', 'skill', 'provider_skill')",
            name="assistant_runtime_policy_scope_kind",
        ),
        sa.CheckConstraint(
            "breaker_state IN ('closed', 'open', 'half_open')",
            name="assistant_runtime_policy_breaker_state",
        ),
        sa.CheckConstraint(
            "breaker_error_rate_threshold > 0 AND breaker_error_rate_threshold <= 1",
            name="assistant_runtime_policy_error_rate_threshold",
        ),
        sa.CheckConstraint(
            "breaker_min_sample_size >= 1",
            name="assistant_runtime_policy_min_sample_size",
        ),
        sa.CheckConstraint(
            "breaker_open_cooldown_seconds >= 1",
            name="assistant_runtime_policy_open_cooldown",
        ),
        sa.UniqueConstraint(
            "scope_kind",
            "provider_name",
            "skill_name",
            "policy_version",
            name="uq_assistant_runtime_policy_scope_version",
        ),
    )
    op.create_index("ix_assistant_runtime_policies_provider_name", "assistant_runtime_policies", ["provider_name"])
    op.create_index("ix_assistant_runtime_policies_skill_name", "assistant_runtime_policies", ["skill_name"])
    op.create_index("ix_assistant_runtime_policies_changed_by_id", "assistant_runtime_policies", ["changed_by_id"])
    op.create_index("ix_assistant_runtime_policies_effective_at", "assistant_runtime_policies", ["effective_at"])
    op.create_index("ix_assistant_runtime_policy_active_effective", "assistant_runtime_policies", ["is_active", "effective_at"])
    op.create_index(
        "ix_assistant_runtime_policy_scope",
        "assistant_runtime_policies",
        ["scope_kind", "provider_name", "skill_name"],
    )

    op.create_table(
        "assistant_execution_ledger",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("store_id", sa.Integer(), sa.ForeignKey("shopify_stores.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action_type", sa.String(length=96), nullable=False),
        sa.Column("resource_id", sa.String(length=128), nullable=True),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("correlation_id", sa.String(length=96), nullable=True),
        sa.Column("policy_snapshot_hash", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="PROCESSING"),
        sa.Column("status_url", sa.String(length=255), nullable=True),
        sa.Column("response_json", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("last_error_class", sa.String(length=64), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('PROCESSING', 'SUCCESS', 'FAILED', 'EXPIRED')",
            name="assistant_execution_ledger_status",
        ),
        sa.CheckConstraint(
            "attempt_count >= 1",
            name="assistant_execution_ledger_attempt_count",
        ),
        sa.UniqueConstraint("idempotency_key", name="uq_assistant_execution_ledger_idempotency_key"),
    )
    op.create_index("ix_assistant_execution_ledger_idempotency_key", "assistant_execution_ledger", ["idempotency_key"])
    op.create_index("ix_assistant_execution_ledger_store_id", "assistant_execution_ledger", ["store_id"])
    op.create_index("ix_assistant_execution_ledger_user_id", "assistant_execution_ledger", ["user_id"])
    op.create_index("ix_assistant_execution_ledger_action_type", "assistant_execution_ledger", ["action_type"])
    op.create_index("ix_assistant_execution_ledger_resource_id", "assistant_execution_ledger", ["resource_id"])
    op.create_index("ix_assistant_execution_ledger_status", "assistant_execution_ledger", ["status"])
    op.create_index("ix_assistant_execution_ledger_expires_at", "assistant_execution_ledger", ["expires_at"])
    op.create_index("ix_assistant_execution_ledger_correlation_id", "assistant_execution_ledger", ["correlation_id"])
    op.create_index(
        "ix_assistant_execution_ledger_store_status",
        "assistant_execution_ledger",
        ["store_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_assistant_execution_ledger_store_status", table_name="assistant_execution_ledger")
    op.drop_index("ix_assistant_execution_ledger_correlation_id", table_name="assistant_execution_ledger")
    op.drop_index("ix_assistant_execution_ledger_expires_at", table_name="assistant_execution_ledger")
    op.drop_index("ix_assistant_execution_ledger_status", table_name="assistant_execution_ledger")
    op.drop_index("ix_assistant_execution_ledger_resource_id", table_name="assistant_execution_ledger")
    op.drop_index("ix_assistant_execution_ledger_action_type", table_name="assistant_execution_ledger")
    op.drop_index("ix_assistant_execution_ledger_user_id", table_name="assistant_execution_ledger")
    op.drop_index("ix_assistant_execution_ledger_store_id", table_name="assistant_execution_ledger")
    op.drop_index("ix_assistant_execution_ledger_idempotency_key", table_name="assistant_execution_ledger")
    op.drop_table("assistant_execution_ledger")

    op.drop_index("ix_assistant_runtime_policy_scope", table_name="assistant_runtime_policies")
    op.drop_index("ix_assistant_runtime_policy_active_effective", table_name="assistant_runtime_policies")
    op.drop_index("ix_assistant_runtime_policies_effective_at", table_name="assistant_runtime_policies")
    op.drop_index("ix_assistant_runtime_policies_changed_by_id", table_name="assistant_runtime_policies")
    op.drop_index("ix_assistant_runtime_policies_skill_name", table_name="assistant_runtime_policies")
    op.drop_index("ix_assistant_runtime_policies_provider_name", table_name="assistant_runtime_policies")
    op.drop_table("assistant_runtime_policies")

