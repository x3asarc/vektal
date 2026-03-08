"""Find pico-warden implementation functions + LongTermPattern domains + USES_SKILL gap closure."""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from dotenv import load_dotenv
from neo4j import GraphDatabase
load_dotenv()

uri  = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME", "neo4j")
pwd  = os.getenv("NEO4J_PASSWORD")
driver = GraphDatabase.driver(uri, auth=(user, pwd))

print("=== Pico-Warden implementation functions ===")
WARDEN_TERMS = ['infra_probe', 'probe_aura', 'orchestrate_heal', 'neo4j_health',
                'sync_remediator', 'backend_resolver', 'runtime_backend', 'remediator',
                'orchestrate', 'heal', 'probe']

with driver.session() as s:
    for term in WARDEN_TERMS:
        rows = s.run("""
            MATCH (f:Function) WHERE f.EndDate IS NULL
              AND (toLower(f.function_signature) CONTAINS $t
                   OR toLower(f.file_path) CONTAINS $t)
            RETURN f.function_signature AS sig, f.file_path AS fp, f.StartDate AS sd
            LIMIT 5
        """, t=term).data()
        if rows:
            print(f"\n  term='{term}': {len(rows)} hit(s)")
            for r in rows:
                print(f"    {r['sig']}")
                print(f"    file: {r['fp']}  synced: {str(r['sd'])[:19] if r['sd'] else 'N/A'}")

print()
print("=== All LongTermPattern entries (full detail) ===")
with driver.session() as s:
    all_ltp = s.run("""
        MATCH (lp:LongTermPattern)
        RETURN lp.domain AS domain, lp.task_id AS task_id,
               lp.description AS desc, lp.StartDate AS recorded_at,
               lp.source AS source
        ORDER BY lp.StartDate DESC
    """).data()
    for lp in all_ltp:
        print(f"\n  [{lp['domain']}] {lp['task_id']}")
        print(f"  recorded: {lp['recorded_at']}")
        print(f"  source:   {lp['source']}")
        print(f"  desc:     {(lp['desc'] or '')[:200]}")

print()
print("=== Create USES_SKILL edge: forensic-lead -> pico-warden ===")
with driver.session() as s:
    result = s.run("""
        MATCH (a:AgentDef {agent_id: '4eab1519698a'})
        MATCH (sk:SkillDef) WHERE sk.name = 'pico-warden'
        MERGE (a)-[r:USES_SKILL]->(sk)
        RETURN type(r) AS rel, a.name AS agent, sk.name AS skill
    """).data()
    if result:
        r = result[0]
        print(f"  Created: ({r['agent']})-[:USES_SKILL]->({r['skill']})")
    else:
        print("  [WARN] Could not create edge — agent or skill not found")

print()
print("=== SentryIssue: any touching remediator/healer modules ===")
with driver.session() as s:
    sentry_warden = s.run("""
        MATCH (si:SentryIssue)
        WHERE si.resolved = false
          AND (si.culprit CONTAINS 'remediator'
               OR si.culprit CONTAINS 'orchestrate'
               OR si.culprit CONTAINS 'heal'
               OR si.culprit CONTAINS 'graphiti_client'
               OR si.culprit CONTAINS 'neo4j'
               OR toLower(si.title) CONTAINS 'timeout'
               OR toLower(si.title) CONTAINS 'unavailabl')
        RETURN si.issue_id, si.title, si.category, si.culprit, si.timestamp
        ORDER BY si.timestamp DESC
    """).data()
    if sentry_warden:
        print(f"  Found {len(sentry_warden)} relevant Sentry issues:")
        for r in sentry_warden:
            print(f"  [{r['si.category']}] {r['si.title']}")
            print(f"  culprit: {r['si.culprit']}  at: {r['si.timestamp']}")
    else:
        print("  No Sentry issues matching warden/healer modules.")
        all_sentry = s.run("MATCH (si:SentryIssue) RETURN si.issue_id, si.title, si.category, si.resolved, si.culprit").data()
        print(f"  All {len(all_sentry)} SentryIssue nodes:")
        for r in all_sentry:
            status = "RESOLVED" if r['si.resolved'] else "UNRESOLVED"
            print(f"  [{status}] [{r['si.category']}] {r['si.title']}  culprit: {r['si.culprit']}")

driver.close()
