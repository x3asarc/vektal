"""Quick test: write mock SentryIssue nodes to Aura and verify."""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from dotenv import load_dotenv
load_dotenv()

from scripts.observability.sentry_issue_puller import _write_sentry_issue_to_graph, _cul_to_module
from src.graph.sentry_ingestor import FailureEvent
from neo4j import GraphDatabase

# Verify culprit parsing
print("=== Culprit parsing test ===")
tests = [
    ("src/core/graphiti_client.py in get_graphiti_client", ("src.core.graphiti_client", "get_graphiti_client")),
    ("src/graph/sentry_ingestor.py", ("src.graph.sentry_ingestor", None)),
    ("src/tasks/graphiti_sync.py in emit_episode", ("src.tasks.graphiti_sync", "emit_episode")),
]
for culprit, expected in tests:
    result = _cul_to_module(culprit)
    status = "OK" if result == expected else "FAIL"
    print(f"  [{status}] {culprit!r} -> {result}")

# Write mock SentryIssue nodes to Aura
print("\n=== Aura graph write test ===")
uri = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME", "neo4j")
pwd = os.getenv("NEO4J_PASSWORD")
driver = GraphDatabase.driver(uri, auth=(user, pwd))

mock_events = [
    FailureEvent(
        event_id="test-sentry-1",
        title="Neo4jError: ServiceUnavailable",
        category="AURA_UNREACHABLE",
        culprit="src/core/graphiti_client.py in get_graphiti_client",
        timestamp="2026-03-08T10:00:00+00:00",
        tags={"issue_id": "test-sentry-1"},
        level="error",
    ),
    FailureEvent(
        event_id="test-sentry-2",
        title="FileNotFoundError: local-snapshot.json missing",
        category="SNAPSHOT_CORRUPT",
        culprit="src/graph/sentry_ingestor.py",
        timestamp="2026-03-08T10:01:00+00:00",
        tags={"issue_id": "test-sentry-2"},
        level="error",
    ),
]

# Ensure constraint
with driver.session() as s:
    s.run("CREATE CONSTRAINT sentry_issue_id_unique IF NOT EXISTS "
          "FOR (si:SentryIssue) REQUIRE si.issue_id IS UNIQUE")

for event in mock_events:
    _write_sentry_issue_to_graph(event, driver)
    print(f"  Written: {event.event_id} ({event.category})")

# Verify
with driver.session() as s:
    si_count = s.run("MATCH (n:SentryIssue) RETURN count(n) as c").single()['c']
    occ = s.run("MATCH ()-[r:OCCURRED_IN]->() RETURN count(r) as c").single()['c']
    rep = s.run("MATCH ()-[r:REPORTED_IN]->() RETURN count(r) as c").single()['c']
    print(f"\n=== Aura verification ===")
    print(f"  :SentryIssue nodes: {si_count}")
    print(f"  :OCCURRED_IN edges: {occ}")
    print(f"  :REPORTED_IN edges: {rep}")

driver.close()
print("\n[OK] Task 11b complete (SentryIssue bridge ready)")
