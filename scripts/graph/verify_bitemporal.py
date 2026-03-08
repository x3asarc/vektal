"""Task 9 verification: confirm StartDate/EndDate/checksum on nodes in Aura."""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from dotenv import load_dotenv
from scripts.graph.sync_to_neo4j import Neo4jCodebaseSync
load_dotenv()

syncer = Neo4jCodebaseSync()
try:
    with syncer.driver.session() as session:
        # Check Function nodes
        r = session.run("""
            MATCH (f:Function) WHERE f.EndDate IS NULL
            RETURN count(f) as current,
                   count(f.StartDate) as with_start,
                   count(f.checksum) as with_checksum
        """).single()
        print(f"Function nodes (current, EndDate IS NULL):")
        print(f"  Total:         {r['current']}")
        print(f"  With StartDate:{r['with_start']}")
        print(f"  With checksum: {r['with_checksum']}")

        r_del = session.run("""
            MATCH (f:Function) WHERE f.EndDate IS NOT NULL
            RETURN count(f) as c
        """).single()
        print(f"  Deleted (EndDate set): {r_del['c']}")

        # Sample one node
        sample = session.run("""
            MATCH (f:Function) WHERE f.EndDate IS NULL AND f.StartDate IS NOT NULL
            RETURN f.full_name, f.StartDate, f.checksum LIMIT 1
        """).single()
        if sample:
            print(f"\nSample: {sample['f.full_name']}")
            print(f"  StartDate: {sample['f.StartDate']}")
            print(f"  checksum:  {sample['f.checksum']}")

        # Check File nodes
        rf = session.run("""
            MATCH (f:File) WHERE f.EndDate IS NULL
            RETURN count(f) as c, count(f.StartDate) as s, count(f.checksum) as ch
        """).single()
        print(f"\nFile nodes: {rf['c']} current, {rf['s']} with StartDate, {rf['ch']} with checksum")

        # Check Class nodes
        rc = session.run("""
            MATCH (c:Class) WHERE c.EndDate IS NULL
            RETURN count(c) as ct, count(c.StartDate) as s, count(c.checksum) as ch
        """).single()
        print(f"Class nodes: {rc['ct']} current, {rc['s']} with StartDate, {rc['ch']} with checksum")

finally:
    syncer.close()
