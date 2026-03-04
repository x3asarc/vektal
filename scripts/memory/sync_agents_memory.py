#!/usr/bin/env python3
"""Sync the AGENTS memory contract from .planning/memory-system-design.md."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENTS_PATH = REPO_ROOT / "AGENTS.md"
DESIGN_PATH = REPO_ROOT / ".planning" / "memory-system-design.md"

BEGIN_MARKER = "<!-- MEMORY-CONTRACT:START -->"
END_MARKER = "<!-- MEMORY-CONTRACT:END -->"


@dataclass(frozen=True)
class TierContract:
    name: str
    location: str
    scope: str
    ttl: str


def _clean_value(raw: str) -> str:
    value = raw.strip().strip("`")
    value = re.sub(r"[^\x20-\x7E]+", " ", value)
    value = value.replace("|", " ").strip()
    value = re.sub(r"\s+", " ", value)
    return value


def _extract_tier_contract_from_location(
    lines: list[str],
    *,
    tier_label: str,
    location_hint: str,
    fallback_scope: str,
    fallback_ttl: str,
) -> TierContract:
    location = location_hint
    scope = fallback_scope
    ttl = fallback_ttl

    target_idx = None
    for idx, line in enumerate(lines):
        if location_hint in line:
            target_idx = idx
            break
    if target_idx is not None:
        location_line = lines[target_idx]
        if "Location:" in location_line:
            location = _clean_value(location_line.split("Location:", maxsplit=1)[1])
        else:
            location = _clean_value(location_hint)

        window_start = max(0, target_idx - 12)
        window_end = min(len(lines), target_idx + 12)
        for line in lines[window_start:window_end]:
            if "Scope:" in line:
                scope = _clean_value(line.split("Scope:", maxsplit=1)[1])
            elif "TTL:" in line:
                ttl = _clean_value(line.split("TTL:", maxsplit=1)[1])

    return TierContract(name=tier_label, location=location, scope=scope, ttl=ttl)


def _load_contract_from_design(design_text: str) -> list[TierContract]:
    lines = design_text.splitlines()
    return [
        _extract_tier_contract_from_location(
            lines,
            tier_label="WORKING MEMORY",
            location_hint=".memory/working/{session_id}.json",
            fallback_scope="Single conversation session",
            fallback_ttl="Until session ends; stale sessions ignored after 24h",
        ),
        _extract_tier_contract_from_location(
            lines,
            tier_label="SHORT-TERM MEMORY",
            location_hint=".memory/short-term/{date}.jsonl",
            fallback_scope="Daily task/activity summary",
            fallback_ttl="7-30 days",
        ),
        _extract_tier_contract_from_location(
            lines,
            tier_label="LONG-TERM MEMORY",
            location_hint=".memory/long-term/",
            fallback_scope="Project lifetime",
            fallback_ttl="Forever (versioned)",
        ),
    ]


def _render_memory_contract(tiers: list[TierContract]) -> str:
    lines = [
        "1. Managed section: update `.planning/memory-system-design.md`, then run `python scripts/memory/sync_agents_memory.py`.",
        "2. Source of truth for memory behavior: `.planning/memory-system-design.md`.",
        "3. Multi-tier memory contract:",
    ]
    for tier in tiers:
        lines.append(
            f"   - `{tier.name.title()}`: location `{tier.location}`; scope `{tier.scope}`; TTL `{tier.ttl}`."
        )
    lines.extend(
        [
            "4. Runtime hooks/scripts:",
            "   - Session bootstrap: `python scripts/memory/session_start.py`",
            "   - Live command sync (Codex PreTool): `python scripts/memory/pre_tool_update.py --provider codex --session-key <stable-id>`",
            "   - Session finalize: `python scripts/memory/session_end.py --context-file <json>`",
            "   - Task learnings: `python scripts/memory/task_complete.py --task <id>`",
            "   - Phase synthesis: `python scripts/memory/phase_complete.py --phase <id> --summary <text>`",
            "5. Provider SessionStart wiring must include the session bootstrap script in:",
            "   - `.codex/settings.json`",
            "   - `.claude/settings.json`",
            "   - `.gemini/settings.json`",
            "6. Memory hooks are best-effort and must not block sessions on failure.",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def _upsert_memory_section(agents_text: str, contract_text: str) -> str:
    managed_block = f"{BEGIN_MARKER}\n{contract_text}{END_MARKER}"
    pattern = re.compile(
        rf"{re.escape(BEGIN_MARKER)}[\s\S]*?{re.escape(END_MARKER)}",
        flags=re.MULTILINE,
    )
    if pattern.search(agents_text):
        return pattern.sub(managed_block, agents_text)

    section = "\n".join(
        [
            "",
            "",
            "## Memory runtime contract",
            managed_block,
            "",
        ]
    )
    return agents_text.rstrip() + section


def sync_agents_memory_section(repo_root: Path = REPO_ROOT) -> tuple[bool, str]:
    agents_path = repo_root / "AGENTS.md"
    design_path = repo_root / ".planning" / "memory-system-design.md"

    if not agents_path.exists():
        return False, f"AGENTS missing: {agents_path}"
    if not design_path.exists():
        return False, f"Memory design missing: {design_path}"

    design_text = design_path.read_text(encoding="utf-8", errors="ignore")
    tiers = _load_contract_from_design(design_text)
    contract = _render_memory_contract(tiers)
    current_agents = agents_path.read_text(encoding="utf-8")
    updated_agents = _upsert_memory_section(current_agents, contract)
    if updated_agents == current_agents:
        return False, "AGENTS memory contract already up to date."
    agents_path.write_text(updated_agents, encoding="utf-8")
    return True, "AGENTS memory contract updated."


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync AGENTS memory section from planning design.")
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="Repository root (default: current repo)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    changed, message = sync_agents_memory_section(Path(args.repo_root).resolve())
    tag = "UPDATED" if changed else "OK"
    print(f"[{tag}] {message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
