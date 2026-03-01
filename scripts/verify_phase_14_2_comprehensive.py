import asyncio
import os
import sys
import json
import time

# Ensure absolute imports resolve
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.graph.mcp_server import dispatch_tool_call

async def verify_14_2():
    print("STARTING COMPREHENSIVE PHASE 14.2 VERIFICATION\n")
    os.environ["GRAPH_ORACLE_ENABLED"] = "true"
    os.environ["GRAPH_DISABLE_ASYNC_EMIT"] = "true"  # Bypass Redis

    # --- 1. Tool Discovery (Deferred Loading) ---
    print("TEST 1: Tool Discovery (Deferred Loading)")
    try:
        # Search for batch tools to verify they are discoverable
        discovery = await dispatch_tool_call('search_tools', {'query': 'batch operations'})
        tools = discovery.get("tools", [])
        names = [t['name'] for t in tools]
        print(f"Found tools: {names}")
        
        if "batch_query" in names and "batch_dependencies" in names:
            print("✅ Batch tools discovered successfully")
        else:
            print("⚠️ Batch tools NOT found in top results")
            
        # Verify fullSchema is present (critical for deferred loading)
        if tools and "fullSchema" in tools[0]:
            print("✅ fullSchema present in discovery result")
        else:
            print("❌ fullSchema MISSING in discovery result")
    except Exception as e:
        print(f"❌ Discovery failed: {e}")

    # --- 2. Batch Operations ---
    print("\nTEST 2: Batch Query & Dependencies")
    try:
        # Batch Query
        queries = [
            "who imports src/core/graphiti_client.py",
            "what calls src/graph/mcp_server.py",
            "find decisions about Neo4j"
        ]
        t0 = time.time()
        batch_q_res = await dispatch_tool_call('batch_query', {'queries': queries})
        dt = time.time() - t0
        print(f"Batch query (3 items) took {dt:.2f}s")
        print(f"Status: {batch_q_res.get('successful')} successful, {batch_q_res.get('failed')} failed")
        
        if batch_q_res.get('successful') == 3:
            print("✅ Batch query fully successful")
        else:
            print(f"⚠️ Batch query partial failure: {batch_q_res.get('errors')}")

        # Batch Dependencies
        files = [
            "src/core/graphiti_client.py",
            "src/graph/mcp_server.py"
        ]
        batch_d_res = await dispatch_tool_call('batch_dependencies', {'file_paths': files})
        print(f"Batch dependencies checked {batch_d_res.get('total_files')} files")
        if batch_d_res.get('successful') == 2:
            print("✅ Batch dependencies successful")
        else:
            print("⚠️ Batch dependencies partial failure")

    except Exception as e:
        print(f"❌ Batch operations failed: {e}")

    # --- 3. Compact Output ---
    print("\nTEST 3: Compact Output Mode")
    try:
        query = "find all files" # Broad query to get many results
        
        # Full mode
        full_res = await dispatch_tool_call('query_graph', {'query': query, 'compact_output': False})
        full_json = json.dumps(full_res)
        full_len = len(full_json)
        
        # Compact mode
        compact_res = await dispatch_tool_call('query_graph', {'query': query, 'compact_output': True})
        compact_json = json.dumps(compact_res)
        compact_len = len(compact_json)
        
        reduction = (full_len - compact_len) / full_len * 100
        print(f"Full size: {full_len} chars")
        print(f"Compact size: {compact_len} chars")
        print(f"Reduction: {reduction:.1f}%")
        
        if reduction > 10:
            print("✅ Compact mode significantly reduced output size")
        else:
            print("⚠️ Compact mode reduction minimal (check implementation)")
            
        # Verify structure
        if compact_res.get('results') and 'summary' in compact_res['results'][0]:
            print("✅ Compact results contain 'summary' field")
        else:
            print("❌ Compact results missing 'summary' field")

    except Exception as e:
        print(f"❌ Compact output test failed: {e}")

    # --- 4. External Research ---
    print("\nTEST 4: External Research (Perplexity)")
    try:
        # Use a specific technical query
        topic = "Python Neo4j driver connection timeout best practices"
        doc_res = await dispatch_tool_call('search_documentation', {'topic': topic})
        
        if doc_res.get('status') == 'success':
            print("✅ Perplexity search successful")
            print(f"Answer snippet: {doc_res.get('answer')[:100]}...")
            if doc_res.get('citations'):
                print(f"Citations present: {len(doc_res['citations'])}")
            else:
                print("⚠️ No citations returned")
        else:
            print(f"⚠️ Research failed or fell back: {doc_res}")

    except Exception as e:
        print(f"❌ External research failed: {e}")

    print("\nVERIFICATION COMPLETE")

if __name__ == "__main__":
    asyncio.run(verify_14_2())
