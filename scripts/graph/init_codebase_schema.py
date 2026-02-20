#!/usr/bin/env python3
"""Initialize codebase knowledge graph schema in Neo4j."""

import os
import sys
import argparse
import asyncio
import logging
from typing import Any

# Add project root to Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.core.graphiti_client import get_graphiti_client, check_graph_availability
from src.core.codebase_schema import ensure_schema, CODEBASE_INDEXES, CODEBASE_CONSTRAINTS

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

async def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize codebase knowledge graph schema in Neo4j.")
    parser.add_argument("--dry-run", action="store_true", help="Print schema creation plan without applying it")
    args = parser.parse_args()

    if args.dry_run:
        logger.info("DRY RUN: Schema creation plan")
        for idx in CODEBASE_INDEXES:
            if idx.get("type") == "UNIQUE":
                logger.info(f" - Would create unique constraint for {idx['label']}.{idx['property']}")
            elif "properties" in idx:
                logger.info(f" - Would create composite index for {idx['label']} on {idx['properties']}")
        for const in CODEBASE_CONSTRAINTS:
            if const.get("type") == "EXISTS":
                logger.info(f" - Would create existence constraint for {const['label']}.{const['property']}")
        logger.info("DRY RUN: Exiting successfully")
        return 0

    # Ensure Neo4j credentials are appropriately set for the client fetching
    os.environ["GRAPH_ORACLE_ENABLED"] = "true"
    
    # Fail gracefully if graph is not available
    if not check_graph_availability(timeout_seconds=3.0):
        logger.warning("Graph database is unavailable. Skipping schema initialization but exiting 0 to not block pipelines.")
        return 0
        
    client = get_graphiti_client()
    if client is None:
        logger.warning("Graph database client is None. Exiting gracefully.")
        return 0

    logger.info("Initializing schema...")
    success = await ensure_schema(client)
    
    if success:
        logger.info("Schema initialized successfully.")
        return 0
    else:
        logger.error("Failed to initialize schema.")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
