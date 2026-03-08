import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from dotenv import load_dotenv
load_dotenv()
from scripts.graph.sync_to_neo4j import Neo4jCodebaseSync
s = Neo4jCodebaseSync()
with s.driver.session() as sess:
    r = sess.run("SHOW INDEXES YIELD name, state ORDER BY name")
    for row in r:
        print(f"{row['state']:10s} {row['name']}")
s.close()
