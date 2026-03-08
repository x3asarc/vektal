from src.assistant.context_broker import get_context
import json

try:
    bundle = get_context('Shopify Webhook receiver', top_k=3)
    print(f"Graph Used: {bundle.telemetry['graph_used']}")
    print(f"Fallback Reason: {bundle.telemetry['fallback_reason']}")
    print("Snippets found:")
    for s in bundle.snippets:
        print(f"- {s}")
except Exception as e:
    print(f"Error: {e}")
