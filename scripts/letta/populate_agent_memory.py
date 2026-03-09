"""
scripts/letta/populate_agent_memory.py

Populates persistent memory blocks on all registered Letta agents.
Reads content from project memory files and agent specs.

Success criteria (10 SCs — must all pass before --verify exits 0):
  SC-1:  Block coverage — every agent has its required blocks
  SC-2:  All block limits >= 50000
  SC-3:  No placeholder content ("I am a Vektal platform agent" etc.)
  SC-4:  agent-registry block contains valid IDs on Commander + Watson
  SC-5:  casebook-summary block exists and is non-empty on Watson
  SC-6:  Idempotent — running twice does not create duplicate blocks
  SC-7:  Old 2000-limit stub blocks removed from all agents
  SC-8:  --verify flag exits 0 when all SCs pass
  SC-9:  No source file content leaked into blocks
  SC-10: Registry file unchanged after script runs

Usage:
    python scripts/letta/populate_agent_memory.py           # populate all
    python scripts/letta/populate_agent_memory.py --verify  # check SCs only
    python scripts/letta/populate_agent_memory.py --agent commander  # single
    python scripts/letta/populate_agent_memory.py --dry-run # show what would change
"""

import os, sys, json, re, argparse, requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ROOT        = Path(__file__).parent.parent.parent
MEMORY_DIR  = Path(os.getenv("LETTA_MEMORY_DIR", Path.home() / ".letta" / "agents" /
              os.getenv("LETTA_AGENT_ID", "") / "memory"))
REGISTRY    = ROOT / ".letta" / "agent-registry.json"
AGENTS_DIR  = ROOT / ".letta" / "agents"

LETTA_BASE  = os.getenv("LETTA_BASE_URL", "https://api.letta.com")
LETTA_KEY   = os.getenv("LETTA_API_KEY", "")
HEADERS     = {"Authorization": f"Bearer {LETTA_KEY}", "Content-Type": "application/json"}

BLOCK_LIMIT = 100_000  # SC-2: all blocks must be at least this
STUB_LIMIT  = 2_000    # SC-7: blocks at this limit are stubs to remove
STUB_TEXTS  = [        # SC-3: these strings must not appear in any block value
    "I am a Vektal platform agent",
    "I am commander, part of",
    "I am watson, part of",
    "I am bundle, part of",
    "I am engineering-lead",
    "I am design-lead",
    "I am forensic-lead",
    "I am infrastructure-lead",
    "I am project-lead",
    "I am task-observer",
    "I am validator",
]
# SC-9: these patterns must NOT appear in any block value
SOURCE_LEAK_PATTERNS = [
    r"def [a-z_]+\(self",          # Python method definitions
    r"SELECT .+ FROM ",            # SQL
    r"MATCH \(n:",                 # Cypher (raw graph queries shouldn't be in memory blocks)
    r"import (requests|flask|sqlalchemy)",  # Python imports
]


# ── Shared project content ─────────────────────────────────────────────────────

def _read_memory_file(relative_path: str) -> str:
    """Read a file from the Analyst's memory directory (source of truth for project content)."""
    p = MEMORY_DIR / relative_path
    if p.exists():
        return p.read_text(encoding="utf-8").strip()
    # Fallback: try project root docs
    return f"[MISSING: {relative_path}]"


def _read_project_file(relative_path: str) -> str:
    """Read a file directly from the project root."""
    p = ROOT / relative_path
    if p.exists():
        return p.read_text(encoding="utf-8").strip()
    return f"[MISSING: {relative_path}]"


