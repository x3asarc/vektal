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

def upgrade():
    # Add schema_json column
    op.add_column(
        'assistant_tool_registry',
        sa.Column('schema_json', postgresql.JSONB(), nullable=True)
    )

    # Populate schema_json from existing name, description and metadata_json
    # (metadata_json contains inputSchema and input_examples)
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

    # Make column non-nullable after population
    op.alter_column('assistant_tool_registry', 'schema_json', nullable=False)


def downgrade():
    op.drop_column('assistant_tool_registry', 'schema_json')
