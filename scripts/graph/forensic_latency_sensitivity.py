"""
Forensic: Latency Sensitivity Map
How many CALLS hops separate each API route from each God Function?
Shorter = more latency-sensitive. Depth 1 = direct. Depth 2 = one intermediary. etc.
"""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from dotenv import load_dotenv
from neo4j import GraphDatabase
load_dotenv()

uri  = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME", "neo4j")
pwd  = os.getenv("NEO4J_PASSWORD")
driver = GraphDatabase.driver(uri, auth=(user, pwd))

GOD_SIGS = [
    "scripts.governance.validate_governance.read_text",
    "src.cli.approvals.list",
    "src.api.app.create_openapi_app",
    "src.memory.memory_manager.ensure_memory_layout",
    "src.core.graphiti_client.get_graphiti_client",
]

SEP = "-" * 72

# Depth-1: direct (APIRoute TRIGGERS god function)
print(SEP)
print("LATENCY SENSITIVITY MAP: API Route -> God Function (hops)")
print(SEP)

with driver.session() as s:
    # Depth 1 direct
    d1 = s.run("""
        MATCH (ar:APIRoute)-[:TRIGGERS]->(god:Function)
        WHERE god.function_signature IN $sigs AND god.EndDate IS NULL
        RETURN ar.url_template AS url, ar.http_method AS method,
               ar.blueprint AS bp, god.function_signature AS god, 1 AS hops
        ORDER BY url
    """, sigs=GOD_SIGS).data()

    # Depth 2
    d2 = s.run("""
        MATCH (ar:APIRoute)-[:TRIGGERS]->(h:Function)-[:CALLS]->(god:Function)
        WHERE god.function_signature IN $sigs
          AND h.EndDate IS NULL AND god.EndDate IS NULL
          AND NOT EXISTS { (ar)-[:TRIGGERS]->(god) }
        RETURN ar.url_template AS url, ar.http_method AS method,
               ar.blueprint AS bp, god.function_signature AS god,
               h.function_signature AS via, 2 AS hops
        ORDER BY url
        LIMIT 30
    """, sigs=GOD_SIGS).data()

    # Depth 3
    d3 = s.run("""
        MATCH (ar:APIRoute)-[:TRIGGERS]->(h1:Function)-[:CALLS]->(h2:Function)-[:CALLS]->(god:Function)
        WHERE god.function_signature IN $sigs
          AND h1.EndDate IS NULL AND h2.EndDate IS NULL AND god.EndDate IS NULL
          AND NOT EXISTS { (ar)-[:TRIGGERS]->(god) }
          AND NOT EXISTS {
              MATCH (ar)-[:TRIGGERS]->(h:Function)-[:CALLS]->(god)
              WHERE h.EndDate IS NULL
          }
        RETURN ar.url_template AS url, ar.http_method AS method,
               ar.blueprint AS bp, god.function_signature AS god,
               h1.function_signature AS via1, h2.function_signature AS via2,
               3 AS hops
        ORDER BY url
        LIMIT 30
    """, sigs=GOD_SIGS).data()

all_rows = d1 + d2 + d3

# Group by god function
from collections import defaultdict
by_god = defaultdict(list)
for r in all_rows:
    by_god[r["god"]].append(r)

god_labels = {
    "scripts.governance.validate_governance.read_text": "#1 validate_governance.read_text",
    "src.cli.approvals.list": "#2 cli.approvals.list",
    "src.api.app.create_openapi_app": "#3 api.app.create_openapi_app",
    "src.memory.memory_manager.ensure_memory_layout": "#4 memory_manager.ensure_memory_layout",
    "src.core.graphiti_client.get_graphiti_client": "#5 graphiti_client.get_graphiti_client",
}

for sig in GOD_SIGS:
    rows = sorted(by_god[sig], key=lambda r: r["hops"])
    label = god_labels[sig]
    print(f"\n  GOD {label}")
    if not rows:
        print(f"    No API route reaches this function within 3 hops.")
        continue
    for r in rows:
        method = r.get("method") or "?"
        url = r["url"]
        hops = r["hops"]
        bp = r.get("bp") or ""
        via_parts = []
        if r.get("via"):
            via_parts.append(r["via"].split(".")[-1])
        if r.get("via2"):
            via_parts.append(r["via2"].split(".")[-1])
        via_str = f"  via: {' -> '.join(via_parts)}" if via_parts else ""
        print(f"    [{hops}hop] [{method}] {url}  ({bp}){via_str}")

# Summary: most latency-exposed (depth-1 API routes to get_graphiti_client)
print()
print(SEP)
print("HIGHEST LATENCY EXPOSURE: routes that reach get_graphiti_client")
print(SEP)

ggc_routes = [r for r in all_rows if r["god"] == "src.core.graphiti_client.get_graphiti_client"]
if ggc_routes:
    for r in sorted(ggc_routes, key=lambda x: x["hops"]):
        print(f"  [{r['hops']}hop] [{r.get('method','?')}] {r['url']}  ({r.get('bp','')})")
else:
    print("  No API routes reach get_graphiti_client within 3 hops.")
    print("  (It is called from Celery tasks only — not on the synchronous HTTP path)")

print()
driver.close()
