"""
scripts/letta/register_agents.py

Registers all Vektal agents in Letta Cloud via the REST API.
Reads system prompts from .letta/agents/*.md, creates agents,
writes agent IDs to .letta/agent-registry.json.

Usage:
    python scripts/letta/register_agents.py              # register all missing
    python scripts/letta/register_agents.py --force      # re-create all (delete + recreate)
    python scripts/letta/register_agents.py --list       # show registry
    python scripts/letta/register_agents.py --agent commander  # single agent only
"""

import os, sys, json, re, argparse, requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).parent.parent.parent
AGENTS_DIR = ROOT / ".letta" / "agents"
REGISTRY_FILE = ROOT / ".letta" / "agent-registry.json"

LETTA_BASE = os.getenv("LETTA_BASE_URL", "https://api.letta.com")
LETTA_KEY = os.getenv("LETTA_API_KEY", "")
HEADERS = {
    "Authorization": f"Bearer {LETTA_KEY}",
    "Content-Type": "application/json",
}

# ── Model assignments (METADATA ONLY — not used for inference) ────────────────
# ARCHITECTURE: Letta = memory store only. Inference = OpenRouter direct.
# These model IDs are stored as labels on AgentDef nodes in Aura and in the
# registry file. They document intent. They do NOT route inference calls.
#
# Inference happens when a CLI session invokes an agent:
#   - Claude Code  → uses Anthropic / OpenRouter via OPENROUTER_API_KEY
#   - Gemini CLI   → OPENAI_BASE_URL=https://openrouter.ai/api/v1
#   - Codex        → OPENAI_BASE_URL=https://openrouter.ai/api/v1
#
# Source of truth: docs/agent-system/model-rationale.md
# Letta expects OpenRouter-backed models to use the lc-openrouter/ prefix.
# Confirmed real OpenRouter IDs used here (verified 2026-03-09).
MODEL_MAP = {
    # High Court — Forensic Reasoning
    "watson": "lc-openrouter/anthropic/claude-opus-4-6",  # multi-step forensic reasoning (confirmed on OpenRouter)
    # Command Tier — Strategic Orchestration
    "commander": "lc-openrouter/x-ai/grok-3",  # 131K context, agentic (confirmed)
    "project-lead": "lc-openrouter/google/gemini-2.5-flash",  # long-horizon stability (upgrade to 2.5-pro when available)
    # Lead Tier — Production Execution
    "engineering-lead": "lc-openrouter/openai/gpt-4o",  # code quality, deterministic (upgrade to o3 when available)
    "design-lead": "lc-openrouter/qwen/qwen-2.5-coder-32b-instruct",  # free on OpenRouter, strong coding model (confirmed)
    "infrastructure-lead": "lc-openrouter/z-ai/glm-4.6",  # 203K context, multi-tenant (confirmed; glm-5 when available)
    "forensic-lead": "lc-openrouter/deepseek/deepseek-v3.2",  # distinct lineage, adversarial (confirmed)
    # Guardian Tier — Validation & Logistics
    "bundle": "lc-openrouter/google/gemini-2.5-flash",  # near-Pro at flash speed (confirmed)
    "task-observer": "lc-openrouter/google/gemini-2.5-flash-lite",  # token-efficient telemetry (confirmed)
    "validator": "lc-openrouter/openai/gpt-4o-mini",  # critique diversity (upgrade to gpt-5-mini when available)
    # GSD agents (used by Engineering Lead)
    "gsd-planner": "lc-openrouter/openai/gpt-4o",
    "gsd-executor": "lc-openrouter/openai/gpt-4o",
    "gsd-verifier": "lc-openrouter/openai/gpt-4o",
    "gsd-plan-checker": "lc-openrouter/openai/gpt-4o",
    "gsd-debugger": "lc-openrouter/openai/gpt-4o",
}

