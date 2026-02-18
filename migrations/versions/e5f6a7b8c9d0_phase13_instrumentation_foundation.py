"""Phase 13 instrumentation foundation (preference + verification signals)

Revision ID: e5f6a7b8c9d0
Revises: c4d5e6f7a8b9
Create Date: 2026-02-17 00:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "e5f6a7b8c9d0"
down_revision = "c4d5e6f7a8b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assistant_preference_signals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("action_id", sa.Integer(), sa.ForeignKey("chat_actions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("chat_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("store_id", sa.Integer(), sa.ForeignKey("shopify_stores.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("correlation_id", sa.String(length=96), nullable=True),
        sa.Column("tier", sa.String(length=16), nullable=False, server_default="tier_1"),
        sa.Column("signal_kind", sa.String(length=24), nullable=False, server_default="approval"),
        sa.Column("preference_signal", sa.String(length=32), nullable=False, server_default="approved_all"),
        sa.Column("selected_change_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("override_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("reasoning_trace_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "tier IN ('tier_1', 'tier_2', 'tier_3')",
            name="assistant_preference_signal_tier",
        ),
        sa.CheckConstraint(
            "signal_kind IN ('approval', 'edit', 'thumb')",
            name="assistant_preference_signal_kind",
        ),
        sa.CheckConstraint(
            "preference_signal IN ("
            "'approved_all', 'approved_selection', 'edited', 'thumb_up', 'thumb_down', 'rejected'"
            ")",
            name="assistant_preference_signal_value",
        ),
        sa.CheckConstraint(
            "selected_change_count >= 0",
            name="assistant_preference_signal_selected_count",
        ),
        sa.CheckConstraint(
            "override_count >= 0",
            name="assistant_preference_signal_override_count",
        ),
        sa.CheckConstraint(
            "reasoning_trace_tokens IS NULL OR reasoning_trace_tokens >= 0",
            name="assistant_preference_signal_tokens_nonnegative",
        ),
        sa.CheckConstraint(
            "cost_usd IS NULL OR cost_usd >= 0",
            name="assistant_preference_signal_cost_nonnegative",
        ),
    )
    op.create_index("ix_assistant_preference_signals_action_id", "assistant_preference_signals", ["action_id"])
    op.create_index("ix_assistant_preference_signals_session_id", "assistant_preference_signals", ["session_id"])
    op.create_index("ix_assistant_preference_signals_store_id", "assistant_preference_signals", ["store_id"])
    op.create_index("ix_assistant_preference_signals_user_id", "assistant_preference_signals", ["user_id"])
    op.create_index("ix_assistant_preference_signals_correlation_id", "assistant_preference_signals", ["correlation_id"])
    op.create_index("ix_assistant_preference_signals_tier", "assistant_preference_signals", ["tier"])
    op.create_index(
        "ix_assistant_preference_signal_action_created",
        "assistant_preference_signals",
        ["action_id", "created_at"],
    )
    op.create_index(
        "ix_assistant_preference_signal_corr_created",
        "assistant_preference_signals",
        ["correlation_id", "created_at"],
    )
    op.create_index(
        "ix_assistant_preference_signal_store_tier",
        "assistant_preference_signals",
        ["store_id", "tier"],
    )

    op.create_table(
        "assistant_verification_signals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("action_id", sa.Integer(), sa.ForeignKey("chat_actions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("chat_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("store_id", sa.Integer(), sa.ForeignKey("shopify_stores.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column(
            "verification_event_id",
            sa.Integer(),
            sa.ForeignKey("assistant_verification_events.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("correlation_id", sa.String(length=96), nullable=False),
        sa.Column("tier", sa.String(length=16), nullable=False, server_default="tier_1"),
        sa.Column("verification_status", sa.String(length=16), nullable=False, server_default="deferred"),
        sa.Column("oracle_signal", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("waited_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reasoning_trace_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "tier IN ('tier_1', 'tier_2', 'tier_3')",
            name="assistant_verification_signal_tier",
        ),
        sa.CheckConstraint(
            "verification_status IN ('verified', 'deferred', 'failed')",
            name="assistant_verification_signal_status",
        ),
        sa.CheckConstraint(
            "attempt_count >= 1",
            name="assistant_verification_signal_attempt_count",
        ),
        sa.CheckConstraint(
            "waited_seconds >= 0",
            name="assistant_verification_signal_waited_nonnegative",
        ),
        sa.CheckConstraint(
            "reasoning_trace_tokens IS NULL OR reasoning_trace_tokens >= 0",
            name="assistant_verification_signal_tokens_nonnegative",
        ),
        sa.CheckConstraint(
            "cost_usd IS NULL OR cost_usd >= 0",
            name="assistant_verification_signal_cost_nonnegative",
        ),
    )
    op.create_index("ix_assistant_verification_signals_action_id", "assistant_verification_signals", ["action_id"])
    op.create_index("ix_assistant_verification_signals_session_id", "assistant_verification_signals", ["session_id"])
    op.create_index("ix_assistant_verification_signals_store_id", "assistant_verification_signals", ["store_id"])
    op.create_index("ix_assistant_verification_signals_user_id", "assistant_verification_signals", ["user_id"])
    op.create_index("ix_assistant_verification_signals_verification_event_id", "assistant_verification_signals", ["verification_event_id"])
    op.create_index("ix_assistant_verification_signals_correlation_id", "assistant_verification_signals", ["correlation_id"])
    op.create_index("ix_assistant_verification_signals_tier", "assistant_verification_signals", ["tier"])
    op.create_index(
        "ix_assistant_verification_signal_action_created",
        "assistant_verification_signals",
        ["action_id", "created_at"],
    )
    op.create_index(
        "ix_assistant_verification_signal_corr_created",
        "assistant_verification_signals",
        ["correlation_id", "created_at"],
    )
    op.create_index(
        "ix_assistant_verification_signal_store_tier",
        "assistant_verification_signals",
        ["store_id", "tier"],
    )


def downgrade() -> None:
    op.drop_index("ix_assistant_verification_signal_store_tier", table_name="assistant_verification_signals")
    op.drop_index("ix_assistant_verification_signal_corr_created", table_name="assistant_verification_signals")
    op.drop_index("ix_assistant_verification_signal_action_created", table_name="assistant_verification_signals")
    op.drop_index("ix_assistant_verification_signals_tier", table_name="assistant_verification_signals")
    op.drop_index("ix_assistant_verification_signals_correlation_id", table_name="assistant_verification_signals")
    op.drop_index("ix_assistant_verification_signals_verification_event_id", table_name="assistant_verification_signals")
    op.drop_index("ix_assistant_verification_signals_user_id", table_name="assistant_verification_signals")
    op.drop_index("ix_assistant_verification_signals_store_id", table_name="assistant_verification_signals")
    op.drop_index("ix_assistant_verification_signals_session_id", table_name="assistant_verification_signals")
    op.drop_index("ix_assistant_verification_signals_action_id", table_name="assistant_verification_signals")
    op.drop_table("assistant_verification_signals")

    op.drop_index("ix_assistant_preference_signal_store_tier", table_name="assistant_preference_signals")
    op.drop_index("ix_assistant_preference_signal_corr_created", table_name="assistant_preference_signals")
    op.drop_index("ix_assistant_preference_signal_action_created", table_name="assistant_preference_signals")
    op.drop_index("ix_assistant_preference_signals_tier", table_name="assistant_preference_signals")
    op.drop_index("ix_assistant_preference_signals_correlation_id", table_name="assistant_preference_signals")
    op.drop_index("ix_assistant_preference_signals_user_id", table_name="assistant_preference_signals")
    op.drop_index("ix_assistant_preference_signals_store_id", table_name="assistant_preference_signals")
    op.drop_index("ix_assistant_preference_signals_session_id", table_name="assistant_preference_signals")
    op.drop_index("ix_assistant_preference_signals_action_id", table_name="assistant_preference_signals")
    op.drop_table("assistant_preference_signals")
