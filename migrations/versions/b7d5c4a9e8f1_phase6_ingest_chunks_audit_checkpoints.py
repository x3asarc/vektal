"""Phase 6 ingest chunks + audit checkpoints schema

Revision ID: b7d5c4a9e8f1
Revises: 4d8f6b9c2e1a
Create Date: 2026-02-10 23:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "b7d5c4a9e8f1"
down_revision = "4d8f6b9c2e1a"
branch_labels = None
depends_on = None


def _column_names(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns(table_name)}


def _index_names(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _check_constraint_names(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {
        constraint["name"]
        for constraint in inspector.get_check_constraints(table_name)
        if constraint.get("name")
    }


def _has_check_constraint(table_name: str, expected_name: str) -> bool:
    existing = _check_constraint_names(table_name)
    if expected_name in existing:
        return True
    prefixed = f"ck_{table_name}_{expected_name}"
    return prefixed in existing


def _foreign_key_names(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {
        fk["name"]
        for fk in inspector.get_foreign_keys(table_name)
        if fk.get("name")
    }


def _upgrade_postgresql() -> None:
    """PostgreSQL-specific enum and index operations."""
    op.execute(
        """
        DO $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM pg_enum e
            JOIN pg_type t ON t.oid = e.enumtypid
            WHERE t.typname = 'job_type' AND e.enumlabel = 'INGEST_CATALOG'
          ) THEN
            ALTER TYPE job_type ADD VALUE 'INGEST_CATALOG';
          END IF;
        END$$;
        """
    )
    for value in ("QUEUED", "CANCEL_REQUESTED", "FAILED_TERMINAL"):
        op.execute(
            f"""
            DO $$
            BEGIN
              IF NOT EXISTS (
                SELECT 1 FROM pg_enum e
                JOIN pg_type t ON t.oid = e.enumtypid
                WHERE t.typname = 'job_status' AND e.enumlabel = '{value}'
              ) THEN
                ALTER TYPE job_status ADD VALUE '{value}';
              END IF;
            END$$;
            """
        )

    # PostgreSQL requires new enum labels to be committed before use in index predicates.
    op.execute("COMMIT")
    if "uq_jobs_active_ingest_per_store" not in _index_names("jobs"):
        op.create_index(
            "uq_jobs_active_ingest_per_store",
            "jobs",
            ["store_id"],
            unique=True,
            postgresql_where=sa.text(
                "store_id IS NOT NULL "
                "AND job_type = 'INGEST_CATALOG' "
                "AND status IN ('PENDING', 'QUEUED', 'RUNNING', 'CANCEL_REQUESTED')"
            ),
        )


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    job_columns = _column_names("jobs")
    if "store_id" not in job_columns:
        op.add_column("jobs", sa.Column("store_id", sa.Integer(), nullable=True))
    if "total_products" not in job_columns:
        op.add_column("jobs", sa.Column("total_products", sa.Integer(), nullable=True, server_default="0"))
    if "processed_count" not in job_columns:
        op.add_column("jobs", sa.Column("processed_count", sa.Integer(), nullable=True, server_default="0"))
    if "cancellation_requested_at" not in job_columns:
        op.add_column("jobs", sa.Column("cancellation_requested_at", sa.DateTime(timezone=True), nullable=True))
    if "terminal_reason" not in job_columns:
        op.add_column("jobs", sa.Column("terminal_reason", sa.String(length=255), nullable=True))

    job_fks = _foreign_key_names("jobs")
    fk_name = op.f("fk_jobs_store_id_shopify_stores")
    if fk_name not in job_fks:
        op.create_foreign_key(
            fk_name,
            "jobs",
            "shopify_stores",
            ["store_id"],
            ["id"],
            ondelete="CASCADE",
        )

    job_indexes = _index_names("jobs")
    ix_store_id = op.f("ix_jobs_store_id")
    if ix_store_id not in job_indexes:
        op.create_index(ix_store_id, "jobs", ["store_id"], unique=False)

    op.execute(
        "UPDATE jobs "
        "SET total_products = COALESCE(total_items, 0), "
        "processed_count = LEAST(COALESCE(processed_items, 0), COALESCE(total_items, 0))"
    )

    op.alter_column("jobs", "total_products", nullable=False, server_default=None)
    op.alter_column("jobs", "processed_count", nullable=False, server_default=None)
    if not _has_check_constraint("jobs", "job_processed_count_bounds"):
        op.create_check_constraint(
            "job_processed_count_bounds",
            "jobs",
            "processed_count >= 0 AND processed_count <= total_products",
        )

    if dialect == "postgresql":
        ingest_chunk_status = postgresql.ENUM(
            "PENDING",
            "IN_PROGRESS",
            "COMPLETED",
            "FAILED_TERMINAL",
            name="ingest_chunk_status",
            create_type=False,
        )
        audit_dispatch_status = postgresql.ENUM(
            "PENDING_DISPATCH",
            "DISPATCHED",
            name="audit_dispatch_status",
            create_type=False,
        )
        op.execute(
            "DO $$ BEGIN "
            "IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'ingest_chunk_status') THEN "
            "CREATE TYPE ingest_chunk_status AS ENUM ('PENDING','IN_PROGRESS','COMPLETED','FAILED_TERMINAL'); "
            "END IF; "
            "END $$;"
        )
        op.execute(
            "DO $$ BEGIN "
            "IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'audit_dispatch_status') THEN "
            "CREATE TYPE audit_dispatch_status AS ENUM ('PENDING_DISPATCH','DISPATCHED'); "
            "END IF; "
            "END $$;"
        )
    else:
        ingest_chunk_status = sa.Enum(
            "PENDING",
            "IN_PROGRESS",
            "COMPLETED",
            "FAILED_TERMINAL",
            name="ingest_chunk_status",
        )
        audit_dispatch_status = sa.Enum(
            "PENDING_DISPATCH",
            "DISPATCHED",
            name="audit_dispatch_status",
        )

    inspector = sa.inspect(bind)
    if not inspector.has_table("ingest_chunks"):
        op.create_table(
            "ingest_chunks",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("job_id", sa.Integer(), nullable=False),
            sa.Column("store_id", sa.Integer(), nullable=False),
            sa.Column("chunk_idx", sa.Integer(), nullable=False),
            sa.Column("status", ingest_chunk_status, nullable=False, server_default="PENDING"),
            sa.Column("claim_token", sa.String(length=64), nullable=True),
            sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("processed_expected", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("processed_actual", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("product_ids_json", sa.JSON(), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("task_id", sa.String(length=255), nullable=True),
            sa.Column("cancellation_code", sa.String(length=64), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("job_id", "chunk_idx", name="uq_ingest_chunks_job_chunk_idx"),
            sa.CheckConstraint(
                "processed_expected >= 0 "
                "AND processed_actual >= 0 "
                "AND processed_actual <= processed_expected",
                name="ck_ingest_chunks_processed_bounds",
            ),
            sa.CheckConstraint(
                "status != 'COMPLETED' OR completed_at IS NOT NULL",
                name="ck_ingest_chunks_completed_has_timestamp",
            ),
        )
    ingest_indexes = _index_names("ingest_chunks")
    for index_name, columns in (
        (op.f("ix_ingest_chunks_job_id"), ["job_id"]),
        (op.f("ix_ingest_chunks_store_id"), ["store_id"]),
        (op.f("ix_ingest_chunks_status"), ["status"]),
        (op.f("ix_ingest_chunks_claimed_at"), ["claimed_at"]),
        (op.f("ix_ingest_chunks_claim_token"), ["claim_token"]),
    ):
        if index_name not in ingest_indexes:
            op.create_index(index_name, "ingest_chunks", columns, unique=False)

    if not inspector.has_table("audit_checkpoints"):
        op.create_table(
            "audit_checkpoints",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("job_id", sa.Integer(), nullable=False),
            sa.Column("store_id", sa.Integer(), nullable=False),
            sa.Column("checkpoint", sa.Integer(), nullable=False),
            sa.Column("dispatch_status", audit_dispatch_status, nullable=False, server_default="PENDING_DISPATCH"),
            sa.Column("dispatch_attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("next_dispatch_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("payload", sa.JSON(), nullable=True),
            sa.Column("task_id", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("job_id", "checkpoint", name="uq_audit_checkpoints_job_checkpoint"),
            sa.CheckConstraint("checkpoint >= 1 AND checkpoint <= 100", name="ck_audit_checkpoint_bounds"),
        )
    audit_indexes = _index_names("audit_checkpoints")
    for index_name, columns in (
        (op.f("ix_audit_checkpoints_job_id"), ["job_id"]),
        (op.f("ix_audit_checkpoints_store_id"), ["store_id"]),
        (op.f("ix_audit_checkpoints_checkpoint"), ["checkpoint"]),
        (op.f("ix_audit_checkpoints_dispatch_status"), ["dispatch_status"]),
        (op.f("ix_audit_checkpoints_next_dispatch_at"), ["next_dispatch_at"]),
    ):
        if index_name not in audit_indexes:
            op.create_index(index_name, "audit_checkpoints", columns, unique=False)

    if dialect == "postgresql":
        _upgrade_postgresql()


def _downgrade_postgresql() -> None:
    """Rebuild enums to drop Phase 6 labels safely."""
    op.execute("UPDATE jobs SET status = 'PENDING' WHERE status = 'QUEUED'")
    op.execute("UPDATE jobs SET status = 'CANCELLED' WHERE status = 'CANCEL_REQUESTED'")
    op.execute("UPDATE jobs SET status = 'FAILED' WHERE status = 'FAILED_TERMINAL'")
    op.execute("UPDATE jobs SET job_type = 'CATALOG_IMPORT' WHERE job_type = 'INGEST_CATALOG'")

    op.execute("ALTER TABLE jobs ALTER COLUMN status TYPE TEXT USING status::text")
    op.execute("ALTER TABLE jobs ALTER COLUMN job_type TYPE TEXT USING job_type::text")
    op.execute("DROP TYPE job_status")
    op.execute("DROP TYPE job_type")

    op.execute(
        "CREATE TYPE job_status AS ENUM ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED')"
    )
    op.execute(
        "CREATE TYPE job_type AS ENUM "
        "('PRODUCT_SYNC', 'PRODUCT_ENRICH', 'IMAGE_PROCESS', 'CATALOG_IMPORT', 'VENDOR_SCRAPE')"
    )

    op.execute("ALTER TABLE jobs ALTER COLUMN status TYPE job_status USING status::job_status")
    op.execute("ALTER TABLE jobs ALTER COLUMN job_type TYPE job_type USING job_type::job_type")


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.drop_index("uq_jobs_active_ingest_per_store", table_name="jobs")

    with op.batch_alter_table("audit_checkpoints", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_audit_checkpoints_next_dispatch_at"))
        batch_op.drop_index(batch_op.f("ix_audit_checkpoints_dispatch_status"))
        batch_op.drop_index(batch_op.f("ix_audit_checkpoints_checkpoint"))
        batch_op.drop_index(batch_op.f("ix_audit_checkpoints_store_id"))
        batch_op.drop_index(batch_op.f("ix_audit_checkpoints_job_id"))
    op.drop_table("audit_checkpoints")

    with op.batch_alter_table("ingest_chunks", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_ingest_chunks_claim_token"))
        batch_op.drop_index(batch_op.f("ix_ingest_chunks_claimed_at"))
        batch_op.drop_index(batch_op.f("ix_ingest_chunks_status"))
        batch_op.drop_index(batch_op.f("ix_ingest_chunks_store_id"))
        batch_op.drop_index(batch_op.f("ix_ingest_chunks_job_id"))
    op.drop_table("ingest_chunks")

    if dialect == "postgresql":
        op.execute("DROP TYPE IF EXISTS ingest_chunk_status")
        op.execute("DROP TYPE IF EXISTS audit_dispatch_status")

    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.drop_constraint("job_processed_count_bounds", type_="check")
        batch_op.drop_index(batch_op.f("ix_jobs_store_id"))
        batch_op.drop_constraint(batch_op.f("fk_jobs_store_id_shopify_stores"), type_="foreignkey")
        batch_op.drop_column("terminal_reason")
        batch_op.drop_column("cancellation_requested_at")
        batch_op.drop_column("processed_count")
        batch_op.drop_column("total_products")
        batch_op.drop_column("store_id")

    if dialect == "postgresql":
        _downgrade_postgresql()