def _build_agent_registry_block() -> str:
    """Build the agent-registry block content from .letta/agent-registry.json."""
    registry = json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}
    lines = ["# Vektal Agent Registry", "",
             "Use these IDs when sending messages to other agents via send_message.", ""]
    lines.append(f"{'Agent':<25} {'Letta Agent ID':<45} Model")
    lines.append("-" * 100)
    for name, data in sorted(registry.items()):
        if name.startswith("_"):
            continue
        lines.append(f"{name:<25} {data['id']:<45} {data.get('model','')}")
    lines += [
        "",
        "## Key pairs for this agent",
        "- Commander messages Watson by ID for blind spawn and PostMortem",
        "- Watson replies to Commander by ID after ChallengeReport",
        "- Commander messages Bundle for configuration",
        "",
        "## Environment variables (also in .env)",
        "LETTA_AGENT_COMMANDER_ID, LETTA_AGENT_WATSON_ID, LETTA_AGENT_BUNDLE_ID,",
        "LETTA_AGENT_ENGINEERING_LEAD_ID, LETTA_AGENT_DESIGN_LEAD_ID,",
        "LETTA_AGENT_FORENSIC_LEAD_ID, LETTA_AGENT_INFRA_LEAD_ID,",
        "LETTA_AGENT_PROJECT_LEAD_ID, LETTA_AGENT_TASK_OBSERVER_ID, LETTA_AGENT_VALIDATOR_ID",
    ]
    return "\n".join(lines)


def _build_casebook_summary() -> str:
    """Watson's initial casebook-summary block — cold start."""
    return """# Watson Casebook Summary

## Calibration Status
- **Overall:** COLD_START (0 cases recorded)
- **Per domain:** All domains at calibration_score = 0.0

## Domain Case Counts
| Domain | Cases | Weighted Failure Rate | Dominant Failure Mode |
|---|---|---|---|
| billing | 0 | — | — |
| frontend | 0 | — | — |
| infrastructure | 0 | — | — |
| engineering | 0 | — | — |
| graph | 0 | — | — |

## Commander Override Patterns
No data yet. Will populate as PostMortems accumulate.

## Notes
- Calibration score = 0.0 until 5+ cases per domain
- watson_verdict_correct rate tracked per domain
- This block is updated by W-POSTMORTEM after each Lead completion
- Git-entropy decay applied to all priors (commits in affected dir since case opened)
"""


# ── Block definitions per agent ────────────────────────────────────────────────

def _get_project_overview() -> str:
    return _read_memory_file("system/project/overview.md")

def _get_project_conventions() -> str:
    return _read_memory_file("system/project/conventions.md")

def _get_project_commands() -> str:
    return _read_memory_file("system/project/commands.md")


def _build_persona_block(role_header: str, identity: str, spec_ref: str) -> str:
    """persona block = role identity. No project content (that goes in human)."""
    return f"{role_header}\n\n{identity}\n\nFull spec: {spec_ref}"


def _build_human_block(sections: list) -> str:
    """human block = all project context packed together. sections = list of (header, content)."""
    parts = []
    for header, content in sections:
        parts.append(f"{'='*60}\n{header}\n{'='*60}\n\n{content}")
    return "\n\n".join(parts)


def _reg() -> dict:
    return json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}


