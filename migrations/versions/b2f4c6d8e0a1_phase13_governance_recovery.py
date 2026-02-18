"""Phase 13 governance and recovery contracts

Revision ID: b2f4c6d8e0a1
Revises: a9f3c7d5e1b2
Create Date: 2026-02-16 22:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "b2f4c6d8e0a1"
down_revision = "a9f3c7d5e1b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assistant_verification_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("action_id", sa.Integer(), sa.ForeignKey("chat_actions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("batch_id", sa.Integer(), sa.ForeignKey("resolution_batches.id", ondelete="SET NULL"), nullable=True),
        sa.Column("store_id", sa.Integer(), sa.ForeignKey("shopify_stores.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("correlation_id", sa.String(length=96), nullable=True),
        sa.Column("oracle_name", sa.String(length=64), nullable=False, server_default="post_apply_finality"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="deferred"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("poll_schedule_json", sa.JSON(), nullable=False),
        sa.Column("waited_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status_message", sa.String(length=255), nullable=True),
        sa.Column("oracle_result_json", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("deferred_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('verified', 'deferred', 'failed')",
            name="assistant_verification_event_status",
        ),
        sa.CheckConstraint(
            "attempt_count >= 1",
            name="assistant_verification_event_attempt_count",
        ),
        sa.CheckConstraint(
            "(status = 'verified' AND verified_at IS NOT NULL) OR (status != 'verified')",
            name="assistant_verification_event_verified_at_required",
        ),
    )
    op.create_index("ix_assistant_verification_events_action_id", "assistant_verification_events", ["action_id"])
    op.create_index("ix_assistant_verification_events_batch_id", "assistant_verification_events", ["batch_id"])
    op.create_index("ix_assistant_verification_events_store_id", "assistant_verification_events", ["store_id"])
    op.create_index("ix_assistant_verification_events_user_id", "assistant_verification_events", ["user_id"])
    op.create_index("ix_assistant_verification_events_status", "assistant_verification_events", ["status"])
    op.create_index("ix_assistant_verification_events_correlation_id", "assistant_verification_events", ["correlation_id"])
    op.create_index("ix_assistant_verification_events_deferred_until", "assistant_verification_events", ["deferred_until"])
    op.create_index(
        "ix_assistant_verification_event_store_status",
        "assistant_verification_events",
        ["store_id", "status"],
    )
    op.create_index(
        "ix_assistant_verification_event_action_created",
        "assistant_verification_events",
        ["action_id", "created_at"],
    )

    op.create_table(
        "assistant_kill_switches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scope_kind", sa.String(length=16), nullable=False, server_default="tenant"),
        sa.Column("store_id", sa.Integer(), sa.ForeignKey("shopify_stores.id", ondelete="CASCADE"), nullable=True),
        sa.Column("mode", sa.String(length=32), nullable=False, server_default="safe_degraded"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("changed_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "scope_kind IN ('global', 'tenant')",
            name="assistant_kill_switch_scope_kind",
        ),
        sa.CheckConstraint(
            "mode IN ('safe_degraded', 'blocked')",
            name="assistant_kill_switch_mode",
        ),
        sa.CheckConstraint(
            "(scope_kind = 'global' AND store_id IS NULL) OR "
            "(scope_kind = 'tenant' AND store_id IS NOT NULL)",
            name="assistant_kill_switch_scope_store_match",
        ),
    )
    op.create_index("ix_assistant_kill_switches_store_id", "assistant_kill_switches", ["store_id"])
    op.create_index("ix_assistant_kill_switches_is_enabled", "assistant_kill_switches", ["is_enabled"])
    op.create_index("ix_assistant_kill_switches_changed_by_id", "assistant_kill_switches", ["changed_by_id"])
    op.create_index("ix_assistant_kill_switches_effective_at", "assistant_kill_switches", ["effective_at"])
    op.create_index("ix_assistant_kill_switches_expires_at", "assistant_kill_switches", ["expires_at"])
    op.create_index(
        "ix_assistant_kill_switch_scope_enabled",
        "assistant_kill_switches",
        ["scope_kind", "is_enabled", "effective_at"],
    )
    op.create_index(
        "ix_assistant_kill_switch_store_enabled",
        "assistant_kill_switches",
        ["store_id", "is_enabled"],
    )

    op.create_table(
        "assistant_field_policies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("store_id", sa.Integer(), sa.ForeignKey("shopify_stores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("policy_name", sa.String(length=96), nullable=False, server_default="default"),
        sa.Column("policy_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("immutable_fields_json", sa.JSON(), nullable=False),
        sa.Column("hitl_thresholds_json", sa.JSON(), nullable=False),
        sa.Column("dr_objectives_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("changed_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("policy_version >= 1", name="assistant_field_policy_version"),
        sa.UniqueConstraint(
            "store_id",
            "policy_version",
            name="uq_assistant_field_policy_store_version",
        ),
    )
    op.create_index("ix_assistant_field_policies_store_id", "assistant_field_policies", ["store_id"])
    op.create_index("ix_assistant_field_policies_is_active", "assistant_field_policies", ["is_active"])
    op.create_index("ix_assistant_field_policies_effective_at", "assistant_field_policies", ["effective_at"])
    op.create_index("ix_assistant_field_policies_changed_by_id", "assistant_field_policies", ["changed_by_id"])
    op.create_index(
        "ix_assistant_field_policy_store_active",
        "assistant_field_policies",
        ["store_id", "is_active", "effective_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_assistant_field_policy_store_active", table_name="assistant_field_policies")
    op.drop_index("ix_assistant_field_policies_changed_by_id", table_name="assistant_field_policies")
    op.drop_index("ix_assistant_field_policies_effective_at", table_name="assistant_field_policies")
    op.drop_index("ix_assistant_field_policies_is_active", table_name="assistant_field_policies")
    op.drop_index("ix_assistant_field_policies_store_id", table_name="assistant_field_policies")
    op.drop_table("assistant_field_policies")

    op.drop_index("ix_assistant_kill_switch_store_enabled", table_name="assistant_kill_switches")
    op.drop_index("ix_assistant_kill_switch_scope_enabled", table_name="assistant_kill_switches")
    op.drop_index("ix_assistant_kill_switches_expires_at", table_name="assistant_kill_switches")
    op.drop_index("ix_assistant_kill_switches_effective_at", table_name="assistant_kill_switches")
    op.drop_index("ix_assistant_kill_switches_changed_by_id", table_name="assistant_kill_switches")
    op.drop_index("ix_assistant_kill_switches_is_enabled", table_name="assistant_kill_switches")
    op.drop_index("ix_assistant_kill_switches_store_id", table_name="assistant_kill_switches")
    op.drop_table("assistant_kill_switches")

    op.drop_index("ix_assistant_verification_event_action_created", table_name="assistant_verification_events")
    op.drop_index("ix_assistant_verification_event_store_status", table_name="assistant_verification_events")
    op.drop_index("ix_assistant_verification_events_deferred_until", table_name="assistant_verification_events")
    op.drop_index("ix_assistant_verification_events_correlation_id", table_name="assistant_verification_events")
    op.drop_index("ix_assistant_verification_events_status", table_name="assistant_verification_events")
    op.drop_index("ix_assistant_verification_events_user_id", table_name="assistant_verification_events")
    op.drop_index("ix_assistant_verification_events_store_id", table_name="assistant_verification_events")
    op.drop_index("ix_assistant_verification_events_batch_id", table_name="assistant_verification_events")
    op.drop_index("ix_assistant_verification_events_action_id", table_name="assistant_verification_events")
    op.drop_table("assistant_verification_events")

