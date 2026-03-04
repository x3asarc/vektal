#!/usr/bin/env python3
"""Test script to verify graph-first context retrieval is working."""

import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from src.assistant.context_broker import get_context

# Enable debug logging
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')

def test_graph_context():
    """Test that graph is used for context retrieval."""

    print("Testing graph-first context retrieval...\n")

    # Test query - looking for files related to embeddings
    query = "files that handle embeddings"

    print(f"Query: {query}\n")

    bundle = get_context(query, top_k=5, max_tokens=1000)

    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"\nQuery Class: {bundle.query_class}")
    print(f"\nTelemetry:")
    for key, value in bundle.telemetry.items():
        print(f"  {key}: {value}")

    print(f"\nSnippets Found: {len(bundle.snippets)}")
    print(f"\nContext Preview (first 500 chars):")
    print(bundle.output_text[:500])
    print("...\n")

    print(f"\nProvenance:")
    for prov in bundle.provenance[:3]:  # Show first 3
        print(f"  - Source: {prov['source']}, Path: {prov['path']}")

    print("\n" + "=" * 70)

    # Check if graph was actually used
    if bundle.telemetry.get("graph_used"):
        print("[SUCCESS] Graph was used as primary context source!")
    else:
        print("[FAILED] Graph was not used")
        if bundle.telemetry.get("fallback_reason"):
            print(f"   Fallback reason: {bundle.telemetry['fallback_reason']}")

    print("=" * 70)

if __name__ == "__main__":
    test_graph_context()
