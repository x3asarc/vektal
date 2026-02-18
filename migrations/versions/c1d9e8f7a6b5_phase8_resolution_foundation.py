"""Phase 8 resolution foundation schema

Revision ID: c1d9e8f7a6b5
Revises: b7d5c4a9e8f1
Create Date: 2026-02-12 23:59:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c1d9e8f7a6b5"
down_revision = "b7d5c4a9e8f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resolution_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("store_id", sa.Integer(), sa.ForeignKey("shopify_stores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="draft"),
        sa.Column("apply_mode", sa.String(length=32), nullable=False, server_default="immediate"),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("critical_error_threshold", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("lock_owner_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("lock_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lock_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('draft', 'ready_for_review', 'approved', 'scheduled', 'applying', "
            "'applied', 'applied_with_conflicts', 'failed', 'cancelled')",
            name="resolution_batch_status",
        ),
        sa.CheckConstraint("apply_mode IN ('immediate', 'scheduled')", name="resolution_batch_apply_mode"),
    )
    op.create_index("ix_resolution_batches_user_id", "resolution_batches", ["user_id"])
    op.create_index("ix_resolution_batches_store_id", "resolution_batches", ["store_id"])
    op.create_index("ix_resolution_batches_scheduled_for", "resolution_batches", ["scheduled_for"])
    op.create_index("ix_resolution_batches_lock_expires_at", "resolution_batches", ["lock_expires_at"])
    op.create_index("ix_resolution_batch_user_status", "resolution_batches", ["user_id", "status"])
    op.create_index("ix_resolution_batch_store_status", "resolution_batches", ["store_id", "status"])

    op.create_table(
        "resolution_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("supplier_code", sa.String(length=64), nullable=False, server_default="*"),
        sa.Column("field_group", sa.String(length=32), nullable=False),
        sa.Column("rule_type", sa.String(length=32), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False, server_default="require_approval"),
        sa.Column("consented", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("field_group IN ('images', 'text', 'pricing', 'ids')", name="resolution_rule_field_group"),
        sa.CheckConstraint(
            "rule_type IN ('auto_apply', 'exclude', 'variant_create', 'quiz_default')",
            name="resolution_rule_type",
        ),
    )
    op.create_index("ix_resolution_rules_user_id", "resolution_rules", ["user_id"])
    op.create_index("ix_resolution_rules_expires_at", "resolution_rules", ["expires_at"])
    op.create_index("ix_resolution_rule_user_supplier_group", "resolution_rules", ["user_id", "supplier_code", "field_group"])

    op.create_table(
        "resolution_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("batch_id", sa.Integer(), sa.ForeignKey("resolution_batches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="SET NULL"), nullable=True),
        sa.Column("shopify_product_id", sa.BigInteger(), nullable=True),
        sa.Column("shopify_variant_id", sa.BigInteger(), nullable=True),
        sa.Column("supplier_code", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="pending"),
        sa.Column("structural_state", sa.String(length=128), nullable=True),
        sa.Column("conflict_reason", sa.Text(), nullable=True),
        sa.Column("product_label", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'ready', 'awaiting_approval', 'approved', "
            "'structural_conflict', 'excluded', 'applied', 'failed')",
            name="resolution_item_status",
        ),
    )
    op.create_index("ix_resolution_items_batch_id", "resolution_items", ["batch_id"])
    op.create_index("ix_resolution_items_product_id", "resolution_items", ["product_id"])
    op.create_index("ix_resolution_items_shopify_product_id", "resolution_items", ["shopify_product_id"])
    op.create_index("ix_resolution_items_shopify_variant_id", "resolution_items", ["shopify_variant_id"])
    op.create_index("ix_resolution_item_batch_status", "resolution_items", ["batch_id", "status"])
    op.create_index("ix_resolution_item_product", "resolution_items", ["product_id"])

    op.create_table(
        "resolution_changes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("resolution_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("field_group", sa.String(length=32), nullable=False),
        sa.Column("field_name", sa.String(length=128), nullable=False),
        sa.Column("before_value", sa.JSON(), nullable=True),
        sa.Column("after_value", sa.JSON(), nullable=True),
        sa.Column("reason_sentence", sa.Text(), nullable=True),
        sa.Column("reason_factors", sa.JSON(), nullable=True),
        sa.Column("confidence_score", sa.Numeric(4, 3), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="awaiting_approval"),
        sa.Column("applied_rule_id", sa.Integer(), sa.ForeignKey("resolution_rules.id", ondelete="SET NULL"), nullable=True),
        sa.Column("blocked_by_rule_id", sa.Integer(), sa.ForeignKey("resolution_rules.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("field_group IN ('images', 'text', 'pricing', 'ids')", name="resolution_change_field_group"),
        sa.CheckConstraint(
            "status IN ('auto_applied', 'awaiting_approval', 'approved', 'rejected', "
            "'blocked_exclusion', 'structural_conflict', 'applied', 'failed')",
            name="resolution_change_status",
        ),
    )
    op.create_index("ix_resolution_changes_item_id", "resolution_changes", ["item_id"])
    op.create_index("ix_resolution_change_item_status", "resolution_changes", ["item_id", "status"])
    op.create_index("ix_resolution_change_field", "resolution_changes", ["field_name"])

    op.create_table(
        "resolution_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("batch_id", sa.Integer(), sa.ForeignKey("resolution_batches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("resolution_items.id", ondelete="CASCADE"), nullable=True),
        sa.Column("snapshot_type", sa.String(length=64), nullable=False),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "snapshot_type IN ('batch_manifest', 'product_pre_change')",
            name="resolution_snapshot_type",
        ),
    )
    op.create_index("ix_resolution_snapshots_batch_id", "resolution_snapshots", ["batch_id"])
    op.create_index("ix_resolution_snapshots_item_id", "resolution_snapshots", ["item_id"])
    op.create_index("ix_resolution_snapshots_checksum", "resolution_snapshots", ["checksum"])
    op.create_index("ix_resolution_snapshot_batch_type", "resolution_snapshots", ["batch_id", "snapshot_type"])

    op.create_table(
        "recovery_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("batch_id", sa.Integer(), sa.ForeignKey("resolution_batches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("resolution_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("store_id", sa.Integer(), sa.ForeignKey("shopify_stores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=False),
        sa.Column("reason_detail", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("snapshot_id", sa.Integer(), sa.ForeignKey("resolution_snapshots.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "reason_code IN ('stale_target', 'deleted_target', 'preflight_conflict', "
            "'critical_apply_failure', 'policy_exclusion')",
            name="recovery_log_reason",
        ),
    )
    op.create_index("ix_recovery_logs_batch_id", "recovery_logs", ["batch_id"])
    op.create_index("ix_recovery_logs_item_id", "recovery_logs", ["item_id"])
    op.create_index("ix_recovery_logs_store_id", "recovery_logs", ["store_id"])
    op.create_index("ix_recovery_logs_snapshot_id", "recovery_logs", ["snapshot_id"])
    op.create_index("ix_recovery_log_batch_reason", "recovery_logs", ["batch_id", "reason_code"])
    op.create_index("ix_recovery_log_store_created", "recovery_logs", ["store_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_recovery_log_store_created", table_name="recovery_logs")
    op.drop_index("ix_recovery_log_batch_reason", table_name="recovery_logs")
    op.drop_index("ix_recovery_logs_snapshot_id", table_name="recovery_logs")
    op.drop_index("ix_recovery_logs_store_id", table_name="recovery_logs")
    op.drop_index("ix_recovery_logs_item_id", table_name="recovery_logs")
    op.drop_index("ix_recovery_logs_batch_id", table_name="recovery_logs")
    op.drop_table("recovery_logs")

    op.drop_index("ix_resolution_snapshot_batch_type", table_name="resolution_snapshots")
    op.drop_index("ix_resolution_snapshots_checksum", table_name="resolution_snapshots")
    op.drop_index("ix_resolution_snapshots_item_id", table_name="resolution_snapshots")
    op.drop_index("ix_resolution_snapshots_batch_id", table_name="resolution_snapshots")
    op.drop_table("resolution_snapshots")

    op.drop_index("ix_resolution_change_field", table_name="resolution_changes")
    op.drop_index("ix_resolution_change_item_status", table_name="resolution_changes")
    op.drop_index("ix_resolution_changes_item_id", table_name="resolution_changes")
    op.drop_table("resolution_changes")

    op.drop_index("ix_resolution_item_product", table_name="resolution_items")
    op.drop_index("ix_resolution_item_batch_status", table_name="resolution_items")
    op.drop_index("ix_resolution_items_shopify_variant_id", table_name="resolution_items")
    op.drop_index("ix_resolution_items_shopify_product_id", table_name="resolution_items")
    op.drop_index("ix_resolution_items_product_id", table_name="resolution_items")
    op.drop_index("ix_resolution_items_batch_id", table_name="resolution_items")
    op.drop_table("resolution_items")

    op.drop_index("ix_resolution_rule_user_supplier_group", table_name="resolution_rules")
    op.drop_index("ix_resolution_rules_expires_at", table_name="resolution_rules")
    op.drop_index("ix_resolution_rules_user_id", table_name="resolution_rules")
    op.drop_table("resolution_rules")

    op.drop_index("ix_resolution_batch_store_status", table_name="resolution_batches")
    op.drop_index("ix_resolution_batch_user_status", table_name="resolution_batches")
    op.drop_index("ix_resolution_batches_lock_expires_at", table_name="resolution_batches")
    op.drop_index("ix_resolution_batches_scheduled_for", table_name="resolution_batches")
    op.drop_index("ix_resolution_batches_store_id", table_name="resolution_batches")
    op.drop_index("ix_resolution_batches_user_id", table_name="resolution_batches")
    op.drop_table("resolution_batches")

