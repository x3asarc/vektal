"""Phase 12 tier routing, profile, memory, and delegation foundations

Revision ID: d4e5f6a7b8c9
Revises: f1a2b3c4d5e6
Create Date: 2026-02-15 23:45:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "d4e5f6a7b8c9"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assistant_tool_registry",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tool_id", sa.String(length=96), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("risk_class", sa.String(length=16), nullable=False, server_default="low"),
        sa.Column("mutates_data", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("requires_integration", sa.String(length=64), nullable=True),
        sa.Column("allowed_tiers", sa.JSON(), nullable=False),
        sa.Column("required_role", sa.String(length=64), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "risk_class IN ('low', 'medium', 'high', 'critical')",
            name="assistant_tool_registry_risk_class",
        ),
        sa.UniqueConstraint("tool_id", name="uq_assistant_tool_registry_tool_id"),
    )
    op.create_index("ix_assistant_tool_registry_tool_id", "assistant_tool_registry", ["tool_id"])
    op.create_index("ix_assistant_tool_registry_enabled", "assistant_tool_registry", ["enabled"])
    op.create_index("ix_assistant_tool_registry_requires_integration", "assistant_tool_registry", ["requires_integration"])

    op.create_table(
        "assistant_tenant_tool_policies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("store_id", sa.Integer(), sa.ForeignKey("shopify_stores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tool_id", sa.String(length=96), nullable=False),
        sa.Column("policy_action", sa.String(length=16), nullable=False, server_default="deny"),
        sa.Column("role_scope", sa.String(length=64), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "policy_action IN ('allow', 'deny')",
            name="assistant_tenant_tool_policy_action",
        ),
        sa.UniqueConstraint(
            "store_id",
            "tool_id",
            "role_scope",
            name="uq_assistant_tenant_tool_policy_scope",
        ),
    )
    op.create_index("ix_assistant_tenant_tool_policies_store_id", "assistant_tenant_tool_policies", ["store_id"])
    op.create_index("ix_assistant_tenant_tool_policies_tool_id", "assistant_tenant_tool_policies", ["tool_id"])
    op.create_index("ix_assistant_tenant_tool_policies_created_by_user_id", "assistant_tenant_tool_policies", ["created_by_user_id"])
    op.create_index("ix_assistant_tenant_policy_store_tool", "assistant_tenant_tool_policies", ["store_id", "tool_id"])

    op.create_table(
        "assistant_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("store_id", sa.Integer(), sa.ForeignKey("shopify_stores.id", ondelete="CASCADE"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("profile_scope", sa.String(length=16), nullable=False, server_default="user"),
        sa.Column("name", sa.String(length=128), nullable=True),
        sa.Column("enabled_skill_set", sa.JSON(), nullable=False),
        sa.Column("settings_json", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("profile_scope IN ('user', 'team')", name="assistant_profile_scope"),
        sa.CheckConstraint(
            "user_id IS NOT NULL OR store_id IS NOT NULL",
            name="assistant_profile_target_present",
        ),
    )
    op.create_index("ix_assistant_profiles_store_id", "assistant_profiles", ["store_id"])
    op.create_index("ix_assistant_profiles_user_id", "assistant_profiles", ["user_id"])
    op.create_index("ix_assistant_profile_user_scope", "assistant_profiles", ["user_id", "profile_scope", "is_active"])
    op.create_index("ix_assistant_profile_store_scope", "assistant_profiles", ["store_id", "profile_scope", "is_active"])

    op.create_table(
        "assistant_memory_facts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("store_id", sa.Integer(), sa.ForeignKey("shopify_stores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("fact_key", sa.String(length=128), nullable=False),
        sa.Column("fact_value_text", sa.Text(), nullable=False),
        sa.Column("fact_value_json", sa.JSON(), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False, server_default="chat"),
        sa.Column("trust_score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("provenance_json", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "trust_score >= 0.0 AND trust_score <= 1.0",
            name="assistant_memory_fact_trust_score",
        ),
    )
    op.create_index("ix_assistant_memory_facts_store_id", "assistant_memory_facts", ["store_id"])
    op.create_index("ix_assistant_memory_facts_user_id", "assistant_memory_facts", ["user_id"])
    op.create_index("ix_assistant_memory_facts_fact_key", "assistant_memory_facts", ["fact_key"])
    op.create_index("ix_assistant_memory_facts_expires_at", "assistant_memory_facts", ["expires_at"])
    op.create_index("ix_assistant_memory_fact_store_active", "assistant_memory_facts", ["store_id", "is_active"])
    op.create_index("ix_assistant_memory_fact_user_key", "assistant_memory_facts", ["user_id", "fact_key"])

    op.create_table(
        "assistant_memory_embeddings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("memory_fact_id", sa.Integer(), sa.ForeignKey("assistant_memory_facts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("embedding_json", sa.JSON(), nullable=False),
        sa.Column("embedding_model", sa.String(length=96), nullable=False, server_default="placeholder"),
        sa.Column("vector_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "memory_fact_id",
            "embedding_model",
            "vector_version",
            name="uq_assistant_memory_embedding_version",
        ),
    )
    op.create_index("ix_assistant_memory_embeddings_memory_fact_id", "assistant_memory_embeddings", ["memory_fact_id"])
    op.create_index("ix_assistant_memory_embeddings_store_id", "assistant_memory_embeddings", ["store_id"])
    op.create_index("ix_assistant_memory_embeddings_user_id", "assistant_memory_embeddings", ["user_id"])
    op.create_index(
        "ix_assistant_memory_embedding_store_model",
        "assistant_memory_embeddings",
        ["store_id", "embedding_model"],
    )

    op.create_table(
        "assistant_route_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("store_id", sa.Integer(), sa.ForeignKey("shopify_stores.id", ondelete="SET NULL"), nullable=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("chat_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("route_decision", sa.String(length=16), nullable=False),
        sa.Column("intent_type", sa.String(length=64), nullable=False),
        sa.Column("classifier_method", sa.String(length=32), nullable=False, server_default="heuristic"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("approval_mode", sa.String(length=64), nullable=False, server_default="none"),
        sa.Column("fallback_stage", sa.String(length=64), nullable=True),
        sa.Column("reasons_json", sa.JSON(), nullable=False),
        sa.Column("effective_toolset_json", sa.JSON(), nullable=False),
        sa.Column("policy_snapshot_hash", sa.String(length=128), nullable=False),
        sa.Column("effective_toolset_hash", sa.String(length=128), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "route_decision IN ('tier_1', 'tier_2', 'tier_3', 'blocked')",
            name="assistant_route_event_route_decision",
        ),
    )
    op.create_index("ix_assistant_route_events_user_id", "assistant_route_events", ["user_id"])
    op.create_index("ix_assistant_route_events_store_id", "assistant_route_events", ["store_id"])
    op.create_index("ix_assistant_route_events_session_id", "assistant_route_events", ["session_id"])
    op.create_index("ix_assistant_route_events_policy_snapshot_hash", "assistant_route_events", ["policy_snapshot_hash"])
    op.create_index("ix_assistant_route_events_effective_toolset_hash", "assistant_route_events", ["effective_toolset_hash"])
    op.create_index("ix_assistant_route_event_store_created", "assistant_route_events", ["store_id", "created_at"])
    op.create_index("ix_assistant_route_event_user_created", "assistant_route_events", ["user_id", "created_at"])

    op.create_table(
        "assistant_delegation_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("chat_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action_id", sa.Integer(), sa.ForeignKey("chat_actions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("store_id", sa.Integer(), sa.ForeignKey("shopify_stores.id", ondelete="SET NULL"), nullable=True),
        sa.Column("parent_request_id", sa.String(length=64), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("depth", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("fan_out", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="spawned"),
        sa.Column("worker_tool_scope_json", sa.JSON(), nullable=False),
        sa.Column("budget_json", sa.JSON(), nullable=True),
        sa.Column("fallback_stage", sa.String(length=64), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('spawned', 'running', 'completed', 'failed', 'blocked')",
            name="assistant_delegation_event_status",
        ),
        sa.UniqueConstraint("request_id", name="uq_assistant_delegation_events_request_id"),
    )
    op.create_index("ix_assistant_delegation_events_session_id", "assistant_delegation_events", ["session_id"])
    op.create_index("ix_assistant_delegation_events_action_id", "assistant_delegation_events", ["action_id"])
    op.create_index("ix_assistant_delegation_events_user_id", "assistant_delegation_events", ["user_id"])
    op.create_index("ix_assistant_delegation_events_store_id", "assistant_delegation_events", ["store_id"])
    op.create_index("ix_assistant_delegation_events_request_id", "assistant_delegation_events", ["request_id"])
    op.create_index("ix_assistant_delegation_parent", "assistant_delegation_events", ["parent_request_id"])
    op.create_index("ix_assistant_delegation_action_created", "assistant_delegation_events", ["action_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_assistant_delegation_action_created", table_name="assistant_delegation_events")
    op.drop_index("ix_assistant_delegation_parent", table_name="assistant_delegation_events")
    op.drop_index("ix_assistant_delegation_events_request_id", table_name="assistant_delegation_events")
    op.drop_index("ix_assistant_delegation_events_store_id", table_name="assistant_delegation_events")
    op.drop_index("ix_assistant_delegation_events_user_id", table_name="assistant_delegation_events")
    op.drop_index("ix_assistant_delegation_events_action_id", table_name="assistant_delegation_events")
    op.drop_index("ix_assistant_delegation_events_session_id", table_name="assistant_delegation_events")
    op.drop_table("assistant_delegation_events")

    op.drop_index("ix_assistant_route_event_user_created", table_name="assistant_route_events")
    op.drop_index("ix_assistant_route_event_store_created", table_name="assistant_route_events")
    op.drop_index("ix_assistant_route_events_effective_toolset_hash", table_name="assistant_route_events")
    op.drop_index("ix_assistant_route_events_policy_snapshot_hash", table_name="assistant_route_events")
    op.drop_index("ix_assistant_route_events_session_id", table_name="assistant_route_events")
    op.drop_index("ix_assistant_route_events_store_id", table_name="assistant_route_events")
    op.drop_index("ix_assistant_route_events_user_id", table_name="assistant_route_events")
    op.drop_table("assistant_route_events")

    op.drop_index("ix_assistant_memory_embedding_store_model", table_name="assistant_memory_embeddings")
    op.drop_index("ix_assistant_memory_embeddings_user_id", table_name="assistant_memory_embeddings")
    op.drop_index("ix_assistant_memory_embeddings_store_id", table_name="assistant_memory_embeddings")
    op.drop_index("ix_assistant_memory_embeddings_memory_fact_id", table_name="assistant_memory_embeddings")
    op.drop_table("assistant_memory_embeddings")

    op.drop_index("ix_assistant_memory_fact_user_key", table_name="assistant_memory_facts")
    op.drop_index("ix_assistant_memory_fact_store_active", table_name="assistant_memory_facts")
    op.drop_index("ix_assistant_memory_facts_expires_at", table_name="assistant_memory_facts")
    op.drop_index("ix_assistant_memory_facts_fact_key", table_name="assistant_memory_facts")
    op.drop_index("ix_assistant_memory_facts_user_id", table_name="assistant_memory_facts")
    op.drop_index("ix_assistant_memory_facts_store_id", table_name="assistant_memory_facts")
    op.drop_table("assistant_memory_facts")

    op.drop_index("ix_assistant_profile_store_scope", table_name="assistant_profiles")
    op.drop_index("ix_assistant_profile_user_scope", table_name="assistant_profiles")
    op.drop_index("ix_assistant_profiles_user_id", table_name="assistant_profiles")
    op.drop_index("ix_assistant_profiles_store_id", table_name="assistant_profiles")
    op.drop_table("assistant_profiles")

    op.drop_index("ix_assistant_tenant_policy_store_tool", table_name="assistant_tenant_tool_policies")
    op.drop_index("ix_assistant_tenant_tool_policies_created_by_user_id", table_name="assistant_tenant_tool_policies")
    op.drop_index("ix_assistant_tenant_tool_policies_tool_id", table_name="assistant_tenant_tool_policies")
    op.drop_index("ix_assistant_tenant_tool_policies_store_id", table_name="assistant_tenant_tool_policies")
    op.drop_table("assistant_tenant_tool_policies")

    op.drop_index("ix_assistant_tool_registry_requires_integration", table_name="assistant_tool_registry")
    op.drop_index("ix_assistant_tool_registry_enabled", table_name="assistant_tool_registry")
    op.drop_index("ix_assistant_tool_registry_tool_id", table_name="assistant_tool_registry")
    op.drop_table("assistant_tool_registry")

