"""
Forensic Query: God Functions investigation.

Stage 1 — Top 5 by in-degree CALLS (most-called by other functions)
Stage 2 — Queue cross-reference (via ROUTES_TO + QUEUED_ON)
Stage 3 — Tier 1 config exposure (DEPENDS_ON_CONFIG where risk_tier = 1)
Stage 4 — Graphiti FAILURE_PATTERN episodes for 'timeout' or 'concurrency'
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

SEP = "-" * 72

# ── Stage 1: God Functions (in-degree CALLS) ─────────────────────────────────
print(SEP)
print("STAGE 1: TOP 5 GOD FUNCTIONS (most in-bound CALLS)")
print(SEP)

with driver.session() as s:
    god_rows = s.run("""
        MATCH (caller:Function)-[:CALLS]->(callee:Function)
        WHERE caller.EndDate IS NULL AND callee.EndDate IS NULL
        WITH callee, count(caller) AS caller_count
        ORDER BY caller_count DESC
        LIMIT 5
        RETURN callee.function_signature    AS function_signature,
               callee.name                  AS name,
               callee.file_path             AS file_path,
               callee.is_async              AS is_async,
               caller_count
    """).data()

god_sigs = [r["function_signature"] for r in god_rows]

for rank, r in enumerate(god_rows, 1):
    print(f"  #{rank}  {r['function_signature']}")
    print(f"       file:       {r['file_path']}")
    print(f"       is_async:   {r['is_async']}")
    print(f"       in-degree:  {r['caller_count']} callers")
    print()

# ── Stage 2: Queue routing ────────────────────────────────────────────────────
print(SEP)
print("STAGE 2: QUEUE ROUTING (via CeleryTask or APIRoute)")
print(SEP)

with driver.session() as s:
    # Direct: Function -[:ROUTES_TO]-> CeleryTask -[:QUEUED_ON]-> Queue
    queue_direct = s.run("""
        UNWIND $sigs AS sig
        MATCH (f:Function {function_signature: sig})-[:ROUTES_TO]->(ct:CeleryTask)-[:QUEUED_ON]->(q:Queue)
        WHERE f.EndDate IS NULL
        RETURN sig, ct.task_name AS task, q.name AS queue, 'DIRECT' AS via
    """, sigs=god_sigs).data()

    # Indirect: APIRoute -[:TRIGGERS]-> Function (god function is a handler)
    queue_via_api = s.run("""
        UNWIND $sigs AS sig
        MATCH (ar:APIRoute)-[:TRIGGERS]->(f:Function {function_signature: sig})
        WHERE f.EndDate IS NULL
        RETURN sig, ar.route_id AS route_id, ar.url_template AS url,
               ar.http_method AS method, 'VIA_APIROUTE' AS via
    """, sigs=god_sigs).data()

queue_map = {sig: [] for sig in god_sigs}
for row in queue_direct:
    queue_map[row["sig"]].append(row)
for row in queue_via_api:
    queue_map[row["sig"]].append(row)

for sig in god_sigs:
    routes = queue_map[sig]
    if routes:
        for r in routes:
            if r["via"] == "DIRECT":
                print(f"  {sig}")
                print(f"    -> CeleryTask: {r['task']}  Queue: {r['queue']}")
            else:
                print(f"  {sig}")
                print(f"    -> APIRoute [{r['method']}] {r['url']}")
    else:
        print(f"  {sig}")
        print(f"    -> NO QUEUE MAPPING (utility / internal function)")
    print()

# ── Stage 3: Tier 1 config exposure ──────────────────────────────────────────
print(SEP)
print("STAGE 3: TIER 1 CONFIG EXPOSURE")
print(SEP)

with driver.session() as s:
    tier1_rows = s.run("""
        UNWIND $sigs AS sig
        MATCH (f:Function {function_signature: sig})-[:DEPENDS_ON_CONFIG]->(e:EnvVar)
        WHERE f.EndDate IS NULL AND e.risk_tier = 1
        RETURN sig,
               e.name          AS env_var,
               e.has_default   AS has_default,
               e.risk_tier     AS tier
        ORDER BY sig, e.name
    """, sigs=god_sigs).data()

if tier1_rows:
    for r in tier1_rows:
        default_flag = "[NO DEFAULT - hard fail on missing]" if not r["has_default"] else "[has default]"
        print(f"  {r['sig']}")
        print(f"    Tier 1 EnvVar: {r['env_var']}  {default_flag}")
        print()
else:
    print("  No direct Tier 1 config exposure found on God Functions.")
    print("  (may be inherited via transitive callee — check blast radius)")
    print()

# ── Stage 4: FAILURE_PATTERN episodes (timeout / concurrency) ────────────────
print(SEP)
print("STAGE 4: FAILURE_PATTERN EPISODES (timeout | concurrency)")
print(SEP)

with driver.session() as s:
    # Check episodic count first
    ep_count = s.run(
        "MATCH (n:Episodic) RETURN count(n) as c"
    ).single()["c"]
    print(f"  Episodic layer total nodes: {ep_count}")

    if ep_count > 0:
        # Search for timeout/concurrency episodes linked to our god functions
        fp_rows = s.run("""
            MATCH (ep:Episodic)-[:REFERS_TO]->(f:Function)
            WHERE f.EndDate IS NULL
              AND f.function_signature IN $sigs
              AND ep.episode_type = 'failure_pattern'
              AND (toLower(ep.content) CONTAINS 'timeout'
                   OR toLower(ep.content) CONTAINS 'concurrency')
            RETURN ep.name     AS episode_id,
                   ep.content  AS body,
                   f.function_signature AS function
            LIMIT 10
        """, sigs=god_sigs).data()

        if fp_rows:
            for r in fp_rows:
                print(f"  EPISODE: {r['episode_id']}")
                print(f"  Function: {r['function']}")
                print(f"  Body snippet: {str(r['body'])[:300]}")
                print()
        else:
            print("  No REFERS_TO-linked FAILURE_PATTERN episodes for God Functions.")
            print()

        # Broader: any FAILURE_PATTERN episode mentioning timeout/concurrency in content
        broad = s.run("""
            MATCH (ep:Episodic)
            WHERE ep.episode_type = 'failure_pattern'
              AND (toLower(ep.content) CONTAINS 'timeout'
                   OR toLower(ep.content) CONTAINS 'concurrency')
            RETURN ep.name, ep.content, ep.function_signature
            LIMIT 5
        """).data()
        if broad:
            print("  Broader search (any FAILURE_PATTERN with timeout/concurrency):")
            for r in broad:
                print(f"    Episode: {r['ep.name']}, sig: {r['ep.function_signature']}")
        else:
            print("  Broader search: 0 FAILURE_PATTERN episodes with timeout/concurrency keywords.")

    else:
        # Fall back: LongTermPattern (FAILURE_JOURNEY.md entries)
        print("  Episodic layer empty. Falling back to :LongTermPattern nodes.")
        print()
        with driver.session() as s2:
            lp_rows = s2.run("""
                MATCH (lp:LongTermPattern)
                WHERE lp.source = 'FAILURE_JOURNEY.md'
                  AND (toLower(lp.description) CONTAINS 'timeout'
                       OR toLower(lp.description) CONTAINS 'concurrency'
                       OR toLower(lp.description) CONTAINS 'celery'
                       OR toLower(lp.description) CONTAINS 'sync')
                RETURN lp.pattern_id   AS id,
                       lp.domain       AS domain,
                       lp.description  AS description,
                       lp.task_id      AS task_id
                LIMIT 10
            """).data()
            if lp_rows:
                print("  Relevant LongTermPattern entries (keyword match):")
                for r in lp_rows:
                    print(f"    [{r['domain']}] {r['task_id']}: {r['description'][:150]}")
                    print()
            else:
                print("  No LongTermPattern entries match timeout/concurrency/celery/sync.")

        # Also search god functions against FAILURE_JOURNEY module paths
        print()
        print("  Cross-referencing God Function module paths against LongTermPattern:")
        god_modules = list({sig.rsplit(".", 1)[0] for sig in god_sigs})
        with driver.session() as s3:
            module_hits = s3.run("""
                MATCH (lp:LongTermPattern)
                WHERE ANY(mod IN $modules WHERE toLower(lp.description) CONTAINS mod)
                RETURN lp.domain, lp.description, lp.task_id LIMIT 5
            """, modules=god_modules).data()
            if module_hits:
                for r in module_hits:
                    print(f"    [{r['lp.domain']}] {r['lp.task_id']}: {r['lp.description'][:150]}")
            else:
                print("    No cross-reference hits on God Function module paths.")

print()
print(SEP)
print("END OF FORENSIC REPORT")
print(SEP)

driver.close()
