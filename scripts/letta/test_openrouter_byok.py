"""Test openrouter-letta BYOK provider with claude-opus-4-6 on Watson."""
import os, json, requests, sys
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parents[2] / ".env")
BASE    = os.getenv("LETTA_BASE_URL", "https://api.letta.com")
KEY     = os.getenv("LETTA_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
reg     = json.loads((Path(__file__).parents[2] / ".letta/agent-registry.json").read_text())
wid     = reg["watson"]["id"]

# Test model candidates via openrouter-letta prefix
CANDIDATES = [
    "openrouter-letta/anthropic/claude-opus-4-6",
    "openrouter-letta/anthropic/claude-opus-4-5",
    "openrouter-letta/anthropic/claude-3.7-sonnet",
    "openrouter-letta/x-ai/grok-3",
]

for model in CANDIDATES:
    r = requests.patch(f"{BASE}/v1/agents/{wid}", headers=HEADERS,
                       json={"model": model}, timeout=10)
    if not r.ok:
        print(f"PATCH {model}: RED {r.status_code}")
        continue

    r2 = requests.post(f"{BASE}/v1/agents/{wid}/messages", headers=HEADERS, json={
        "messages": [{"role": "user", "content": "ping — respond with one word: pong"}],
        "stream_steps": False
    }, timeout=30)

    if r2.ok:
        for m in r2.json().get("messages", []):
            if m.get("message_type") == "assistant_message":
                print(f"GREEN  {model}")
                print(f"       Watson: {m['content'][:120]}")
                sys.exit(0)
    else:
        print(f"RED    {model} — {r2.status_code}: {r2.text[:120]}")
