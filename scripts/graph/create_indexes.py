"""Task 12a: Create 9 composite indexes specified in research-v2-analysis.md."""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from dotenv import load_dotenv
from scripts.graph.sync_to_neo4j import Neo4jCodebaseSync
load_dotenv()

INDEXES = [
    # Current-state filter — used in every query
    ("function_active",
     "FOR (f:Function) ON (f.function_signature, f.EndDate)"),
    # Sentry issue lookup
    ("sentry_unresolved",
     "FOR (s:SentryIssue) ON (s.resolved, s.timestamp)"),
    # Episode bridge traversal
    ("episode_type_sig",
     "FOR (e:Episodic) ON (e.episode_type, e.function_signature)"),
    # EnvVar config lookup
    ("envvar_name",
     "FOR (e:EnvVar) ON (e.name)"),
    # Table access lookup
    ("table_name",
     "FOR (t:Table) ON (t.name)"),
    # APIRoute lookup
    ("apiroute_url",
     "FOR (a:APIRoute) ON (a.url_template)"),
    # TaskExecution model tracking (Commander layer — Task 13)
    ("taskexec_type_model",
     "FOR (te:TaskExecution) ON (te.task_type, te.model_used)"),
    # LongTermPattern semantic search (domain filter before embedding)
    ("longterm_domain",
     "FOR (p:LongTermPattern) ON (p.domain, p.EndDate)"),
    # ImprovementProposal queue (Infrastructure Lead reads this every session)
    ("improvement_status",
     "FOR (ip:ImprovementProposal) ON (ip.status, ip.created_at)"),
]


def main():
    print("=== Task 12a: Composite Indexes ===\n")
    syncer = Neo4jCodebaseSync()
    try:
        created = 0
        skipped = 0
        with syncer.driver.session() as session:
            for name, spec in INDEXES:
                try:
                    session.run(f"CREATE INDEX {name} IF NOT EXISTS {spec}")
                    print(f"  [OK] {name}")
                    created += 1
                except Exception as e:
                    # Composite indexes need Neo4j 4.4+ — check for version issues
                    print(f"  [WARN] {name}: {e}")
                    skipped += 1

        # Verify by listing indexes
        with syncer.driver.session() as session:
            result = session.run("SHOW INDEXES YIELD name, type, state WHERE state = 'ONLINE'")
            online = [r['name'] for r in result]

        our_indexes = [n for n, _ in INDEXES]
        verified = [n for n in our_indexes if n in online]

        print(f"\nResults:")
        print(f"  Created/confirmed: {len(verified)}/{len(INDEXES)}")
        if len(verified) < len(INDEXES):
            missing = [n for n in our_indexes if n not in online]
            print(f"  Not yet online: {missing}")
        print(f"\n[OK] Task 12a complete")
    finally:
        syncer.close()


if __name__ == "__main__":
    main()
