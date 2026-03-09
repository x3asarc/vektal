"""Additional verification queries for Task 14."""
import os, sys
sys.path.insert(0, r'C:\Users\Hp\Documents\Shopify Scraping Script')
from dotenv import load_dotenv
load_dotenv(r'C:\Users\Hp\Documents\Shopify Scraping Script\.env')

from neo4j import GraphDatabase

def get_driver():
    uri = os.getenv('NEO4J_URI')
    user = os.getenv('NEO4J_USER') or os.getenv('NEO4J_USERNAME', 'neo4j')
    pwd = os.getenv('NEO4J_PASSWORD')
    return GraphDatabase.driver(uri, auth=(user, pwd))

def run_query(driver, query):
    with driver.session() as session:
        result = session.run(query)
        record = result.single()
        if record:
            return record[0]
        return None

def run_query_multi(driver, query):
    with driver.session() as session:
        result = session.run(query)
        return [dict(record) for record in result]

driver = get_driver()

# Check LongTermPattern discrepancy
print("=== LongTermPattern Investigation ===")
total_ltp = run_query(driver, "MATCH (n:LongTermPattern) RETURN count(n)")
print(f"Total LongTermPattern nodes in Aura: {total_ltp}")

# Check by source
by_source = run_query_multi(driver, "MATCH (n:LongTermPattern) RETURN n.source as source, count(n) as count ORDER BY source")
print("By source:")
for row in by_source:
    print(f"  {row['source']}: {row['count']}")

# Check SentryIssue details
print("\n=== SentryIssue Investigation ===")
sentry_issues = run_query_multi(driver, "MATCH (n:SentryIssue) RETURN n.issue_id, n.title, n.category LIMIT 10")
print(f"SentryIssue nodes found: {len(sentry_issues)}")
for si in sentry_issues:
    print(f"  {si['n.issue_id']}: {si['n.title'][:60]}...")

# Check edges from SentryIssue
occurred_in = run_query_multi(driver, """
    MATCH (si:SentryIssue)-[r:OCCURRED_IN]->(f:Function)
    RETURN si.issue_id, f.function_signature
""")
print(f"\nOCCURRED_IN edges: {len(occurred_in)}")
for e in occurred_in:
    print(f"  {e['si.issue_id']} -> {e['f.function_signature']}")

reported_in = run_query_multi(driver, """
    MATCH (si:SentryIssue)-[r:REPORTED_IN]->(f:File)
    RETURN si.issue_id, f.path
""")
print(f"\nREPORTED_IN edges: {len(reported_in)}")
for e in reported_in:
    print(f"  {e['si.issue_id']} -> {e['f.path']}")

# Check EnvVar risk tiers match claims
print("\n=== EnvVar Risk Tier Distribution ===")
tiers = run_query_multi(driver, """
    MATCH (e:EnvVar) 
    RETURN e.risk_tier as tier, count(e) as count 
    ORDER BY tier
""")
for row in tiers:
    print(f"  Tier {row['tier']}: {row['count']}")

# Check for any Function nodes without function_signature
print("\n=== Function function_signature Coverage ===")
missing_sig = run_query(driver, "MATCH (f:Function) WHERE f.EndDate IS NULL AND f.function_signature IS NULL RETURN count(f)")
print(f"Functions missing function_signature: {missing_sig}")

# Check if any Function has function_signature
with_sig = run_query(driver, "MATCH (f:Function) WHERE f.EndDate IS NULL AND f.function_signature IS NOT NULL RETURN count(f)")
print(f"Functions with function_signature: {with_sig}")

driver.close()
