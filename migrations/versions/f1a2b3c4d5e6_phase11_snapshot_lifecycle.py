"""Phase 11 snapshot lifecycle and recovery retry metadata

Revision ID: f1a2b3c4d5e6
Revises: a7b8c9d0e1f2
Create Date: 2026-02-15 21:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f1a2b3c4d5e6"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    fk_name = "fk_rs_canonical_snapshot_id"
    op.add_column(
        "resolution_snapshots",
        sa.Column("canonical_snapshot_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "resolution_snapshots",
        sa.Column("retention_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        fk_name,
        "resolution_snapshots",
        "resolution_snapshots",
        ["canonical_snapshot_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_resolution_snapshots_canonical_snapshot_id",
        "resolution_snapshots",
        ["canonical_snapshot_id"],
    )
    op.create_index(
        "ix_resolution_snapshot_checksum_type",
        "resolution_snapshots",
        ["checksum", "snapshot_type"],
    )

    op.drop_constraint("resolution_snapshot_type", "resolution_snapshots", type_="check")
    op.create_check_constraint(
        "resolution_snapshot_type",
        "resolution_snapshots",
        "snapshot_type IN ('baseline', 'batch_manifest', 'product_pre_change')",
    )

    op.add_column("recovery_logs", sa.Column("replay_metadata", sa.JSON(), nullable=True))
    op.add_column("recovery_logs", sa.Column("deferred_until", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    fk_name = "fk_rs_canonical_snapshot_id"
    op.drop_column("recovery_logs", "deferred_until")
    op.drop_column("recovery_logs", "replay_metadata")

    op.drop_constraint("resolution_snapshot_type", "resolution_snapshots", type_="check")
    op.create_check_constraint(
        "resolution_snapshot_type",
        "resolution_snapshots",
        "snapshot_type IN ('batch_manifest', 'product_pre_change')",
    )

    op.drop_index("ix_resolution_snapshot_checksum_type", table_name="resolution_snapshots")
    op.drop_index("ix_resolution_snapshots_canonical_snapshot_id", table_name="resolution_snapshots")
    op.drop_constraint(
        fk_name,
        "resolution_snapshots",
        type_="foreignkey",
    )
    op.drop_column("resolution_snapshots", "retention_expires_at")
    op.drop_column("resolution_snapshots", "canonical_snapshot_id")