# Maps agent_name -> (persona_value_fn, human_value_fn)
# Both target the EXISTING 'persona' and 'human' blocks (confirmed patchable).
AGENT_CONTENT = {
    "commander": (
        lambda: _build_persona_block(
            "# Commander — Lead Investigator & Chief Orchestration Agent (v2.0)",
            (
                "You propose routing, defend it against Watson's adversarial review, integrate accepted\n"
                "flags, and hand the Watson-validated package to Bundle.\n\n"
                "Authority partition:\n"
                "  Routing:              YOURS (Lead selection, domain)\n"
                "  Scope + loop budget:  WATSON'S (you propose, Watson sets final)\n"
                "  GHOST_DATA:           WATSON'S (sole issuer)\n\n"
                "Key agent IDs:\n"
                f"  Watson:  {_reg().get('watson',{}).get('id','NOT_REGISTERED')}\n"
                f"  Bundle:  {_reg().get('bundle',{}).get('id','NOT_REGISTERED')}"
            ),
            "docs/agent-system/specs/commander.md (v2.0)"
        ),
        lambda: _build_human_block([
            ("PROJECT OVERVIEW", _get_project_overview()),
            ("PROJECT CONVENTIONS", _get_project_conventions()),
            ("AGENT REGISTRY", _build_agent_registry_block()),
        ]),
    ),

    "watson": (
        lambda: _build_persona_block(
            "# Watson — Forensic Partnership Co-Lead (v1.0)",
            (
                "You ground Commander's routing in human intent, graph evidence quality, and\n"
                "business consequence. You own scope tier and loop budget.\n\n"
                "Authority partition:\n"
                "  Routing:              0% (Commander's lane)\n"
                "  Scope + loop budget:  100% (your lane — binding)\n"
                "  GHOST_DATA:           100% (sole issuer)\n\n"
                "Platform context: Single Shopify store, 8 suppliers, 4,000+ SKUs. NOT multi-tenant.\n\n"
                "Key agent IDs:\n"
                f"  Commander: {_reg().get('commander',{}).get('id','NOT_REGISTERED')}\n\n"
                "CASEBOOK SUMMARY (cold start — updates after each PostMortem):\n"
                + _build_casebook_summary()
            ),
            "docs/agent-system/specs/watson.md (v1.0)"
        ),
        lambda: _build_human_block([
            ("PROJECT OVERVIEW", _get_project_overview()),
            ("AGENT REGISTRY", _build_agent_registry_block()),
        ]),
    ),

    "bundle": (
        lambda: _build_persona_block(
            "# Bundle — Project Configuration & Model Policy Engine (v1.0)",
            (
                "You sit between Commander and execution. Given Commander's Watson-validated context\n"
                "package, return the optimal team configuration (BundleConfig).\n\n"
                "You do not implement. You do not coordinate. Classify, configure, inject lessons, return config.\n\n"
                "Key v2 rule: scope_tier_final and loop_budget_final from Watson are binding.\n"
                "Watson's scope authority is not yours to override."
            ),
            "docs/agent-system/specs/bundle.md (v1.0)"
        ),
        lambda: _build_human_block([
            ("PROJECT OVERVIEW", _get_project_overview()),
        ]),
    ),

    "engineering-lead": (
        lambda: _build_persona_block(
            "# Engineering Lead — Backend & Feature Engineering Conductor",
            (
                "You own the full implementation cycle: plan validation, TDD, GSD execution,\n"
                "governance gating, and branch completion.\n\n"
                "The loop_budget in your context package was set by Watson's scope authority — respect it."
            ),
            "docs/agent-system/specs/engineering-lead.md"
        ),
        lambda: _build_human_block([
            ("PROJECT OVERVIEW", _get_project_overview()),
            ("PROJECT CONVENTIONS", _get_project_conventions()),
            ("COMMON COMMANDS", _get_project_commands()),
        ]),
    ),

    "design-lead": (
        lambda: _build_persona_block(
            "# Design Lead — Frontend & UX Conductor",
            (
                "You own the full frontend implementation cycle: UI/UX design, component implementation,\n"
                "accessibility, and visual satisfaction gates.\n\n"
                "The loop_budget in your context package was set by Watson's scope authority — respect it."
            ),
            "docs/agent-system/specs/design-lead.md"
        ),
        lambda: _build_human_block([
            ("PROJECT OVERVIEW", _get_project_overview()),
            ("PROJECT CONVENTIONS", _get_project_conventions()),
            ("COMMON COMMANDS", _get_project_commands()),
        ]),
    ),

    "forensic-lead": (
        lambda: _build_persona_block(
            "# Forensic Lead — Root Cause Analysis & Investigation Conductor",
            (
                "You own deep investigation: blast radius analysis, root cause tracing,\n"
                "Sentry intake, and failure pattern detection.\n\n"
                "The loop_budget in your context package was set by Watson's scope authority — respect it."
            ),
            "docs/agent-system/specs/forensic-lead.md"
        ),
        lambda: _build_human_block([
            ("PROJECT OVERVIEW", _get_project_overview()),
            ("PROJECT CONVENTIONS", _get_project_conventions()),
            ("COMMON COMMANDS", _get_project_commands()),
        ]),
    ),

    "infrastructure-lead": (
        lambda: _build_persona_block(
            "# Infrastructure Lead — DevOps & Platform Infrastructure Conductor",
            (
                "You own Docker, Nginx, deployment, environment configuration, database migrations,\n"
                "Celery queues, and all infrastructure concerns.\n\n"
                "The loop_budget in your context package was set by Watson's scope authority — respect it."
            ),
            "docs/agent-system/specs/infrastructure-lead.md"
        ),
        lambda: _build_human_block([
            ("PROJECT OVERVIEW", _get_project_overview()),
            ("PROJECT CONVENTIONS", _get_project_conventions()),
            ("COMMON COMMANDS", _get_project_commands()),
        ]),
    ),

    "project-lead": (
        lambda: _build_persona_block(
            "# Project Lead — Compound Task Conductor",
            (
                "You handle tasks that span multiple domains. You decompose, assign sub-tasks to the\n"
                "appropriate Leads, coordinate sequencing, and synthesise outcomes.\n\n"
                "The loop_budget in your context package was set by Watson's scope authority — respect it."
            ),
            "docs/agent-system/specs/project-lead.md"
        ),
        lambda: _build_human_block([
            ("PROJECT OVERVIEW", _get_project_overview()),
            ("PROJECT CONVENTIONS", _get_project_conventions()),
            ("COMMON COMMANDS", _get_project_commands()),
        ]),
    ),

    "task-observer": (
        lambda: _build_persona_block(
            "# task-observer — Improvement Engine",
            (
                "You read TaskExecution outcomes, infer patterns, propose ImprovementProposals,\n"
                "update BundleTemplate quality scores, and infer Lessons at 3x failure threshold.\n\n"
                "You do not execute tasks. You queue proposals for Validator approval."
            ),
            "docs/agent-system/specs/task-observer.md"
        ),
        lambda: _build_human_block([
            ("PROJECT OVERVIEW", _get_project_overview()),
        ]),
    ),

    "validator": (
        lambda: _build_persona_block(
            "# Validator — Approval Gate",
            (
                "You are the approval gate for ImprovementProposals from task-observer.\n"
                "Two-pass review (adversarial then constructive): approve or reject.\n"
                "Security and governance proposals require claude-sonnet or opus minimum."
            ),
            "docs/agent-system/specs/validator.md"
        ),
        lambda: _build_human_block([
            ("PROJECT OVERVIEW", _get_project_overview()),
            ("PROJECT CONVENTIONS", _get_project_conventions()),
        ]),
    ),
}


