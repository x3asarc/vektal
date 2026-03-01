"""
Initialize Neo4j vector index for tool search.
"""
import os
import sys
import logging
import asyncio

# Ensure absolute imports resolve
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.core.graphiti_client import get_graphiti_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_tool_vector_index():
    """Create vector index on ToolEntity.embedding for semantic search."""
    # Force enable for this session
    os.environ["GRAPH_ORACLE_ENABLED"] = "true"
    
    client = get_graphiti_client()
    if not client:
        logger.warning("Neo4j not available or credentials missing, skipping index creation")
        return

    if not hasattr(client, 'driver'):
        logger.error("Graphiti client has no driver")
        return

    # Use client.driver directly for DDL
    async with client.driver.session() as session:
        try:
            logger.info("Creating vector index tool_embedding_index...")
            # We use label 'Tool' as per QUERY_TEMPLATES
            query = """
            CALL db.index.vector.createNodeIndex(
                'tool_embedding_index',
                'Tool',
                'embedding',
                384,
                'cosine'
            )
            """
            await session.run(query)
            logger.info("Successfully created tool_embedding_index")
        except Exception as e:
            if 'already exists' in str(e).lower() or 'equivalent index' in str(e).lower():
                logger.info("Vector index tool_embedding_index already exists")
            else:
                logger.error(f"Failed to create vector index: {e}")

if __name__ == "__main__":
    asyncio.run(create_tool_vector_index())
