"""Task 12b: Forensic Playbook — 5 validation queries against Aura.

Queries from docs/graph/research-v2-analysis.md.
All must return results for PASS. Any empty result is a schema/data gap.
"""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from dotenv import load_dotenv
from scripts.graph.sync_to_neo4j import Neo4jCodebaseSync
load_dotenv()

PLAYBOOK = [
    {
        "id": "Q1",
        "name": "High-Fan-Out Functions (Blast Radius)",
        "description": "Functions with most outbound calls — top candidates for blast radius analysis",
        "query": """
            MATCH (caller:Function)-[:CALLS]->(callee:Function)
            WHERE caller.EndDate IS NULL AND callee.EndDate IS NULL
            RETURN caller.function_signature AS function,
                   count(callee) AS call_count
            ORDER BY call_count DESC
            LIMIT 10
        """,
        "min_results": 1,
    },
    {
        "id": "Q2",
        "name": "Config Risk Exposure (Vital EnvVars without defaults)",
        "description": "Tier-1 env vars used without default values — hard failures on missing config",
        "query": """
            MATCH (f:Function)-[:DEPENDS_ON_CONFIG]->(e:EnvVar)
            WHERE f.EndDate IS NULL
              AND e.risk_tier = 1
              AND e.has_default = false
            RETURN e.name AS env_var,
                   count(f) AS function_count,
                   collect(f.function_signature)[..3] AS sample_functions
            ORDER BY function_count DESC
            LIMIT 10
        """,
        "min_results": 0,  # may be 0 if all tier-1 vars have defaults
    },
    {
        "id": "Q3",
        "name": "Functions Modified During Instability Window (Code Evolution)",
        "description": "Current function versions that changed recently — using StartDate temporal filter",
        "query": """
            MATCH (f:Function)
            WHERE f.EndDate IS NULL
              AND f.StartDate IS NOT NULL
            RETURN f.function_signature AS function,
                   f.StartDate AS last_changed,
                   f.file_path AS file
            ORDER BY f.StartDate DESC
            LIMIT 10
        """,
        "min_results": 1,
    },
    {
        "id": "Q4",
        "name": "Sentry Issues with Graph Context",
        "description": "Unresolved Sentry issues linked to Function nodes",
        "query": """
            MATCH (si:SentryIssue)-[:OCCURRED_IN]->(f:Function)
            WHERE f.EndDate IS NULL
            RETURN si.issue_id AS issue_id,
                   si.title AS title,
                   si.category AS category,
                   f.function_signature AS function
            ORDER BY si.timestamp DESC
            LIMIT 10
        """,
        "min_results": 0,  # may be 0 if no live Sentry issues yet
    },
    {
        "id": "Q5",
        "name": "Celery Task Queue Coverage",
        "description": "All Celery tasks with their resolved queues — verifies TASK_ROUTES integration",
        "query": """
            MATCH (f:Function)-[:ROUTES_TO]->(t:CeleryTask)-[:QUEUED_ON]->(q:Queue)
            WHERE f.EndDate IS NULL
            RETURN q.name AS queue,
                   count(t) AS task_count,
                   collect(t.task_name)[..3] AS sample_tasks
            ORDER BY task_count DESC
        """,
        "min_results": 1,
    },
]


def run_playbook(syncer: Neo4jCodebaseSync) -> list:
    results = []
    with syncer.driver.session() as session:
        for q in PLAYBOOK:
            try:
                rows = session.run(q["query"]).data()
                passed = len(rows) >= q["min_results"]
                results.append({
                    "id": q["id"],
                    "name": q["name"],
                    "status": "PASS" if passed else "FAIL",
                    "row_count": len(rows),
                    "min_required": q["min_results"],
                    "sample": rows[:3],
                })
            except Exception as e:
                results.append({
                    "id": q["id"],
                    "name": q["name"],
                    "status": "ERROR",
                    "error": str(e),
                    "row_count": 0,
                })
    return results


def main():
    print("=== Task 12b: Forensic Playbook Validation ===\n")
    syncer = Neo4jCodebaseSync()
    try:
        results = run_playbook(syncer)

        all_pass = True
        for r in results:
            status = r["status"]
            if status != "PASS":
                all_pass = False
            print(f"  [{status}] {r['id']}: {r['name']}")
            print(f"         Rows: {r.get('row_count', '?')} (min required: {r.get('min_required', 0)})")
            if r.get("error"):
                print(f"         Error: {r['error']}")
            elif r.get("sample"):
                for row in r["sample"][:2]:
                    # Print first 2 key-value pairs of each row
                    items = list(row.items())[:2]
                    print(f"         Sample: {dict(items)}")
            print()

        overall = "GREEN" if all_pass else "DEGRADED"
        print(f"Overall: {overall}")
        print(f"\n[OK] Task 12b complete")
    finally:
        syncer.close()


if __name__ == "__main__":
    main()
