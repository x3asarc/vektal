"""Add schema_json column to assistant_tool_registry

Revision ID: g14_2_03_schema_json
Revises: g14_2_01_tool_examples
Create Date: 2026-02-26 13:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "g14_2_03_schema_json"
down_revision = "g14_2_01_tool_examples"
branch_labels = None
depends_on = None


def _table_columns(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade():
    columns = _table_columns("assistant_tool_registry")
    if not columns:
        return

    # Add schema_json column
    if "schema_json" not in columns:
        op.add_column(
            "assistant_tool_registry",
            sa.Column("schema_json", postgresql.JSONB(), nullable=True),
        )

    # Populate schema_json from existing name, description and metadata_json
    # (metadata_json contains inputSchema and input_examples)
    if "metadata_json" in columns:
        op.execute("""
        UPDATE assistant_tool_registry
        SET schema_json = jsonb_build_object(
            'name', tool_id,
            'description', description,
            'inputSchema', metadata_json->'inputSchema',
            'input_examples', metadata_json->'input_examples'
        )
        WHERE metadata_json IS NOT NULL
        """)

    # Ensure non-null rows before setting NOT NULL constraint.
    op.execute("UPDATE assistant_tool_registry SET schema_json = '{}'::jsonb WHERE schema_json IS NULL")

    # Make column non-nullable after population
    op.alter_column("assistant_tool_registry", "schema_json", nullable=False)


def downgrade():
    columns = _table_columns("assistant_tool_registry")
    if columns and "schema_json" in columns:
        op.drop_column("assistant_tool_registry", "schema_json")
