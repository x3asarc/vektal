"""Phase 13.1 enrichment capability, policy lineage, and dry-run contracts

Revision ID: f2b3c4d5e6f7
Revises: e5f6a7b8c9d0
Create Date: 2026-02-16 23:59:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "f2b3c4d5e6f7"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_enrichment_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("store_id", sa.Integer(), sa.ForeignKey("shopify_stores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vendor_code", sa.String(length=64), nullable=False),
        sa.Column("run_profile", sa.String(length=32), nullable=False, server_default="quick"),
        sa.Column("target_language", sa.String(length=8), nullable=False, server_default="de"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("policy_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("mapping_version", sa.Integer(), nullable=True),
        sa.Column("idempotency_hash", sa.String(length=64), nullable=False),
        sa.Column("dry_run_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("alt_text_policy", sa.String(length=32), nullable=False, server_default="preserve"),
        sa.Column("protected_columns_json", sa.JSON(), nullable=False),
        sa.Column("capability_audit_json", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "run_profile IN ('quick', 'standard', 'deep')",
            name="product_enrichment_run_profile",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'dry_run_ready', 'approved', 'applied', 'expired', 'cancelled')",
            name="product_enrichment_run_status",
        ),
        sa.CheckConstraint(
            "target_language IN ('de', 'en')",
            name="product_enrichment_run_language",
        ),
        sa.CheckConstraint(
            "alt_text_policy IN ('preserve', 'approved_overwrite')",
            name="product_enrichment_run_alt_text_policy",
        ),
        sa.UniqueConstraint("store_id", "idempotency_hash", name="uq_product_enrichment_run_store_hash"),
    )
    op.create_index("ix_product_enrichment_runs_user_id", "product_enrichment_runs", ["user_id"])
    op.create_index("ix_product_enrichment_runs_store_id", "product_enrichment_runs", ["store_id"])
    op.create_index("ix_product_enrichment_runs_vendor_code", "product_enrichment_runs", ["vendor_code"])
    op.create_index("ix_product_enrichment_runs_status", "product_enrichment_runs", ["status"])
    op.create_index("ix_product_enrichment_runs_idempotency_hash", "product_enrichment_runs", ["idempotency_hash"])
    op.create_index("ix_product_enrichment_runs_dry_run_expires_at", "product_enrichment_runs", ["dry_run_expires_at"])
    op.create_index(
        "ix_product_enrichment_run_store_status",
        "product_enrichment_runs",
        ["store_id", "status"],
    )
    op.create_index(
        "ix_product_enrichment_run_user_status",
        "product_enrichment_runs",
        ["user_id", "status"],
    )

    op.create_table(
        "product_enrichment_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "run_id",
            sa.Integer(),
            sa.ForeignKey("product_enrichment_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("field_group", sa.String(length=32), nullable=False),
        sa.Column("field_name", sa.String(length=128), nullable=False),
        sa.Column("decision_state", sa.String(length=32), nullable=False, server_default="suggested"),
        sa.Column("before_value", sa.JSON(), nullable=True),
        sa.Column("after_value", sa.JSON(), nullable=True),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("provenance", sa.JSON(), nullable=True),
        sa.Column("reason_codes", sa.JSON(), nullable=False),
        sa.Column("evidence_refs", sa.JSON(), nullable=True),
        sa.Column("requires_user_action", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_protected_column", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("alt_text_preserved", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("policy_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("mapping_version", sa.Integer(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "field_group IN ('images', 'text', 'pricing', 'ids', 'metadata')",
            name="product_enrichment_item_field_group",
        ),
        sa.CheckConstraint(
            "decision_state IN ('suggested', 'blocked', 'approved', 'rejected', 'applied')",
            name="product_enrichment_item_decision_state",
        ),
    )
    op.create_index("ix_product_enrichment_items_run_id", "product_enrichment_items", ["run_id"])
    op.create_index("ix_product_enrichment_items_product_id", "product_enrichment_items", ["product_id"])
    op.create_index("ix_product_enrichment_items_field_name", "product_enrichment_items", ["field_name"])
    op.create_index(
        "ix_product_enrichment_item_run_state",
        "product_enrichment_items",
        ["run_id", "decision_state"],
    )
    op.create_index("ix_product_enrichment_item_product", "product_enrichment_items", ["product_id"])

    with op.batch_alter_table("vendor_field_mappings", schema=None) as batch_op:
        batch_op.add_column(sa.Column("protected_columns_json", sa.JSON(), nullable=False, server_default="[]"))
        batch_op.add_column(
            sa.Column(
                "alt_text_policy",
                sa.String(length=32),
                nullable=False,
                server_default="preserve",
            )
        )
        batch_op.add_column(sa.Column("policy_version", sa.Integer(), nullable=False, server_default="1"))
        batch_op.add_column(sa.Column("governance_metadata_json", sa.JSON(), nullable=True))
        batch_op.create_check_constraint(
            "vendor_field_mapping_alt_text_policy",
            "alt_text_policy IN ('preserve', 'approved_overwrite')",
        )
        batch_op.create_check_constraint(
            "vendor_field_mapping_policy_version",
            "policy_version >= 1",
        )


def downgrade() -> None:
    with op.batch_alter_table("vendor_field_mappings", schema=None) as batch_op:
        batch_op.drop_constraint("vendor_field_mapping_policy_version", type_="check")
        batch_op.drop_constraint("vendor_field_mapping_alt_text_policy", type_="check")
        batch_op.drop_column("governance_metadata_json")
        batch_op.drop_column("policy_version")
        batch_op.drop_column("alt_text_policy")
        batch_op.drop_column("protected_columns_json")

    op.drop_index("ix_product_enrichment_item_product", table_name="product_enrichment_items")
    op.drop_index("ix_product_enrichment_item_run_state", table_name="product_enrichment_items")
    op.drop_index("ix_product_enrichment_items_field_name", table_name="product_enrichment_items")
    op.drop_index("ix_product_enrichment_items_product_id", table_name="product_enrichment_items")
    op.drop_index("ix_product_enrichment_items_run_id", table_name="product_enrichment_items")
    op.drop_table("product_enrichment_items")

    op.drop_index("ix_product_enrichment_run_user_status", table_name="product_enrichment_runs")
    op.drop_index("ix_product_enrichment_run_store_status", table_name="product_enrichment_runs")
    op.drop_index("ix_product_enrichment_runs_dry_run_expires_at", table_name="product_enrichment_runs")
    op.drop_index("ix_product_enrichment_runs_idempotency_hash", table_name="product_enrichment_runs")
    op.drop_index("ix_product_enrichment_runs_status", table_name="product_enrichment_runs")
    op.drop_index("ix_product_enrichment_runs_vendor_code", table_name="product_enrichment_runs")
    op.drop_index("ix_product_enrichment_runs_store_id", table_name="product_enrichment_runs")
    op.drop_index("ix_product_enrichment_runs_user_id", table_name="product_enrichment_runs")
    op.drop_table("product_enrichment_runs")
