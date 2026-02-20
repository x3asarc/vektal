"""
Neo4j schema definitions for the codebase knowledge graph.
"""

import logging

logger = logging.getLogger(__name__)

CODEBASE_INDEXES = [
    # Node indexes for fast lookups
    {"label": "File", "property": "path", "type": "UNIQUE"},
    {"label": "Module", "property": "path", "type": "UNIQUE"},
    {"label": "Class", "property": "full_name", "type": "UNIQUE"},
    {"label": "Function", "property": "full_name", "type": "UNIQUE"},
    {"label": "PlanningDoc", "property": "path", "type": "UNIQUE"},
    # Composite indexes for common queries
    {"label": "File", "properties": ["language", "last_modified"]},
    {"label": "Function", "properties": ["file_path", "name"]},
]

CODEBASE_CONSTRAINTS = [
    # Ensure referential integrity
    {"type": "EXISTS", "label": "File", "property": "path"},
    {"type": "EXISTS", "label": "Function", "property": "full_name"},
]

async def ensure_schema(client, dry_run=False):
    """
    Ensure the Neo4j schema is initialized with required indexes and constraints.
    Idempotent operation using IF NOT EXISTS clauses.
    """
    success = True
    
    if dry_run:
        logger.info("DRY RUN: Schema creation skipped.")
        logger.info(f"Would create {len(CODEBASE_INDEXES)} indexes and {len(CODEBASE_CONSTRAINTS)} constraints.")
        return True

    try:
        if not hasattr(client, 'driver'):
            logger.error("Client does not have a valid driver")
            return False
            
        async with client.driver.session() as session:
            # Create indexes
            for index in CODEBASE_INDEXES:
                try:
                    if "type" in index and index["type"] == "UNIQUE":
                        query = f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{index['label']}) REQUIRE n.{index['property']} IS UNIQUE"
                        await session.run(query)
                        logger.info(f"Created/Verified UNIQUE constraint on {index['label']}.{index['property']}")
                    elif "properties" in index:
                        props = ", ".join([f"n.{p}" for p in index["properties"]])
                        query = f"CREATE INDEX IF NOT EXISTS FOR (n:{index['label']}) ON ({props})"
                        await session.run(query)
                        logger.info(f"Created/Verified composite index on {index['label']} ({props})")
                    elif "property" in index:
                        query = f"CREATE INDEX IF NOT EXISTS FOR (n:{index['label']}) ON (n.{index['property']})"
                        await session.run(query)
                        logger.info(f"Created/Verified index on {index['label']}.{index['property']}")
                except Exception as e:
                    logger.error(f"Failed to create index {index}: {e}")
                    success = False
            
            # Create constraints (EXISTS constraints typically require Neo4j Enterprise Edition)
            for constraint in CODEBASE_CONSTRAINTS:
                try:
                    if constraint.get("type") == "EXISTS":
                        query = f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{constraint['label']}) REQUIRE n.{constraint['property']} IS NOT NULL"
                        await session.run(query)
                        logger.info(f"Created/Verified EXISTS constraint on {constraint['label']}.{constraint['property']}")
                except Exception as e:
                    # Downgrade to warning as this fails on Neo4j Community Edition
                    logger.warning(f"Could not create EXISTS constraint {constraint} (may be Neo4j Community Edition): {e}")

    except Exception as e:
        logger.error(f"Error ensuring schema: {e}")
        return False
        
    return success
