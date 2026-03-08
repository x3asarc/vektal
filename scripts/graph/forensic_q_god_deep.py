"""
Supplementary forensic queries — deeper analysis on God Functions.

- Stage 2b: What queued Celery tasks call the God Functions? (indirect exposure)
- Stage 3b: Transitive Tier 1 config blast — callers-of-callers
- Stage 4b: SentryIssue cross-reference (timeout/unavailable patterns)
- Stage 5:  God Function call fan-out — what do they call that matters?
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

# ── Stage 2b: Which Celery tasks (queued functions) call a God Function? ──────
print(SEP)
print("STAGE 2b: QUEUED CALLERS OF GOD FUNCTIONS")
print("(Celery tasks that directly call into a God Function)")
print(SEP)

with driver.session() as s:
    queued_callers = s.run("""
        UNWIND $sigs AS god_sig
        MATCH (caller:Function)-[:CALLS]->(god:Function {function_signature: god_sig})
        WHERE caller.EndDate IS NULL AND god.EndDate IS NULL
        MATCH (caller)-[:ROUTES_TO]->(ct:CeleryTask)-[:QUEUED_ON]->(q:Queue)
        RETURN god_sig,
               caller.function_signature AS caller_sig,
               ct.task_name              AS celery_task,
               q.name                    AS queue,
               ct.is_bound               AS is_bound
        ORDER BY god_sig, q.name
    """, sigs=GOD_SIGS).data()

if queued_callers:
    current_god = None
    for r in queued_callers:
        if r["god_sig"] != current_god:
            print(f"\n  God Function: {r['god_sig']}")
            current_god = r["god_sig"]
        print(f"    <- {r['caller_sig']}")
        print(f"       via Celery: {r['celery_task']}  on Queue: {r['queue']}")
else:
    print("  No queued Celery callers found for any God Function.")
    print("  These functions are invoked synchronously, not via queue.")

print()

# ── Stage 2c: Which APIRoutes indirectly reach God Functions? ─────────────────
print(SEP)
print("STAGE 2c: API ROUTES THAT REACH GOD FUNCTIONS (depth-2 CALLS)")
print(SEP)

with driver.session() as s:
    api_reach = s.run("""
        UNWIND $sigs AS god_sig
        MATCH (ar:APIRoute)-[:TRIGGERS]->(handler:Function)-[:CALLS]->(god:Function {function_signature: god_sig})
        WHERE handler.EndDate IS NULL AND god.EndDate IS NULL
        RETURN god_sig,
               ar.url_template AS url,
               ar.http_method  AS method,
               ar.blueprint    AS blueprint,
               handler.function_signature AS handler_sig
        ORDER BY god_sig, method
        LIMIT 20
    """, sigs=GOD_SIGS).data()

if api_reach:
    current_god = None
    for r in api_reach:
        if r["god_sig"] != current_god:
            print(f"\n  God Function: {r['god_sig']}")
            current_god = r["god_sig"]
        print(f"    [{r['method']}] {r['url']}  (blueprint: {r['blueprint']})")
        print(f"       handler: {r['handler_sig']}")
else:
    print("  No APIRoute → handler → God Function depth-2 paths found.")

print()

# ── Stage 3b: Transitive Tier 1 exposure — callers that use T1 config ─────────
print(SEP)
print("STAGE 3b: TIER 1 CONFIG EXPOSURE ON get_graphiti_client CALLERS")
print("(Functions that call get_graphiti_client AND also depend on T1 config)")
print(SEP)

with driver.session() as s:
    t1_callers = s.run("""
        MATCH (caller:Function)-[:CALLS]->(:Function {function_signature: 'src.core.graphiti_client.get_graphiti_client'})
        WHERE caller.EndDate IS NULL
        OPTIONAL MATCH (caller)-[:DEPENDS_ON_CONFIG]->(e:EnvVar)
        WHERE e.risk_tier = 1
        RETURN caller.function_signature AS caller_sig,
               caller.file_path         AS file,
               collect(e.name)          AS tier1_vars
        ORDER BY size(collect(e.name)) DESC
        LIMIT 10
    """).data()

    print(f"  Callers of get_graphiti_client: {len(t1_callers)}")
    for r in t1_callers:
        t1 = r["tier1_vars"]
        flag = f"  T1: {t1}" if t1 else "  no direct T1 config (inherits via get_graphiti_client)"
        print(f"    {r['caller_sig']}")
        print(f"      {flag}")

print()

# ── Stage 4b: SentryIssue cross-reference ─────────────────────────────────────
print(SEP)
print("STAGE 4b: SENTRY ISSUES TOUCHING GOD FUNCTION MODULES")
print(SEP)

with driver.session() as s:
    sentry_rows = s.run("""
        MATCH (si:SentryIssue)-[:REPORTED_IN|OCCURRED_IN]->(n)
        WHERE ANY(sig IN $sigs WHERE n.path CONTAINS replace(split(sig, '.')[1], '.', '/')
               OR n.function_signature = sig)
        RETURN si.issue_id  AS issue_id,
               si.title     AS title,
               si.category  AS category,
               si.culprit   AS culprit,
               type(head([(si)-[r]->(n) | r])) AS edge_type
        LIMIT 10
    """, sigs=GOD_SIGS).data()

    if sentry_rows:
        for r in sentry_rows:
            print(f"  Issue: {r['issue_id']} [{r['category']}]")
            print(f"  Title: {r['title']}")
            print(f"  Culprit: {r['culprit']}  (via {r['edge_type']})")
            print()
    else:
        # Broader: any sentry issue mentioning our god function modules
        god_modules = [sig.rsplit(".", 1)[0].replace(".", "/") for sig in GOD_SIGS]
        broad = s.run("""
            MATCH (si:SentryIssue)
            WHERE ANY(mod IN $modules WHERE si.culprit CONTAINS mod OR si.title CONTAINS mod)
               OR toLower(si.title) CONTAINS 'timeout'
               OR toLower(si.title) CONTAINS 'concurren'
               OR toLower(si.title) CONTAINS 'unavailabl'
            RETURN si.issue_id, si.title, si.category, si.culprit
        """, modules=god_modules).data()

        if broad:
            print("  Sentry issues matching god function modules or timeout/unavailable:")
            for r in broad:
                print(f"    [{r['si.category']}] {r['si.title']}")
                print(f"    culprit: {r['si.culprit']}")
                print()
        else:
            print("  No Sentry issues cross-reference God Function modules.")
            print("  All current SentryIssue nodes are mock/test data.")

print()

# ── Stage 5: What does get_graphiti_client call? (fan-out) ────────────────────
print(SEP)
print("STAGE 5: get_graphiti_client OUTBOUND CALLS + CONFIG EXPOSURE")
print("(What it calls + what T1/T2 config it directly reads)")
print(SEP)

with driver.session() as s:
    outbound = s.run("""
        MATCH (f:Function {function_signature: 'src.core.graphiti_client.get_graphiti_client'})
              -[:CALLS]->(callee:Function)
        WHERE f.EndDate IS NULL AND callee.EndDate IS NULL
        RETURN callee.function_signature AS callee, callee.file_path AS file
        ORDER BY callee
    """).data()

    configs = s.run("""
        MATCH (f:Function {function_signature: 'src.core.graphiti_client.get_graphiti_client'})
              -[:DEPENDS_ON_CONFIG]->(e:EnvVar)
        WHERE f.EndDate IS NULL
        RETURN e.name AS var, e.risk_tier AS tier, e.has_default AS has_default
        ORDER BY e.risk_tier, e.name
    """).data()

    print(f"  Outbound CALLS from get_graphiti_client: {len(outbound)}")
    for r in outbound:
        print(f"    -> {r['callee']}")

    print()
    print(f"  Config dependencies ({len(configs)} vars):")
    for r in configs:
        default_str = "has default" if r["has_default"] else "NO DEFAULT"
        print(f"    T{r['tier']}  {r['var']}  [{default_str}]")

print()
print(SEP)
print("END SUPPLEMENTARY REPORT")
print(SEP)

driver.close()