# Agents to register by default (core system — not GSD utilities)
CORE_AGENTS = [
    "commander",
    "watson",
    "bundle",
    "engineering-lead",
    "design-lead",
    "forensic-lead",
    "infrastructure-lead",
    "project-lead",
    "task-observer",
    "validator",
]


def strip_frontmatter(content: str) -> str:
    """Remove YAML frontmatter (---...---) from the top of .md files."""
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            return content[end + 3 :].lstrip("\n")
    return content


def load_registry() -> dict:
    if REGISTRY_FILE.exists():
        return json.loads(REGISTRY_FILE.read_text())
    return {}


def save_registry(registry: dict):
    REGISTRY_FILE.write_text(json.dumps(registry, indent=2))
    print(f"Registry saved -> {REGISTRY_FILE}")


def list_letta_agents() -> dict:
    """Returns {name: agent_dict} for all registered Letta agents."""
    r = requests.get(f"{LETTA_BASE}/v1/agents", headers=HEADERS)
    r.raise_for_status()
    agents = r.json()
    if isinstance(agents, dict):
        agents = agents.get("agents", [])
    return {a["name"]: a for a in agents}


def create_agent(name: str, system_prompt: str, model: str) -> dict:
    """Create a Letta agent. Returns the created agent dict."""
    payload = {
        "name": name,
        "system": system_prompt,
        "model": model,
        "embedding": "letta/letta-free",
        "memory_blocks": [
            {
                "label": "human",
                "value": "I am a Vektal platform agent. I work with the Shopify multi-supplier platform team.",
                "limit": 2000,
            },
            {
                "label": "persona",
                "value": f"I am {name}, part of the Vektal agent system.",
                "limit": 2000,
            },
        ],
    }
    r = requests.post(f"{LETTA_BASE}/v1/agents", headers=HEADERS, json=payload)
    if not r.ok:
        print(f"  ERROR creating {name}: {r.status_code} {r.text[:300]}")
        return {}
    return r.json()


def delete_agent(agent_id: str):
    """Delete a Letta agent by ID."""
    r = requests.delete(f"{LETTA_BASE}/v1/agents/{agent_id}", headers=HEADERS)
    if not r.ok:
        print(f"  WARN: could not delete {agent_id}: {r.status_code}")


def register(agent_names: list, force: bool = False):
    print(f"\n{'=' * 60}")
    print(f"Letta Agent Registration — {LETTA_BASE}")
    print(f"{'=' * 60}")

    if not LETTA_KEY:
        print("ERROR: LETTA_API_KEY not set in .env")
        sys.exit(1)

    registry = load_registry()
    existing = list_letta_agents()
    print(f"Currently registered in Letta: {len(existing)}")
    for n, a in existing.items():
        print(f"  {a['id']} | {n}")

    print(f"\nRegistering {len(agent_names)} agents...")
    results = {"created": [], "skipped": [], "updated": [], "failed": []}

    for name in agent_names:
        md_file = AGENTS_DIR / f"{name}.md"
        if not md_file.exists():
            print(f"  SKIP {name} — no .letta/agents/{name}.md")
            results["skipped"].append(name)
            continue

        system_prompt = strip_frontmatter(md_file.read_text(encoding="utf-8"))
        model = MODEL_MAP.get(name, "letta/auto")

        if name in existing and not force:
            agent_id = existing[name]["id"]
            print(f"  EXISTS {name} ({agent_id}) — skipping (use --force to recreate)")
            registry[name] = {"id": agent_id, "model": model, "status": "existing"}
            results["skipped"].append(name)
            continue

        if name in existing and force:
            print(f"  DELETE {name} ({existing[name]['id']}) — forcing recreation")
            delete_agent(existing[name]["id"])

        print(f"  CREATE {name} (model: {model}) ...", end="", flush=True)
        agent = create_agent(name, system_prompt, model)
        if agent:
            agent_id = agent.get("id", "unknown")
            print(f" ✓ {agent_id}")
            registry[name] = {"id": agent_id, "model": model, "status": "created"}
            results["created"].append(f"{name} → {agent_id}")
        else:
            results["failed"].append(name)

    save_registry(registry)

    print(f"\n{'=' * 60}")
    print(f"DONE")
    print(f"  Created:  {len(results['created'])}")
    print(f"  Skipped:  {len(results['skipped'])}")
    print(f"  Failed:   {len(results['failed'])}")
    if results["created"]:
        print("\nNew agents:")
        for r in results["created"]:
            print(f"  {r}")
    if results["failed"]:
        print("\nFailed:")
        for f in results["failed"]:
            print(f"  {f}")

    # Update .env with key agent IDs
    update_env_with_registry(registry)


