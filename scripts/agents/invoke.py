"""
scripts/agents/invoke.py — Direct OpenRouter agent runner.

Calls any agent spec via OpenRouter directly, bypassing CLI model proxies.
Uses model assignments from docs/agent-system/model-rationale.md.

Usage:
    python scripts/agents/invoke.py --agent commander --message "run infrastructure-audit"
    python scripts/agents/invoke.py --agent watson --message "review this blast radius" --context "..."
    python scripts/agents/invoke.py --agent commander --message "..." --model x-ai/grok-3
    python scripts/agents/invoke.py --list

Environment:
    OPENROUTER_API_KEY  required
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Confirmed real OpenRouter model IDs — source of truth
# Keep in sync with docs/agent-system/model-rationale.md
MODEL_MAP: dict[str, str] = {
    "watson":               "anthropic/claude-opus-4-6",
    "commander":            "x-ai/grok-3",
    "forensic-lead":        "deepseek/deepseek-v3.2",
    "design-lead":          "moonshotai/kimi-k2.5",
    "task-observer":        "google/gemini-2.5-flash-lite",
    "bundle":               "google/gemini-2.5-flash",
    "engineering-lead":     "openai/gpt-4o",
    "infrastructure-lead":  "z-ai/glm-4.6",
    "project-lead":         "google/gemini-2.5-flash",
    "validator":            "openai/gpt-4o-mini",
    "gsd-executor":         "openai/gpt-4o",
    "gsd-planner":          "openai/gpt-4o",
}

# Agent spec directories in priority order
SPEC_DIRS = [
    ROOT / ".claude" / "agents",
    ROOT / ".codex" / "agents",
    ROOT / ".gemini" / "agents",
    ROOT / ".letta" / "agents",
]


def _load_spec(agent_name: str) -> str:
    """Load agent system prompt from spec file, stripping YAML frontmatter."""
    for spec_dir in SPEC_DIRS:
        spec_file = spec_dir / f"{agent_name}.md"
        if spec_file.exists():
            content = spec_file.read_text(encoding="utf-8")
            # Strip YAML frontmatter (--- ... ---)
            if content.startswith("---"):
                end = content.find("---", 3)
                if end != -1:
                    content = content[end + 3:].lstrip("\n")
            return content
    raise FileNotFoundError(f"No spec file found for agent '{agent_name}'")


def invoke(
    agent: str,
    message: str,
    context: str = "",
    model: str = "",
    temperature: float | None = None,
    max_tokens: int = 4096,
    stream: bool = False,
) -> str:
    """Invoke an agent via OpenRouter. Returns the response text."""
    if not OPENROUTER_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not set in .env")

    model = model or MODEL_MAP.get(agent, "openai/gpt-4o")
    system_prompt = _load_spec(agent)

    messages = [{"role": "system", "content": system_prompt}]
    if context:
        messages.append({"role": "user", "content": f"Context:\n{context}"})
    messages.append({"role": "user", "content": message})

    # Sensible temperature defaults per agent tier
    if temperature is None:
        temperature = {
            "watson": 0.2,
            "commander": 0.7,
            "forensic-lead": 0.0,
            "validator": 0.3,
        }.get(agent, 0.5)

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": stream,
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/vektal",
        "X-Title": f"Vektal/{agent}",
    }

    resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Invoke a Vektal agent via OpenRouter")
    parser.add_argument("--agent", "-a", help="Agent name (e.g. commander, watson)")
    parser.add_argument("--message", "-m", help="User message / task")
    parser.add_argument("--context", "-c", default="", help="Optional context block")
    parser.add_argument("--model", default="", help="Override model ID")
    parser.add_argument("--temperature", type=float, default=None)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--list", action="store_true", help="List agents and their models")
    args = parser.parse_args()

    if args.list:
        print("\nAgent → OpenRouter Model")
        print("─" * 55)
        for name, mdl in sorted(MODEL_MAP.items()):
            print(f"  {name:<22} {mdl}")
        return

    if not args.agent or not args.message:
        parser.error("--agent and --message are required")

    try:
        result = invoke(
            agent=args.agent,
            message=args.message,
            context=args.context,
            model=args.model,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )
        print(result)
    except requests.HTTPError as e:
        print(f"OpenRouter error: {e.response.status_code} {e.response.text[:300]}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
