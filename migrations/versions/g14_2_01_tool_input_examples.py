"""Phase 14.2 tool input examples

Revision ID: g14_2_01_tool_examples
Revises: f2b3c4d5e6f7
Create Date: 2026-02-26 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
import json

revision = "g14_2_01_tool_examples"
down_revision = "f2b3c4d5e6f7"
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Seed input_examples for default tools in assistant_tool_registry
    examples_map = {
        "chat.respond": [{"content": "I have found 5 products matching your search."}],
        "products.read": [{"sku": "R0530"}, {"sku": "PENTART-123"}],
        "products.search": [
            {"query": "red acrylic paint"},
            {"query": "decoupage glue 100ml"},
        ],
        "resolution.dry_run": [
            {
                "sku": "R0530",
                "action": "update",
                "fields": {"price": 12.50, "inventory_quantity": 20},
            }
        ],
        "resolution.apply": [{"dry_run_id": 123}, {"dry_run_id": 456}],
        "agent.spawn_sub_agent": [
            {
                "objective": "Research competitive pricing for acrylic paints",
                "tool_scope": ["products.search", "web.search"],
            }
        ],
    }

    for tool_id, examples in examples_map.items():
        examples_json = json.dumps(examples)
        # metadata_json is json (not jsonb), so cast to jsonb for merge ops then cast back.
        op.execute(
            sa.text(
                """
                UPDATE assistant_tool_registry
                SET metadata_json = (
                    COALESCE(metadata_json::jsonb, '{}'::jsonb) ||
                    jsonb_build_object('input_examples', CAST(:examples_json AS jsonb))
                )::json
                WHERE tool_id = :tool_id
                """
            ).bindparams(tool_id=tool_id, examples_json=examples_json)
        )
def downgrade() -> None:
    # Remove input_examples from metadata_json
    op.execute(
        sa.text(
            """
            UPDATE assistant_tool_registry
            SET metadata_json = (
                COALESCE(metadata_json::jsonb, '{}'::jsonb) - 'input_examples'
            )::json
            WHERE COALESCE(metadata_json::jsonb, '{}'::jsonb) ? 'input_examples'
            """
        )
    )
