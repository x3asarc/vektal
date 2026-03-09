"""
Parallel Aura query executor — READ-ONLY batch execution.
Approved: ImprovementProposal ip-729c4e56a7e0
"""

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

# Safety: Block write operations
WRITE_KEYWORDS = ["MERGE", "SET", "CREATE", "DELETE", "REMOVE", "DETACH"]

def validate_read_only(cypher: str) -> None:
    """Raise ValueError if query contains write operations."""
    upper_query = cypher.upper()
    for keyword in WRITE_KEYWORDS:
        if keyword in upper_query:
            raise ValueError(f"WRITE operation detected: {keyword}. Only READ queries allowed.")

def execute_query(driver, label: str, cypher: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute single query and return result with metadata."""
    start = time.time()
    try:
        validate_read_only(cypher)
        with driver.session() as session:
            result = session.run(cypher, **params)
            data = [record.data() for record in result]
        duration_ms = int((time.time() - start) * 1000)
        return {"data": data, "duration_ms": duration_ms, "error": None}
    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        return {"data": [], "duration_ms": duration_ms, "error": str(e)}

def execute_parallel(queries: Dict[str, Dict[str, Any]], max_workers: int = 5) -> Dict[str, Any]:
    """
    Execute multiple independent Aura queries in parallel.

    Args:
        queries: Dict mapping label → {"cypher": str, "params": dict}
        max_workers: Max concurrent threads (default 5)

    Returns:
        Dict mapping label → {"data": list, "duration_ms": int, "error": str|None}
    """
    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI"),
        auth=(os.getenv("NEO4J_USERNAME", "neo4j"), os.getenv("NEO4J_PASSWORD"))
    )

    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(execute_query, driver, label, q["cypher"], q["params"]): label
            for label, q in queries.items()
        }

        for future in as_completed(futures):
            label = futures[future]
            results[label] = future.result()

    driver.close()
    return results
