"""Quick test of route/task extraction without Aura connection."""
import time
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from pathlib import Path
from scripts.graph.sync_to_neo4j import _extract_routes_from_file, _extract_tasks_from_file, _TASK_ROUTE_MAP

py_files = [str(p) for p in Path('src').rglob('*.py')]
print(f"Found {len(py_files)} Python files to scan")

t0 = time.time()
all_routes = []
all_tasks = []
for fp in py_files:
    all_routes.extend(_extract_routes_from_file(fp))
    all_tasks.extend(_extract_tasks_from_file(fp))
t1 = time.time()

print(f"Extraction: {t1-t0:.2f}s")
print(f"Routes found: {len(all_routes)}")
print(f"Tasks found:  {len(all_tasks)}")
print()
print("Sample routes:")
for r in all_routes[:8]:
    print(f"  {r['http_methods']} {r['url_template']} -> {r['function_full_name']}")
print()
print("Sample tasks:")
for t in all_tasks[:8]:
    print(f"  {t['task_name']}  queue={t['queue']}")

misconfigs = [t for t in all_tasks if (t['queue'] or '').startswith('MISCONFIGURED:')]
if misconfigs:
    print(f"\nWARN: {len(misconfigs)} misconfigured queue(s):")
    for t in misconfigs:
        print(f"  {t['task_name']} queue={t['queue']}")