def update_env_with_registry(registry: dict):
    """
    Write key agent IDs to .env so Commander/Watson can find each other
    via environment variables.
    """
    env_path = ROOT / ".env"
    if not env_path.exists():
        return

    env_content = env_path.read_text(encoding="utf-8")

    env_keys = {
        "commander": "LETTA_AGENT_COMMANDER_ID",
        "watson": "LETTA_AGENT_WATSON_ID",
        "bundle": "LETTA_AGENT_BUNDLE_ID",
        "engineering-lead": "LETTA_AGENT_ENGINEERING_LEAD_ID",
        "design-lead": "LETTA_AGENT_DESIGN_LEAD_ID",
        "forensic-lead": "LETTA_AGENT_FORENSIC_LEAD_ID",
        "infrastructure-lead": "LETTA_AGENT_INFRA_LEAD_ID",
        "project-lead": "LETTA_AGENT_PROJECT_LEAD_ID",
        "task-observer": "LETTA_AGENT_TASK_OBSERVER_ID",
        "validator": "LETTA_AGENT_VALIDATOR_ID",
    }

    updated = []
    for agent_name, env_key in env_keys.items():
        if agent_name not in registry:
            continue
        agent_id = registry[agent_name]["id"]
        line = f"{env_key}={agent_id}"

        if env_key in env_content:
            # Replace existing line
            env_content = re.sub(
                rf"^{re.escape(env_key)}=.*$",
                line,
                env_content,
                flags=re.MULTILINE,
            )
            updated.append(f"  updated {env_key}")
        else:
            # Append at end
            env_content += f"\n{line}"
            updated.append(f"  added   {env_key}")

    if updated:
        env_path.write_text(env_content, encoding="utf-8")
        print(f"\n.env updated with agent IDs:")
        for u in updated:
            print(u)


def show_registry():
    registry = load_registry()
    if not registry:
        print("Registry is empty. Run register_agents.py to create agents.")
        return
    print(f"\nAgent Registry ({REGISTRY_FILE}):")
    print(f"{'Agent':<25} {'ID':<45} {'Model':<45} Status")
    print("-" * 130)
    for name, data in sorted(registry.items()):
        if name.startswith("_"):
            continue
        print(
            f"{name:<25} {data['id']:<45} {data['model']:<45} {data.get('status', '?')}"
        )


def main():
    parser = argparse.ArgumentParser(description="Register Vektal agents in Letta")
    parser.add_argument(
        "--force", action="store_true", help="Delete and recreate existing agents"
    )
    parser.add_argument("--list", action="store_true", help="Show current registry")
    parser.add_argument(
        "--all", action="store_true", help="Register all agents including GSD utilities"
    )
    parser.add_argument("--agent", type=str, help="Register a single named agent")
    args = parser.parse_args()

    if args.list:
        show_registry()
        return

    if args.agent:
        register([args.agent], force=args.force)
    elif args.all:
        all_agents = [f.stem for f in AGENTS_DIR.glob("*.md")]
        register(all_agents, force=args.force)
    else:
        register(CORE_AGENTS, force=args.force)


if __name__ == "__main__":
    main()