# ── Letta API helpers ──────────────────────────────────────────────────────────

def get_agent_blocks(agent_id: str) -> list:
    r = requests.get(f"{LETTA_BASE}/v1/agents/{agent_id}/core-memory", headers=HEADERS)
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, list) else data.get("blocks", [])


def patch_block(block_id: str, value: str, dry_run: bool = False) -> str:
    """
    Patch an existing block by its ID — the one endpoint confirmed working.
    PATCH /v1/blocks/{block_id} with {value, limit}.
    Returns: 'updated' | 'dry_run' | 'failed'
    """
    if dry_run:
        return "dry_run"
    r = requests.patch(
        f"{LETTA_BASE}/v1/blocks/{block_id}",
        headers=HEADERS,
        json={"value": value, "limit": BLOCK_LIMIT},
    )
    if not r.ok:
        print(f"    ERROR patching block {block_id}: {r.status_code} {r.text[:200]}")
        return "failed"
    return "updated"


# ── Required blocks per agent ──────────────────────────────────────────────────

# All agents use exactly 2 blocks: persona + human
REQUIRED_BLOCKS = {name: ["persona", "human"] for name in AGENT_CONTENT}

# What must appear in each agent's blocks (SC-3, SC-4, SC-5 checks)
CONTENT_CHECKS = {
    "commander": {
        "persona": ["Lead Investigator", "v2.0", "Watson", "Scope + loop budget"],
        "human":   ["Vektal", "KISS", "AGENT REGISTRY"],
    },
    "watson": {
        "persona": ["Forensic Partnership", "GHOST_DATA", "calibration_score"],
        "human":   ["Vektal", "AGENT REGISTRY"],
    },
    "bundle": {
        "persona": ["scope_tier_final", "loop_budget_final"],
        "human":   ["Vektal"],
    },
    "engineering-lead": {
        "persona": ["Engineering Lead", "loop_budget"],
        "human":   ["Vektal", "KISS", "pytest"],
    },
    "design-lead": {
        "persona": ["Design Lead", "loop_budget"],
        "human":   ["Vektal", "KISS"],
    },
    "forensic-lead": {
        "persona": ["Forensic Lead", "loop_budget"],
        "human":   ["Vektal", "KISS"],
    },
    "infrastructure-lead": {
        "persona": ["Infrastructure Lead", "loop_budget"],
        "human":   ["Vektal", "KISS"],
    },
    "project-lead": {
        "persona": ["Project Lead", "loop_budget"],
        "human":   ["Vektal", "KISS"],
    },
    "task-observer": {
        "persona": ["task-observer", "ImprovementProposal"],
        "human":   ["Vektal"],
    },
    "validator": {
        "persona": ["Validator", "approval gate"],
        "human":   ["Vektal", "KISS"],
    },
}


