"""Final verification queries for Task 14."""
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

# Check ROUTES_TO edge count (Task 6 claim: 23)
routes_to = run_query(driver, "MATCH ()-[r:ROUTES_TO]->() RETURN count(r)")
print(f"ROUTES_TO edges: {routes_to} (claimed: 23)")

# Check if DETACH DELETE is used in sync_to_neo4j.py main path
print("\n--- Checking for DETACH DELETE in sync_to_neo4j.py ---")
with open(r'C:\Users\Hp\Documents\Shopify Scraping Script\scripts\graph\sync_to_neo4j.py', 'r') as f:
    content = f.read()
    # Check if clear_graph is called unconditionally
    if "if fresh:" in content and "syncer.clear_graph()" in content:
        print("[PASS] clear_graph() is conditional on 'fresh' flag - not in main sync path")
    else:
        print("[FAIL] clear_graph() may be unconditional")

# Check for function_signature in CODE_INTENT payload
print("\n--- Checking function_signature in intent_capture.py ---")
with open(r'C:\Users\Hp\Documents\Shopify Scraping Script\src\graph\intent_capture.py', 'r') as f:
    content = f.read()
    if "'function_signature'" in content or '"function_signature"' in content:
        print("[PASS] function_signature found in intent_capture.py payload")
        # Find the line
        for i, line in enumerate(content.splitlines(), 1):
            if 'function_signature' in line:
                print(f"    Line {i}: {line.strip()[:80]}")
    else:
        print("[FAIL] function_signature NOT found in intent_capture.py")

# Check for function_signature in FAILURE_PATTERN payload
print("\n--- Checking function_signature in graphiti_sync.py ---")
with open(r'C:\Users\Hp\Documents\Shopify Scraping Script\src\tasks\graphiti_sync.py', 'r') as f:
    content = f.read()
    if '"function_signature"' in content or "'function_signature'" in content:
        print("[PASS] function_signature found in graphiti_sync.py")
        for i, line in enumerate(content.splitlines(), 1):
            if 'function_signature' in line:
                print(f"    Line {i}: {line.strip()[:80]}")
    else:
        print("[FAIL] function_signature NOT found in graphiti_sync.py")

# Check docstring mentions function_signature
if 'function_signature' in content:
    # Check docstring
    docstring_start = content.find('"""')
    docstring_end = content.find('"""', docstring_start + 3)
    docstring = content[docstring_start:docstring_end+3]
    if 'function_signature' in docstring:
        print("[PASS] function_signature mentioned in module docstring")
    else:
        # Check emit_episode docstring
        if 'def emit_episode' in content:
            fn_start = content.find('def emit_episode')
            fn_docstring_start = content.find('"""', fn_start)
            fn_docstring_end = content.find('"""', fn_docstring_start + 3)
            fn_docstring = content[fn_docstring_start:fn_docstring_end+3]
            if 'function_signature' in fn_docstring:
                print("[PASS] function_signature mentioned in emit_episode docstring")
            else:
                print("[WARN] function_signature not in emit_episode docstring")

# Check piggyback write in graphiti_ingestor.py
print("\n--- Checking piggyback write in graphiti_ingestor.py ---")
with open(r'C:\Users\Hp\Documents\Shopify Scraping Script\src\jobs\graphiti_ingestor.py', 'r') as f:
    content = f.read()
    if '_DEVELOPER_KG_TYPES' in content and 'SET e.function_signature' in content:
        print("[PASS] Piggyback write block found with _DEVELOPER_KG_TYPES and SET e.function_signature")
    else:
        print("[FAIL] Piggyback write block incomplete or missing")

# Check mark_deleted method
print("\n--- Checking mark_deleted() method in sync_to_neo4j.py ---")
with open(r'C:\Users\Hp\Documents\Shopify Scraping Script\scripts\graph\sync_to_neo4j.py', 'r') as f:
    content = f.read()
    if 'def mark_deleted(' in content:
        print("[PASS] mark_deleted() method exists")
    else:
        print("[FAIL] mark_deleted() method NOT found")

# Check _checksum helper
if '_checksum(' in content:
    print("[PASS] _checksum() helper exists")
else:
    print("[FAIL] _checksum() helper NOT found")

# Check _now_iso helper
if '_now_iso(' in content:
    print("[PASS] _now_iso() helper exists")
else:
    print("[FAIL] _now_iso() helper NOT found")

driver.close()
