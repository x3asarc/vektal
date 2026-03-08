"""Final sections: Sentry + LTP + drift."""
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

IMPL_FILES = [
    "src/graph/infra_probe.py",
    "src/graph/backend_resolver.py",
    "src/graph/orchestrate_healers.py",
]

with driver.session() as s:
    print("=== Sentry: direct function match ===")
    d = s.run("""
        MATCH (si:SentryIssue)-[:OCCURRED_IN]->(f:Function)
        WHERE f.function_signature IN $sigs
        RETURN si.issue_id AS id, si.title, si.category, si.resolved, f.function_signature AS fn
    """, sigs=IMPL_SIGS).data()
    print(f"  OCCURRED_IN hits: {len(d)}")
    for r in d:
        print(f"    [{r['si.category']}] {r['si.title']}  fn:{r['fn']}")

    print()
    print("=== Sentry: file-level match ===")
    d2 = s.run("""
        MATCH (si:SentryIssue)-[:REPORTED_IN]->(f:File)
        WHERE f.path IN $files
        RETURN si.issue_id AS id, si.title, si.category, si.resolved,
               si.culprit AS culprit, f.path AS fpath
    """, files=IMPL_FILES).data()
    print(f"  REPORTED_IN hits: {len(d2)}")
    for r in d2:
        flag = "RESOLVED" if r["resolved"] else "UNRESOLVED"
        print(f"    [{flag}][{r['si.category']}] {r['si.title']}  file:{r['fpath']}")

    print()
    print("=== All SentryIssue nodes ===")
    all_si = s.run("""
        MATCH (si:SentryIssue)
        RETURN si.issue_id AS id, si.title AS title, si.category AS cat,
               si.resolved AS resolved, si.culprit AS culprit
        ORDER BY si.timestamp DESC
    """).data()
    for r in all_si:
        flag = "RESOLVED" if r["resolved"] else "UNRESOLVED"
        print(f"  [{flag}][{r['cat']}] {r['title']}")
        print(f"    culprit: {r['culprit']}")

    print()
    print("=== LongTermPattern 14.3 (self-healing, nearest to scraping-stability) ===")
    ltp = s.run("""
        MATCH (lp:LongTermPattern) WHERE lp.domain = '14.3'
        RETURN lp.domain, lp.task_id, lp.description, lp.StartDate
        ORDER BY lp.StartDate DESC
    """).data()
    print(f"  14.3 entries: {len(ltp)}")
    last_ltp_date = None
    for lp in ltp:
        print(f"  {lp['lp.task_id']}  recorded:{str(lp['lp.StartDate'])[:10]}")
        print(f"    {(lp['lp.description'] or '')[:160]}")
        if not last_ltp_date:
            last_ltp_date = lp['lp.StartDate']

    print()
    print("=== Drift: impl functions updated after last 14.3 LTP ===")
    if last_ltp_date:
        print(f"  Anchor: {last_ltp_date}")
        drifted = s.run("""
            MATCH (f:Function) WHERE f.EndDate IS NULL
              AND f.function_signature IN $sigs
              AND f.StartDate > $anchor
            RETURN f.function_signature AS sig, f.StartDate AS updated
            ORDER BY f.StartDate DESC
        """, sigs=IMPL_SIGS, anchor=str(last_ltp_date)).data()
        stable = s.run("""
            MATCH (f:Function) WHERE f.EndDate IS NULL
              AND f.function_signature IN $sigs
              AND f.StartDate <= $anchor
            RETURN f.function_signature AS sig, f.StartDate AS sd
            ORDER BY f.StartDate DESC
        """, sigs=IMPL_SIGS, anchor=str(last_ltp_date)).data()
        print(f"  DRIFTED: {len(drifted)}")
        for r in drifted:
            print(f"    [DRIFT] {r['sig']}  at {r['updated']}")
        print(f"  STABLE:  {len(stable)}")
        for r in stable:
            print(f"    [OK]    {r['sig']}  synced:{str(r['sd'])[:19]}")
    else:
        print("  No 14.3 anchor.")

    print()
    print("=== scraping-logic-stability domain: confirmed gap ===")
    scraping = s.run("""
        MATCH (lp:LongTermPattern)
        WHERE toLower(lp.description) CONTAINS 'scrap'
           OR lp.domain CONTAINS 'scrap'
        RETURN count(lp) AS c
    """).single()["c"]
    print(f"  LongTermPattern entries mentioning 'scrap': {scraping}")
    if scraping == 0:
        print("  CONFIRMED GAP: domain 'scraping-logic-stability' does not exist in graph.")
        print("  Existing domains: 07.1 (governance), 14.3 (self-healing), learnings")

driver.close()
