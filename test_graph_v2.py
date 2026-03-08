import os
from dotenv import load_dotenv
from src.assistant.context_broker import get_context

load_dotenv()
print(f"NEO4J_URI: {os.getenv('NEO4J_URI')}")
print(f"NEO4J_USER: {os.getenv('NEO4J_USER')}")
print(f"NEO4J_PASSWORD: {'SET' if os.getenv('NEO4J_PASSWORD') else 'NOT SET'}")

try:
    bundle = get_context('Shopify', top_k=5)
    print(f"\nGraph Used: {bundle.telemetry['graph_used']}")
    print(f"Fallback Reason: {bundle.telemetry['fallback_reason']}")
    print("\nSnippets:")
    for s in bundle.snippets:
        print(f"- {s}")
except Exception as e:
    print(f"Error: {e}")