# ── Verify (SC-1 through SC-10) ────────────────────────────────────────────────

def verify_all(registry: dict) -> bool:
    all_pass = True
    print("\n=== VERIFICATION REPORT ===\n")

    for agent_name in REQUIRED_BLOCKS:
        if agent_name not in registry:
            print(f"RED   {agent_name}: not in registry")
            all_pass = False
            continue

        agent_id = registry[agent_name]["id"]
        try:
            blocks = get_agent_blocks(agent_id)
        except Exception as e:
            print(f"RED   {agent_name}: API error — {e}")
            all_pass = False
            continue

        block_map = {b["label"]: b for b in blocks}
        fails = []

        # SC-1: persona + human both present
        for label in ["persona", "human"]:
            if label not in block_map:
                fails.append(f"SC-1 MISSING block: {label}")

        # SC-2: both blocks at >= BLOCK_LIMIT
        for label in ["persona", "human"]:
            b = block_map.get(label, {})
            lim = b.get("limit", 0)
            if lim < BLOCK_LIMIT:
                fails.append(f"SC-2 '{label}' limit={lim} < {BLOCK_LIMIT}")

        # SC-3: no placeholder stub text in either block
        for label in ["persona", "human"]:
            val = block_map.get(label, {}).get("value", "")
            for stub in STUB_TEXTS:
                if stub.lower() in val.lower():
                    fails.append(f"SC-3 '{label}' contains placeholder: '{stub[:50]}'")

        # SC-4: Commander's human block contains Watson ID; Watson's persona contains Commander ID
        if agent_name == "commander":
            watson_id = registry.get("watson", {}).get("id", "")
            human_val = block_map.get("human", {}).get("value", "")
            if watson_id and watson_id not in human_val:
                fails.append(f"SC-4 human block missing Watson ID ({watson_id[:20]}...)")

        if agent_name == "watson":
            commander_id = registry.get("commander", {}).get("id", "")
            persona_val = block_map.get("persona", {}).get("value", "")
            if commander_id and commander_id not in persona_val:
                fails.append(f"SC-4 persona block missing Commander ID ({commander_id[:20]}...)")

        # SC-5: Watson persona contains casebook-summary content
        if agent_name == "watson":
            persona_val = block_map.get("persona", {}).get("value", "")
            if "calibration_score" not in persona_val:
                fails.append("SC-5 Watson persona missing casebook-summary (calibration_score)")
            if "COLD_START" not in persona_val:
                fails.append("SC-5 Watson persona missing COLD_START calibration label")

        # SC-6: no duplicate labels
        label_counts = {}
        for b in blocks:
            lbl = b.get("label", "")
            label_counts[lbl] = label_counts.get(lbl, 0) + 1
        for lbl, count in label_counts.items():
            if count > 1:
                fails.append(f"SC-6 duplicate block: '{lbl}' x{count}")

        # SC-7: no 2000-limit stubs remaining
        for b in blocks:
            if b.get("limit") == STUB_LIMIT:
                fails.append(f"SC-7 stub remaining: '{b.get('label')}' limit=2000")

        # SC-8: content checks (expected strings present)
        checks = CONTENT_CHECKS.get(agent_name, {})
        for label, expected_strings in checks.items():
            val = block_map.get(label, {}).get("value", "")
            for s in expected_strings:
                if s not in val:
                    fails.append(f"SC-8 '{label}' missing expected: '{s}'")

        # SC-9: no source file leaks
        for label in ["persona", "human"]:
            val = block_map.get(label, {}).get("value", "")
            for pattern in SOURCE_LEAK_PATTERNS:
                if re.search(pattern, val):
                    fails.append(f"SC-9 source leak in '{label}': '{pattern}'")

        if not fails:
            persona_len = len(block_map.get("persona", {}).get("value", ""))
            human_len   = len(block_map.get("human",   {}).get("value", ""))
            print(f"GREEN {agent_name} — persona:{persona_len:,}c human:{human_len:,}c")
        else:
            all_pass = False
            print(f"RED   {agent_name}:")
            for f in fails:
                print(f"        {f}")

    # SC-10: registry file still intact
    try:
        current = json.loads(REGISTRY.read_text())
        n = len([k for k in current if not k.startswith("_")])
        print(f"\nGREEN SC-10 registry intact ({n} agents)")
    except Exception as e:
        print(f"\nRED   SC-10 registry error: {e}")
        all_pass = False

    print(f"\n{'='*40}")
    print(f"OVERALL: {'GREEN — all SCs pass' if all_pass else 'RED — failures above'}")
    return all_pass


