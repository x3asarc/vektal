"""Phase 10 chat foundation schema

Revision ID: f0a1b2c3d4e5
Revises: c1d9e8f7a6b5
Create Date: 2026-02-15 18:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f0a1b2c3d4e5"
down_revision = "c1d9e8f7a6b5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("store_id", sa.Integer(), sa.ForeignKey("shopify_stores.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("state", sa.String(length=32), nullable=False, server_default="at_door"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("context_json", sa.JSON(), nullable=True),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("state IN ('at_door', 'in_house')", name="chat_session_state"),
        sa.CheckConstraint("status IN ('active', 'closed')", name="chat_session_status"),
    )
    op.create_index("ix_chat_sessions_user_id", "chat_sessions", ["user_id"])
    op.create_index("ix_chat_sessions_store_id", "chat_sessions", ["store_id"])
    op.create_index("ix_chat_sessions_last_message_at", "chat_sessions", ["last_message_at"])
    op.create_index("ix_chat_session_user_state", "chat_sessions", ["user_id", "state"])
    op.create_index("ix_chat_session_user_status", "chat_sessions", ["user_id", "status"])

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("blocks_json", sa.JSON(), nullable=False),
        sa.Column("source_metadata", sa.JSON(), nullable=True),
        sa.Column("intent_type", sa.String(length=64), nullable=True),
        sa.Column("classification_method", sa.String(length=32), nullable=True),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("role IN ('user', 'assistant', 'system')", name="chat_message_role"),
    )
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])
    op.create_index("ix_chat_messages_user_id", "chat_messages", ["user_id"])
    op.create_index("ix_chat_message_session_role", "chat_messages", ["session_id", "role"])

    op.create_table(
        "chat_actions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("store_id", sa.Integer(), sa.ForeignKey("shopify_stores.id", ondelete="SET NULL"), nullable=True),
        sa.Column("message_id", sa.Integer(), sa.ForeignKey("chat_messages.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="drafted"),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('drafted', 'dry_run_ready', 'awaiting_approval', 'approved', "
            "'applying', 'completed', 'failed', 'conflicted', 'partial', 'cancelled')",
            name="chat_action_status",
        ),
    )
    op.create_index("ix_chat_actions_session_id", "chat_actions", ["session_id"])
    op.create_index("ix_chat_actions_user_id", "chat_actions", ["user_id"])
    op.create_index("ix_chat_actions_store_id", "chat_actions", ["store_id"])
    op.create_index("ix_chat_actions_message_id", "chat_actions", ["message_id"])
    op.create_index("ix_chat_actions_idempotency_key", "chat_actions", ["idempotency_key"], unique=True)
    op.create_index("ix_chat_action_session_status", "chat_actions", ["session_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_chat_action_session_status", table_name="chat_actions")
    op.drop_index("ix_chat_actions_idempotency_key", table_name="chat_actions")
    op.drop_index("ix_chat_actions_message_id", table_name="chat_actions")
    op.drop_index("ix_chat_actions_store_id", table_name="chat_actions")
    op.drop_index("ix_chat_actions_user_id", table_name="chat_actions")
    op.drop_index("ix_chat_actions_session_id", table_name="chat_actions")
    op.drop_table("chat_actions")

    op.drop_index("ix_chat_message_session_role", table_name="chat_messages")
    op.drop_index("ix_chat_messages_user_id", table_name="chat_messages")
    op.drop_index("ix_chat_messages_session_id", table_name="chat_messages")
    op.drop_table("chat_messages")

    op.drop_index("ix_chat_session_user_status", table_name="chat_sessions")
    op.drop_index("ix_chat_session_user_state", table_name="chat_sessions")
    op.drop_index("ix_chat_sessions_last_message_at", table_name="chat_sessions")
    op.drop_index("ix_chat_sessions_store_id", table_name="chat_sessions")
    op.drop_index("ix_chat_sessions_user_id", table_name="chat_sessions")
    op.drop_table("chat_sessions")
