"""
Task 14: Independent Forensic Verification Script
Verifies all claims from Tasks 5-13 of the Developer Knowledge Graph sprint.
"""
import os
import sys
from datetime import datetime

# Setup path and load env
sys.path.insert(0, r'C:\Users\Hp\Documents\Shopify Scraping Script')
from dotenv import load_dotenv
load_dotenv(r'C:\Users\Hp\Documents\Shopify Scraping Script\.env')

from neo4j import GraphDatabase

def get_driver():
    uri = os.getenv('NEO4J_URI')
    user = os.getenv('NEO4J_USER') or os.getenv('NEO4J_USERNAME', 'neo4j')
    pwd = os.getenv('NEO4J_PASSWORD')
    if not uri or not pwd:
        raise ValueError("NEO4J_URI and NEO4J_PASSWORD must be set")
    return GraphDatabase.driver(uri, auth=(user, pwd))

def run_query(driver, query, description=""):
    """Run a single Cypher query and return the result."""
    with driver.session() as session:
        result = session.run(query)
        record = result.single()
        if record:
            return record[0]
        return None

def run_query_multi(driver, query):
    """Run a query that returns multiple columns."""
    with driver.session() as session:
        result = session.run(query)
        return [dict(record) for record in result]

def main():
    print("=" * 70)
    print("TASK 14: INDEPENDENT FORENSIC VERIFICATION")
    print(f"Date: {datetime.utcnow().isoformat()}Z")
    print("Backend: Aura")
    print("=" * 70)
    
    driver = get_driver()
    
    # SECTION 1: NODE COUNTS
    print("\n" + "=" * 70)
    print("SECTION 1: AURA NODE/EDGE COUNTS")
    print("-" * 70)
    
    claims = {
        'Function (active)': {'claimed': 2154, 'query': "MATCH (n:Function) WHERE n.EndDate IS NULL RETURN count(n)"},
        'Class (active)': {'claimed': 669, 'query': "MATCH (n:Class) WHERE n.EndDate IS NULL RETURN count(n)"},
        'File (active)': {'claimed': 634, 'query': "MATCH (n:File) WHERE n.EndDate IS NULL RETURN count(n)"},
        'APIRoute': {'claimed': 109, 'query': "MATCH (n:APIRoute) RETURN count(n)"},
        'CeleryTask': {'claimed': 23, 'query': "MATCH (n:CeleryTask) RETURN count(n)"},
        'Queue': {'claimed': 12, 'query': "MATCH (n:Queue) RETURN count(n)"},
        'EnvVar': {'claimed': 91, 'query': "MATCH (n:EnvVar) RETURN count(n)"},
        'Table': {'claimed': 45, 'query': "MATCH (n:Table) RETURN count(n)"},
        'AgentDef': {'claimed': 25, 'query': "MATCH (n:AgentDef) RETURN count(n)"},
        'SkillDef': {'claimed': 4, 'query': "MATCH (n:SkillDef) RETURN count(n)"},
        'LongTermPattern': {'claimed': 22, 'query': "MATCH (n:LongTermPattern) RETURN count(n)"},
        'SentryIssue': {'claimed': 2, 'query': "MATCH (n:SentryIssue) RETURN count(n)", 'min_check': True},
    }
    
    print(f"{'Node Type':<25} {'Claimed':>10} {'Actual':>10} {'Delta':>10} {'Status':>10}")
    print("-" * 70)
    
    node_results = {}
    for name, info in claims.items():
        actual = run_query(driver, info['query'])
        claimed = info['claimed']
        delta = actual - claimed if actual is not None else 'N/A'
        
        if actual is None:
            status = "ERROR"
        elif info.get('min_check'):
            status = "PASS" if actual >= claimed else "FAIL"
        else:
            pct_diff = abs(actual - claimed) / claimed * 100 if claimed > 0 else 0
            if pct_diff <= 5:
                status = "PASS"
            elif pct_diff <= 10:
                status = "WARN"
            else:
                status = "FAIL"
        
        node_results[name] = {'claimed': claimed, 'actual': actual, 'delta': delta, 'status': status}
        print(f"{name:<25} {claimed:>10} {str(actual):>10} {str(delta):>10} {status:>10}")
    
    # EDGE COUNTS
    print("\n--- Edge Counts ---")
    edge_claims = {
        'CALLS': {'claimed': 2128, 'query': "MATCH ()-[r:CALLS]->() RETURN count(r)"},
        'TRIGGERS': {'claimed': 113, 'query': "MATCH ()-[r:TRIGGERS]->() RETURN count(r)"},
        'QUEUED_ON': {'claimed': 23, 'query': "MATCH ()-[r:QUEUED_ON]->() RETURN count(r)"},
        'DEPENDS_ON_CONFIG': {'claimed': 74, 'query': "MATCH ()-[r:DEPENDS_ON_CONFIG]->() RETURN count(r)"},
        'ACCESSES': {'claimed': 173, 'query': "MATCH ()-[r:ACCESSES]->() RETURN count(r)"},
        'OCCURRED_IN': {'claimed': 1, 'query': "MATCH ()-[r:OCCURRED_IN]->() RETURN count(r)", 'min_check': True},
        'REPORTED_IN': {'claimed': 4, 'query': "MATCH ()-[r:REPORTED_IN]->() RETURN count(r)", 'min_check': True},
    }
    
    print(f"{'Edge Type':<25} {'Claimed':>10} {'Actual':>10} {'Delta':>10} {'Status':>10}")
    print("-" * 70)
    
    edge_results = {}
    for name, info in edge_claims.items():
        actual = run_query(driver, info['query'])
        claimed = info['claimed']
        delta = actual - claimed if actual is not None else 'N/A'
        
        if actual is None:
            status = "ERROR"
        elif info.get('min_check'):
            status = "PASS" if actual >= claimed else "FAIL"
        else:
            pct_diff = abs(actual - claimed) / claimed * 100 if claimed > 0 else 0
            if pct_diff <= 5:
                status = "PASS"
            elif pct_diff <= 10:
                status = "WARN"
            else:
                status = "FAIL"
        
        edge_results[name] = {'claimed': claimed, 'actual': actual, 'delta': delta, 'status': status}
        print(f"{name:<25} {claimed:>10} {str(actual):>10} {str(delta):>10} {status:>10}")
    
    # SECTION 2: BI-TEMPORAL COVERAGE
    print("\n" + "=" * 70)
    print("SECTION 2: BI-TEMPORAL COVERAGE (Task 9)")
    print("-" * 70)
    
    bitemporal_queries = {
        'Function missing StartDate': "MATCH (f:Function) WHERE f.EndDate IS NULL AND f.StartDate IS NULL RETURN count(f)",
        'Function missing checksum': "MATCH (f:Function) WHERE f.EndDate IS NULL AND f.checksum IS NULL RETURN count(f)",
        'File missing StartDate': "MATCH (f:File) WHERE f.EndDate IS NULL AND f.StartDate IS NULL RETURN count(f)",
        'Class missing StartDate': "MATCH (c:Class) WHERE c.EndDate IS NULL AND c.StartDate IS NULL RETURN count(c)",
    }
    
    bitemporal_results = {}
    for name, query in bitemporal_queries.items():
        actual = run_query(driver, query)
        status = "PASS" if actual == 0 else "FAIL"
        bitemporal_results[name] = {'count': actual, 'status': status}
        print(f"{name}: {actual} -- {status}")
    
    # SECTION 3: INDEXES
    print("\n" + "=" * 70)
    print("SECTION 3: INDEX STATUS (Task 12)")
    print("-" * 70)
    
    index_count = run_query(driver, "SHOW INDEXES YIELD name, state WHERE state = 'ONLINE' RETURN count(name)")
    print(f"Online indexes: {index_count} (expected >= 9)")
    
    indexes = run_query_multi(driver, "SHOW INDEXES YIELD name, state, type RETURN name, state, type ORDER BY name")
    print("\nIndex Details:")
    for idx in indexes:
        print(f"  - {idx['name']}: {idx['state']} ({idx['type']})")
    
    # SECTION 4: SCHEMA INTEGRITY
    print("\n" + "=" * 70)
    print("SECTION 4: SCHEMA INTEGRITY")
    print("-" * 70)
    
    schema_queries = {
        'Function missing function_signature': "MATCH (f:Function) WHERE f.EndDate IS NULL AND f.function_signature IS NULL RETURN count(f)",
        'EnvVar missing risk_tier': "MATCH (e:EnvVar) WHERE e.risk_tier IS NULL RETURN count(e)",
        'Table missing name': "MATCH (t:Table) WHERE t.name IS NULL RETURN count(t)",
        'CeleryTask missing queue': "MATCH (ct:CeleryTask) WHERE ct.queue IS NULL OR ct.queue = '' RETURN count(ct)",
    }
    
    schema_results = {}
    for name, query in schema_queries.items():
        actual = run_query(driver, query)
        schema_results[name] = actual
        print(f"{name}: {actual}")
    
    # SECTION 5: ENVOAR RISK TIERS
    print("\n--- EnvVar Risk Tier Distribution ---")
    tier_dist = run_query_multi(driver, "MATCH (e:EnvVar) RETURN e.risk_tier as tier, count(e) as count ORDER BY tier")
    for row in tier_dist:
        print(f"  {row['tier']}: {row['count']}")
    
    # SECTION 6: BLAST RADIUS SANITY CHECK
    print("\n" + "=" * 70)
    print("SECTION 5: FORENSIC QUERY (BLAST RADIUS)")
    print("-" * 70)
    
    blast_query = """
    MATCH (caller:Function)-[:CALLS]->(callee:Function {name: 'emit_episode'})
    WHERE caller.EndDate IS NULL AND callee.EndDate IS NULL
    OPTIONAL MATCH (caller)-[:DEPENDS_ON_CONFIG]->(e:EnvVar)
    RETURN caller.function_signature as caller_sig, collect(e.name) as config_deps
    LIMIT 10
    """
    
    blast_results = run_query_multi(driver, blast_query)
    print("Who calls emit_episode and what config does it depend on?")
    for row in blast_results:
        print(f"  {row['caller_sig']}: deps={row['config_deps']}")
    
    if not blast_results:
        print("  (No results - emit_episode may not exist or no callers)")
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    # Count failures
    node_failures = [k for k, v in node_results.items() if v['status'] in ('FAIL', 'ERROR')]
    edge_failures = [k for k, v in edge_results.items() if v['status'] in ('FAIL', 'ERROR')]
    bitemporal_failures = [k for k, v in bitemporal_results.items() if v['status'] == 'FAIL']
    
    total_failures = len(node_failures) + len(edge_failures) + len(bitemporal_failures)
    
    if total_failures == 0:
        verdict = "GREEN"
    elif total_failures <= 3:
        verdict = "DEGRADED"
    else:
        verdict = "RED"
    
    print(f"Node count issues: {node_failures if node_failures else 'None'}")
    print(f"Edge count issues: {edge_failures if edge_failures else 'None'}")
    print(f"Bi-temporal issues: {bitemporal_failures if bitemporal_failures else 'None'}")
    print(f"\nOVERALL VERDICT: {verdict}")
    
    driver.close()
    return verdict

if __name__ == "__main__":
    main()
