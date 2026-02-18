"""Phase 13 deployment policy and provider route observability

Revision ID: c4d5e6f7a8b9
Revises: b2f4c6d8e0a1
Create Date: 2026-02-16 23:35:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "c4d5e6f7a8b9"
down_revision = "b2f4c6d8e0a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assistant_deployment_policies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scope_kind", sa.String(length=16), nullable=False, server_default="global"),
        sa.Column("store_id", sa.Integer(), sa.ForeignKey("shopify_stores.id", ondelete="CASCADE"), nullable=True),
        sa.Column("policy_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("changed_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("primary_provider", sa.String(length=64), nullable=False, server_default="qwen"),
        sa.Column("primary_model", sa.String(length=128), nullable=False, server_default="qwen-2.5-coder"),
        sa.Column("provider_ladder_json", sa.JSON(), nullable=False),
        sa.Column("budget_guard_percent", sa.Float(), nullable=False, server_default="95.0"),
        sa.Column("rollout_guard_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "scope_kind IN ('global', 'tenant')",
            name="assistant_deployment_policy_scope_kind",
        ),
        sa.CheckConstraint(
            "(scope_kind = 'global' AND store_id IS NULL) OR "
            "(scope_kind = 'tenant' AND store_id IS NOT NULL)",
            name="assistant_deployment_policy_scope_store_match",
        ),
        sa.CheckConstraint(
            "policy_version >= 1",
            name="assistant_deployment_policy_version",
        ),
        sa.UniqueConstraint(
            "scope_kind",
            "store_id",
            "policy_version",
            name="uq_assistant_deployment_policy_scope_version",
        ),
    )
    op.create_index("ix_assistant_deployment_policies_store_id", "assistant_deployment_policies", ["store_id"])
    op.create_index("ix_assistant_deployment_policies_is_active", "assistant_deployment_policies", ["is_active"])
    op.create_index("ix_assistant_deployment_policies_effective_at", "assistant_deployment_policies", ["effective_at"])
    op.create_index("ix_assistant_deployment_policies_changed_by_id", "assistant_deployment_policies", ["changed_by_id"])
    op.create_index(
        "ix_assistant_deployment_policy_scope_active",
        "assistant_deployment_policies",
        ["scope_kind", "store_id", "is_active"],
    )

    op.create_table(
        "assistant_provider_route_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("correlation_id", sa.String(length=96), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("store_id", sa.Integer(), sa.ForeignKey("shopify_stores.id", ondelete="SET NULL"), nullable=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("chat_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action_id", sa.Integer(), sa.ForeignKey("chat_actions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("route_event_id", sa.Integer(), sa.ForeignKey("assistant_route_events.id", ondelete="SET NULL"), nullable=True),
        sa.Column("intent_type", sa.String(length=64), nullable=False),
        sa.Column("route_stage", sa.String(length=32), nullable=False, server_default="primary"),
        sa.Column("route_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("selected_provider", sa.String(length=64), nullable=False),
        sa.Column("selected_model", sa.String(length=128), nullable=False),
        sa.Column("fallback_reason_code", sa.String(length=64), nullable=True, server_default="none"),
        sa.Column("policy_snapshot_hash", sa.String(length=128), nullable=False),
        sa.Column("route_metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "route_stage IN ('primary', 'fallback', 'budget_guard', 'safe_degraded')",
            name="assistant_provider_route_event_stage",
        ),
        sa.CheckConstraint(
            "fallback_reason_code IS NULL OR fallback_reason_code IN "
            "('none', 'provider_unavailable', 'invalid_tool_call', 'budget_guard', "
            "'policy_block', 'latency_guard')",
            name="assistant_provider_route_event_reason",
        ),
    )
    op.create_index("ix_assistant_provider_route_events_correlation_id", "assistant_provider_route_events", ["correlation_id"])
    op.create_index("ix_assistant_provider_route_events_user_id", "assistant_provider_route_events", ["user_id"])
    op.create_index("ix_assistant_provider_route_events_store_id", "assistant_provider_route_events", ["store_id"])
    op.create_index("ix_assistant_provider_route_events_session_id", "assistant_provider_route_events", ["session_id"])
    op.create_index("ix_assistant_provider_route_events_action_id", "assistant_provider_route_events", ["action_id"])
    op.create_index("ix_assistant_provider_route_events_route_event_id", "assistant_provider_route_events", ["route_event_id"])
    op.create_index("ix_assistant_provider_route_events_policy_snapshot_hash", "assistant_provider_route_events", ["policy_snapshot_hash"])
    op.create_index(
        "ix_assistant_provider_route_event_corr_created",
        "assistant_provider_route_events",
        ["correlation_id", "created_at"],
    )
    op.create_index(
        "ix_assistant_provider_route_event_store_created",
        "assistant_provider_route_events",
        ["store_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_assistant_provider_route_event_store_created", table_name="assistant_provider_route_events")
    op.drop_index("ix_assistant_provider_route_event_corr_created", table_name="assistant_provider_route_events")
    op.drop_index("ix_assistant_provider_route_events_policy_snapshot_hash", table_name="assistant_provider_route_events")
    op.drop_index("ix_assistant_provider_route_events_route_event_id", table_name="assistant_provider_route_events")
    op.drop_index("ix_assistant_provider_route_events_action_id", table_name="assistant_provider_route_events")
    op.drop_index("ix_assistant_provider_route_events_session_id", table_name="assistant_provider_route_events")
    op.drop_index("ix_assistant_provider_route_events_store_id", table_name="assistant_provider_route_events")
    op.drop_index("ix_assistant_provider_route_events_user_id", table_name="assistant_provider_route_events")
    op.drop_index("ix_assistant_provider_route_events_correlation_id", table_name="assistant_provider_route_events")
    op.drop_table("assistant_provider_route_events")

    op.drop_index("ix_assistant_deployment_policy_scope_active", table_name="assistant_deployment_policies")
    op.drop_index("ix_assistant_deployment_policies_changed_by_id", table_name="assistant_deployment_policies")
    op.drop_index("ix_assistant_deployment_policies_effective_at", table_name="assistant_deployment_policies")
    op.drop_index("ix_assistant_deployment_policies_is_active", table_name="assistant_deployment_policies")
    op.drop_index("ix_assistant_deployment_policies_store_id", table_name="assistant_deployment_policies")
    op.drop_table("assistant_deployment_policies")

