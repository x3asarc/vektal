"""Task 6: Sync APIRoute + CeleryTask nodes to Aura (incremental — no full re-sync)."""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from pathlib import Path
from dotenv import load_dotenv
from scripts.graph.sync_to_neo4j import (
    Neo4jCodebaseSync,
    _extract_routes_from_file,
    _extract_tasks_from_file,
)

load_dotenv()


def main():
    print("=== Task 6: APIRoute + CeleryTask Sync ===\n")

    py_files = [str(p) for p in Path('src').rglob('*.py')]
    print(f"Scanning {len(py_files)} Python files...")

    all_routes = []
    all_tasks = []
    for fp in py_files:
        all_routes.extend(_extract_routes_from_file(fp))
        all_tasks.extend(_extract_tasks_from_file(fp))

    print(f"Found: {len(all_routes)} routes, {len(all_tasks)} tasks")

    syncer = Neo4jCodebaseSync()
    try:
        # Clear only the new node types (don't wipe the whole graph)
        with syncer.driver.session() as session:
            session.run("MATCH (n:APIRoute) DETACH DELETE n")
            session.run("MATCH (n:CeleryTask) DETACH DELETE n")
            session.run("MATCH (n:Queue) DETACH DELETE n")
        print("[OK] Cleared existing APIRoute/CeleryTask/Queue nodes")

        syncer.sync_api_routes(all_routes)
        syncer.sync_celery_tasks(all_tasks)

        # Verification counts
        with syncer.driver.session() as session:
            r = session.run("MATCH (n:APIRoute) RETURN count(n) as c").single()
            t = session.run("MATCH (n:CeleryTask) RETURN count(n) as c").single()
            q = session.run("MATCH (n:Queue) RETURN count(n) as c").single()
            trig = session.run("MATCH ()-[r:TRIGGERS]->() RETURN count(r) as c").single()
            routes_to = session.run("MATCH ()-[r:ROUTES_TO]->() RETURN count(r) as c").single()
            queued = session.run("MATCH ()-[r:QUEUED_ON]->() RETURN count(r) as c").single()

        print(f"\n=== Aura verification ===")
        print(f"  :APIRoute nodes:   {r['c']}")
        print(f"  :CeleryTask nodes: {t['c']}")
        print(f"  :Queue nodes:      {q['c']}")
        print(f"  :TRIGGERS edges:   {trig['c']}")
        print(f"  :ROUTES_TO edges:  {routes_to['c']}")
        print(f"  :QUEUED_ON edges:  {queued['c']}")

        unlinked_routes = len(all_routes) - trig['c']
        unlinked_tasks = len(all_tasks) - routes_to['c']
        if unlinked_routes:
            print(f"\n[WARN] {unlinked_routes} routes not linked to a Function (function not in graph)")
        if unlinked_tasks:
            print(f"[WARN] {unlinked_tasks} tasks not linked to a Function (function not in graph)")

        print("\n[OK] Task 6 complete")
    finally:
        syncer.close()


if __name__ == "__main__":
    main()
