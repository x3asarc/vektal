"""Quick check: duplicate AgentDef nodes and forensic-lead state."""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from dotenv import load_dotenv
from neo4j import GraphDatabase
load_dotenv()
driver = GraphDatabase.driver(os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME","neo4j"), os.getenv("NEO4J_PASSWORD")))
with driver.session() as s:
    dups = s.run("""
        MATCH (a:AgentDef)
        WITH a.name as name, collect(a.platform) as platforms, count(a) as cnt
        WHERE cnt > 1
        RETURN name, platforms, cnt
        ORDER BY name
    """).data()
    print("=== Duplicate AgentDef nodes ===")
    for d in dups:
        print(f"  {d['name']}: {d['platforms']} (cnt={d['cnt']})")
    if not dups:
        print("  None")
    all_agents = s.run("MATCH (a:AgentDef) RETURN count(a) as c").single()["c"]
    print(f"\nTotal AgentDef: {all_agents}")
    lu = s.run("MATCH (b)-[:LEVEL_UNDER]->(c:AgentDef) RETURN c.name as parent, collect(b.name) as children ORDER BY c.name").data()
    print("\n=== LEVEL_UNDER relationships ===")
    for row in lu:
        print(f"  {row['parent']} <- {row['children']}")
driver.close()