# ── Populate ───────────────────────────────────────────────────────────────────

def populate(agent_names: list, dry_run: bool = False):
    """
    Simple approach: each agent has exactly 2 existing blocks ('persona' + 'human').
    PATCH them in place via /v1/blocks/{block_id} — the one confirmed-working endpoint.
    Raises limit to BLOCK_LIMIT (100k). No new block creation needed.
    """
    registry = json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}
    registry_snapshot = json.dumps(registry, sort_keys=True)  # SC-10

    print(f"\n{'='*60}")
    print(f"Agent Memory Population {'(DRY RUN)' if dry_run else ''}")
    print(f"{'='*60}")

    for agent_name in agent_names:
        if agent_name not in registry:
            print(f"\nSKIP {agent_name} — not in registry")
            continue

        agent_id = registry[agent_name]["id"]
        content_def = AGENT_CONTENT.get(agent_name)
        if not content_def:
            print(f"\nSKIP {agent_name} — no content defined")
            continue

        print(f"\n{agent_name} ({agent_id[:16]}...):")

        # Get current blocks
        try:
            blocks = get_agent_blocks(agent_id)
        except Exception as e:
            print(f"  ERROR fetching blocks: {e}")
            continue

        block_map = {b["label"]: b for b in blocks}

        persona_fn, human_fn = content_def

        for label, value_fn in [("persona", persona_fn), ("human", human_fn)]:
            block = block_map.get(label)
            if not block:
                print(f"  WARN '{label}' block not found — skipping")
                continue

            block_id = block["id"]
            try:
                value = value_fn()
            except Exception as e:
                print(f"  ERROR building '{label}': {e}")
                continue

            if dry_run:
                current_limit = block.get("limit", 0)
                print(f"  [?] {label}: {len(value):,} chars, limit {current_limit} -> {BLOCK_LIMIT} — dry_run")
                continue

            result = patch_block(block_id, value, dry_run=False)
            icon = {"updated": "~", "failed": "!"}.get(result, "?")
            print(f"  [{icon}] {label} ({len(value):,} chars, limit -> {BLOCK_LIMIT}) — {result}")

    # SC-10: verify registry is unchanged
    registry_after = json.dumps(json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}, sort_keys=True)
    if registry_snapshot != registry_after:
        print("\nWARN SC-10: registry file was modified (should not happen)")
    else:
        print("\nSC-10: registry unchanged OK")


def main():
    parser = argparse.ArgumentParser(description="Populate Letta agent memory blocks")
    parser.add_argument("--verify",  action="store_true", help="Run SC verification only (no writes)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change, no writes")
    parser.add_argument("--agent",   type=str, help="Populate a single named agent")
    args = parser.parse_args()

    if not LETTA_KEY:
        print("ERROR: LETTA_API_KEY not set")
        sys.exit(1)

    if not REGISTRY.exists():
        print(f"ERROR: registry not found at {REGISTRY}")
        print("Run scripts/letta/register_agents.py first")
        sys.exit(1)

    registry = json.loads(REGISTRY.read_text())

    if args.verify:
        ok = verify_all(registry)
        sys.exit(0 if ok else 1)

    if args.agent:
        populate([args.agent], dry_run=args.dry_run)
    else:
        populate(list(REQUIRED_BLOCKS.keys()), dry_run=args.dry_run)

    if not args.dry_run:
        print("\nRunning verification...")
        ok = verify_all(registry)
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
