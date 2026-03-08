"""Task 11a: Graphiti bridge — (:Episodic)-[:REFERS_TO]->(:Function).

Runs periodically after each episode sync to wire Developer-KG episodes
(CODE_INTENT, BUG_ROOT_CAUSE_IDENTIFIED, CONVENTION_ESTABLISHED, FAILURE_PATTERN)
to their target Function nodes.

Pre-conditions (Task 10): Episodic nodes must have function_signature property set
via the piggyback write in GraphitiIngestor.ingest_episode().
"""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from dotenv import load_dotenv
from scripts.graph.sync_to_neo4j import Neo4jCodebaseSync

load_dotenv()

_DEVELOPER_KG_TYPES = {
    "code_intent", "bug_root_cause_identified",
    "convention_established", "failure_pattern"
}


def run_bridge(syncer: Neo4jCodebaseSync) -> dict:
    """
    Wire (:Episodic {function_signature})-[:REFERS_TO]->(:Function {function_signature}).

    Only creates edges where:
    - Episodic node has function_signature set (Developer-KG piggyback write)
    - Matching Function node exists with EndDate IS NULL (current version)
    - REFERS_TO edge does not already exist (MERGE is idempotent)

    Returns: dict with edge_count, unmatched_count
    """
    with syncer.driver.session() as session:
        # Create REFERS_TO edges for all Episodic nodes with function_signature
        result = session.run("""
            MATCH (ep:Episodic)
            WHERE ep.function_signature IS NOT NULL
            MATCH (f:Function {function_signature: ep.function_signature})
            WHERE f.EndDate IS NULL
            MERGE (ep)-[r:REFERS_TO]->(f)
            RETURN count(r) as edges_created
        """)
        edges_created = result.single()['edges_created']

        # Count unmatched (Episodic with function_signature but no matching Function)
        unmatched = session.run("""
            MATCH (ep:Episodic)
            WHERE ep.function_signature IS NOT NULL
            AND NOT EXISTS {
                MATCH (ep)-[:REFERS_TO]->(:Function)
            }
            RETURN count(ep) as c
        """).single()['c']

        # Summary stats
        total_episodic = session.run(
            "MATCH (n:Episodic) RETURN count(n) as c"
        ).single()['c']
        with_sig = session.run(
            "MATCH (n:Episodic) WHERE n.function_signature IS NOT NULL RETURN count(n) as c"
        ).single()['c']
        referred = session.run(
            "MATCH ()-[r:REFERS_TO]->() RETURN count(r) as c"
        ).single()['c']

    return {
        'total_episodic': total_episodic,
        'with_function_signature': with_sig,
        'refers_to_edges': referred,
        'edges_created_this_run': edges_created,
        'unmatched': unmatched,
    }


def main():
    print("=== Task 11a: Graphiti Bridge ===\n")

    syncer = Neo4jCodebaseSync()
    try:
        stats = run_bridge(syncer)

        print(f"Episodic nodes total:        {stats['total_episodic']}")
        print(f"With function_signature:     {stats['with_function_signature']}")
        print(f":REFERS_TO edges (total):    {stats['refers_to_edges']}")
        print(f"Edges created this run:      {stats['edges_created_this_run']}")

        if stats['unmatched']:
            print(f"\n[WARN] {stats['unmatched']} Episodic nodes with function_signature "
                  f"have no matching Function (function may not be in graph)")

        if stats['total_episodic'] == 0:
            print("\n[INFO] Episodic layer is empty — bridge ready but no edges to create.")
            print("       Bridge will auto-wire on next episode emission.")

        print("\n[OK] Task 11a complete")
    finally:
        syncer.close()


if __name__ == "__main__":
    main()
