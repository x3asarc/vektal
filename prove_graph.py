import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

uri = os.getenv('NEO4J_URI')
user = os.getenv('NEO4J_USER', 'neo4j')
password = os.getenv('NEO4J_PASSWORD')

def prove_graph_usage():
    print(f"Connecting to Graph: {uri}")
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        # Query for nodes related to "Webhook" to show the depth of the graph
        cypher = """
        MATCH (f:File)-[r]->(target)
        WHERE f.path CONTAINS 'webhook' OR target.name CONTAINS 'webhook'
        RETURN f.path as source, type(r) as relationship, target.name as target_node, target.summary as target_summary
        LIMIT 5
        """
        result = session.run(cypher)
        records = list(result)
        
        print(f"\n--- Graph Knowledge Proof ({len(records)} relationships found) ---")
        for record in records:
            print(f"Source: {record['source']}")
            print(f"  --[{record['relationship']}]--> {record['target_node']}")
            if record['target_summary']:
                print(f"  Summary: {record['target_summary'][:100]}...")
            print("-" * 30)
            
    driver.close()

if __name__ == "__main__":
    try:
        prove_graph_usage()
    except Exception as e:
        print(f"Error: {e}")
