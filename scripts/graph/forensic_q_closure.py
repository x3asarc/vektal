"""Gap closure + Sentry + drift check for forensic agent investigation."""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from dotenv import load_dotenv
from neo4j import GraphDatabase
load_dotenv()

uri  = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME", "neo4j")
pwd  = os.getenv("NEO4J_PASSWORD")
driver = GraphDatabase.driver(uri, auth=(user, pwd))

IMPL_SIGS = [
    "src.graph.infra_probe.probe_aura",
    "src.graph.infra_probe.probe_local_neo4j",
    "src.graph.infra_probe.active_remediation_loop",
    "src.graph.backend_resolver.probe_aura_http",
    "src.graph.backend_resolver.probe_bolt",
    "src.graph.backend_resolver.runtime_backend_mode",
    "src.graph.orchestrate_healers.orchestrate_remediation",
    "src.graph.orchestrate_healers.orchestrate_healing",
    "src.graph.orchestrate_healers.record_remediation_outcome",
    "src.graph.orchestrate_healers.normalize_sentry_issue",
    "src.graph.orchestrate_healers.route_service_for_classification",
]

print("=== 1. USES_SKILL edge: forensic-lead -> pico-warden ===")
with driver.session() as s:
    r = s.run("""
        MATCH (a:AgentDef {agent_id: '4eab1519698a'})
        MATCH (sk:SkillDef) WHERE sk.name = 'pico-warden'
        MERGE (a)-[rel:USES_SKILL]->(sk)
        RETURN type(rel) AS t, a.name AS agent, sk.name AS skill
    """).data()
    if r:
        print(f"  OK: (forensic-lead)-[:USES_SKILL]->(pico-warden) confirmed")
    else:
        print("  WARN: agent or skill not found")

print()
print("=== 2. IMPLEMENTS edges: pico-warden -> implementation Functions ===")
with driver.session() as s:
    s.run("MATCH (sk:SkillDef) WHERE sk.name = 'pico-warden' SET sk.impl_module = 'src.graph.infra_probe,src.graph.orchestrate_healers,src.graph.backend_resolver'")
    for sig in IMPL_SIGS:
        r = s.run("""
            MATCH (sk:SkillDef {name: 'pico-warden'})
            MATCH (f:Function {function_signature: $sig}) WHERE f.EndDate IS NULL
            MERGE (sk)-[rel:IMPLEMENTS]->(f)
            RETURN f.function_signature AS sig
        """, sig=sig).data()
        if r:
            print(f"  IMPLEMENTS -> {sig}")

print()
print("=== 3. Sentry issues on pico-warden impl functions ===")
with driver.session() as s:
    sentry = s.run("""
        MATCH (si:SentryIssue)-[:OCCURRED_IN|REPORTED_IN]->(target)
        WHERE target.function_signature IN $sigs
           OR (target.path IS NOT NULL AND
               ANY(sig IN $sigs WHERE target.path CONTAINS
                   replace(split(sig,'.',2)[2], '.', '/')))
        RETURN si.issue_id AS id, si.title AS title, si.category AS cat,
               si.culprit AS culprit, si.resolved AS resolved
    """, sigs=IMPL_SIGS).data()
    if sentry:
        for r in sentry:
            flag = "RESOLVED" if r["resolved"] else "UNRESOLVED"
            print(f"  [{flag}] [{r['cat']}] {r['title']}  culprit: {r['culprit']}")
    else:
        all_sentry = s.run("MATCH (si:SentryIssue) RETURN si.issue_id, si.title, si.category, si.resolved, si.culprit").data()
        print(f"  No Sentry issues on impl functions. All {len(all_sentry)} in graph:")
        for r in all_sentry:
            flag = "RESOLVED" if r["si.resolved"] else "UNRESOLVED"
            print(f"    [{flag}][{r['si.category']}] {r['si.title']}  culprit:{r['si.culprit']}")

print()
print("=== 4. LongTermPattern 14.3 domain (closest to scraping-stability) ===")
with driver.session() as s:
    ltp_14 = s.run("""
        MATCH (lp:LongTermPattern)
        WHERE lp.domain IN ['14.3', '07.1']
        RETURN lp.domain, lp.task_id, lp.description, lp.StartDate
        ORDER BY lp.StartDate DESC
    """).data()
    print(f"  14.3 + 07.1 entries: {len(ltp_14)}")
    for lp in ltp_14:
        print(f"  [{lp['lp.domain']}] {lp['lp.task_id']}  recorded:{str(lp['lp.StartDate'])[:10]}")
        print(f"    {(lp['lp.description'] or '')[:150]}")
    # Most recent 14.3 date
    last_14 = ltp_14[0]['lp.StartDate'] if ltp_14 else None

print()
print("=== 5. Drift: impl functions updated AFTER last 14.3 LTP? ===")
with driver.session() as s:
    if last_14:
        drifted = s.run("""
            MATCH (f:Function) WHERE f.EndDate IS NULL
              AND f.function_signature IN $sigs
              AND f.StartDate > $anchor
            RETURN f.function_signature AS sig, f.StartDate AS updated
            ORDER BY f.StartDate DESC
        """, sigs=IMPL_SIGS, anchor=str(last_14)).data()
        stable = s.run("""
            MATCH (f:Function) WHERE f.EndDate IS NULL
              AND f.function_signature IN $sigs
              AND f.StartDate <= $anchor
            RETURN f.function_signature AS sig, f.StartDate AS sd
            ORDER BY f.StartDate DESC
        """, sigs=IMPL_SIGS, anchor=str(last_14)).data()
        print(f"  Anchor: {last_14}")
        print(f"  DRIFTED (updated after anchor): {len(drifted)}")
        for r in drifted:
            print(f"    [DRIFT] {r['sig']}  at {r['updated']}")
        print(f"  STABLE: {len(stable)}")
        for r in stable:
            print(f"    [OK]    {r['sig']}  synced {str(r['sd'])[:19]}")
    else:
        print("  No 14.3 LTP anchor available.")

print()
print("=== 6. 'scraping-logic-stability': domain gap assessment ===")
with driver.session() as s:
    # Check if any FAILURE_JOURNEY entries mention scraping
    scraping_ltp = s.run("""
        MATCH (lp:LongTermPattern)
        WHERE toLower(lp.description) CONTAINS 'scrap'
           OR lp.domain CONTAINS 'scrap'
        RETURN lp.domain, lp.task_id, lp.description LIMIT 5
    """).data()
    if scraping_ltp:
        for r in scraping_ltp:
            print(f"  [{r['lp.domain']}] {r['lp.task_id']}: {r['lp.description'][:150]}")
    else:
        print("  CONFIRMED GAP: No 'scraping-logic-stability' domain exists.")
        print("  FAILURE_JOURNEY.md has 0 scraping-specific entries.")
        print("  Nearest domain: 14.3 (self-healing/aura failures) — not scraping logic.")

driver.close()
