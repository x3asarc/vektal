"""Phase 11 product history and staging governance models

Revision ID: a7b8c9d0e1f2
Revises: f0a1b2c3d4e5
Create Date: 2026-02-15 20:40:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a7b8c9d0e1f2"
down_revision = "f0a1b2c3d4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_change_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("store_id", sa.Integer(), sa.ForeignKey("shopify_stores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="workspace"),
        sa.Column("event_type", sa.String(length=64), nullable=False, server_default="manual_edit"),
        sa.Column("before_payload", sa.JSON(), nullable=True),
        sa.Column("after_payload", sa.JSON(), nullable=True),
        sa.Column("diff_payload", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("resolution_batch_id", sa.Integer(), sa.ForeignKey("resolution_batches.id", ondelete="SET NULL")),
        sa.Column("resolution_rule_id", sa.Integer(), sa.ForeignKey("resolution_rules.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("source IN ('workspace', 'chat', 'system', 'import')", name="product_change_event_source"),
        sa.CheckConstraint(
            "event_type IN ('manual_edit', 'bulk_stage', 'dry_run_compile', 'apply', 'rollback')",
            name="product_change_event_type",
        ),
    )
    op.create_index("ix_product_change_events_product_id", "product_change_events", ["product_id"])
    op.create_index("ix_product_change_events_store_id", "product_change_events", ["store_id"])
    op.create_index("ix_product_change_events_actor_user_id", "product_change_events", ["actor_user_id"])
    op.create_index("ix_product_change_events_resolution_batch_id", "product_change_events", ["resolution_batch_id"])
    op.create_index("ix_product_change_events_resolution_rule_id", "product_change_events", ["resolution_rule_id"])
    op.create_index(
        "ix_product_change_event_product_created",
        "product_change_events",
        ["product_id", "created_at"],
    )
    op.create_index(
        "ix_product_change_event_store_created",
        "product_change_events",
        ["store_id", "created_at"],
    )

    op.create_table(
        "vendor_field_mappings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("store_id", sa.Integer(), sa.ForeignKey("shopify_stores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vendor_code", sa.String(length=64), nullable=False),
        sa.Column("field_group", sa.String(length=32), nullable=False),
        sa.Column("mapping_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("coverage_status", sa.String(length=32), nullable=False, server_default="incomplete"),
        sa.Column("source_schema", sa.JSON(), nullable=True),
        sa.Column("canonical_mapping", sa.JSON(), nullable=False),
        sa.Column("required_fields", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "field_group IN ('images', 'text', 'pricing', 'ids')",
            name="vendor_field_mapping_field_group",
        ),
        sa.CheckConstraint(
            "coverage_status IN ('ready', 'incomplete', 'draft')",
            name="vendor_field_mapping_coverage_status",
        ),
        sa.UniqueConstraint(
            "store_id",
            "vendor_code",
            "field_group",
            "mapping_version",
            name="uq_vendor_mapping_version",
        ),
    )
    op.create_index("ix_vendor_field_mappings_store_id", "vendor_field_mappings", ["store_id"])
    op.create_index("ix_vendor_field_mappings_vendor_code", "vendor_field_mappings", ["vendor_code"])
    op.create_index("ix_vendor_field_mappings_field_group", "vendor_field_mappings", ["field_group"])
    op.create_index("ix_vendor_field_mappings_created_by_user_id", "vendor_field_mappings", ["created_by_user_id"])
    op.create_index("ix_vendor_mapping_store_vendor", "vendor_field_mappings", ["store_id", "vendor_code"])
    op.create_index(
        "ix_vendor_mapping_active",
        "vendor_field_mappings",
        ["store_id", "vendor_code", "field_group", "is_active"],
    )


def downgrade() -> None:
    op.drop_index("ix_vendor_mapping_active", table_name="vendor_field_mappings")
    op.drop_index("ix_vendor_mapping_store_vendor", table_name="vendor_field_mappings")
    op.drop_index("ix_vendor_field_mappings_created_by_user_id", table_name="vendor_field_mappings")
    op.drop_index("ix_vendor_field_mappings_field_group", table_name="vendor_field_mappings")
    op.drop_index("ix_vendor_field_mappings_vendor_code", table_name="vendor_field_mappings")
    op.drop_index("ix_vendor_field_mappings_store_id", table_name="vendor_field_mappings")
    op.drop_table("vendor_field_mappings")

    op.drop_index("ix_product_change_event_store_created", table_name="product_change_events")
    op.drop_index("ix_product_change_event_product_created", table_name="product_change_events")
    op.drop_index("ix_product_change_events_resolution_rule_id", table_name="product_change_events")
    op.drop_index("ix_product_change_events_resolution_batch_id", table_name="product_change_events")
    op.drop_index("ix_product_change_events_actor_user_id", table_name="product_change_events")
    op.drop_index("ix_product_change_events_store_id", table_name="product_change_events")
    op.drop_index("ix_product_change_events_product_id", table_name="product_change_events")
    op.drop_table("product_change_events")
