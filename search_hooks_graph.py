import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

uri = os.getenv('NEO4J_URI')
user = os.getenv('NEO4J_USER', 'neo4j')
password = os.getenv('NEO4J_PASSWORD')

def search_hooks():
    print(f"Connecting to Graph: {uri}")
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        # Search for nodes or properties containing "TaskCreate", "TaskUpdate", or "hook"
        cypher = """
        MATCH (n)
        WHERE n.name CONTAINS 'Task' OR n.summary CONTAINS 'Task' OR n.content CONTAINS 'Task'
           OR n.name CONTAINS 'hook' OR n.summary CONTAINS 'hook'
        RETURN n.name as name, labels(n) as labels, n.summary as summary, n.content as content
        LIMIT 20
        """
        result = session.run(cypher)
        records = list(result)
        
        print(f"\n--- Graph Hook Search ({len(records)} nodes found) ---")
        for record in records:
            print(f"Node: {record['name']} (Labels: {record['labels']})")
            if record['summary']:
                print(f"  Summary: {record['summary'][:150]}...")
            if record['content']:
                print(f"  Content: {record['content'][:150]}...")
            print("-" * 50)
            
    driver.close()

if __name__ == "__main__":
    try:
        search_hooks()
    except Exception as e:
        print(f"Error: {e}")
