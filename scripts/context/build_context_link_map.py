#!/usr/bin/env python3
"""Generate docs/CONTEXT_LINK_MAP.md for high-signal context navigation."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _status(repo_root: Path, relative_path: str) -> str:
    return "present" if (repo_root / relative_path).exists() else "missing"


def build_context_link_map(
    *,
    repo_root: Path = REPO_ROOT,
    output_path: Path | None = None,
    now_iso: str | None = None,
    write: bool = True,
) -> dict[str, Any]:
    """Build context link map markdown and optionally write to docs/."""

    now_value = now_iso or _utc_now_iso()
    links: list[tuple[str, str, str, str]] = [
        ("Lifecycle", ".planning/ROADMAP.md", "Canonical lifecycle state", _status(repo_root, ".planning/ROADMAP.md")),
        ("Lifecycle", ".planning/STATE.md", "Current execution snapshot", _status(repo_root, ".planning/STATE.md")),
        ("Phase16", ".planning/phases/16-agent-context-os/16-PLAN.md", "Master phase plan", _status(repo_root, ".planning/phases/16-agent-context-os/16-PLAN.md")),
        ("Phase16", ".planning/phases/16-agent-context-os/16-RESEARCH.md", "Research + thought enhancement", _status(repo_root, ".planning/phases/16-agent-context-os/16-RESEARCH.md")),
        ("Onboarding", "docs/AGENT_START_HERE.md", "Primary new-agent entrypoint", _status(repo_root, "docs/AGENT_START_HERE.md")),
        ("Onboarding", "docs/FOLDER_SUMMARIES.md", "Directory-level summaries", _status(repo_root, "docs/FOLDER_SUMMARIES.md")),
        ("Onboarding", "docs/MASTER_MAP.md", "Global context map", _status(repo_root, "docs/MASTER_MAP.md")),
        ("Memory", ".memory/events/", "Append-only event stream root", _status(repo_root, ".memory/events")),
        ("Memory", "src/memory/event_log.py", "Event append/read primitives", _status(repo_root, "src/memory/event_log.py")),
        ("Memory", "src/memory/materializers.py", "Deterministic view builders", _status(repo_root, "src/memory/materializers.py")),
        ("Runtime", "src/assistant/memory_retrieval.py", "Runtime memory retrieval integration", _status(repo_root, "src/assistant/memory_retrieval.py")),
        ("Runtime", "scripts/memory/pre_tool_update.py", "Live command memory update hook", _status(repo_root, "scripts/memory/pre_tool_update.py")),
    ]

    lines = [
        "# CONTEXT LINK MAP",
        "",
        f"Last refreshed: {now_value}",
        "",
        "| Group | Path | Purpose | Status |",
        "|---|---|---|---|",
    ]

    for group, path, purpose, status in links:
        lines.append(f"| {group} | `{path}` | {purpose} | {status} |")

    content = "\n".join(lines) + "\n"
    target = output_path or (repo_root / "docs" / "CONTEXT_LINK_MAP.md")
    if write:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return {"path": str(target), "content": content, "row_count": len(links)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate docs/CONTEXT_LINK_MAP.md")
    parser.add_argument("--dry-run", action="store_true", help="Render without writing file")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_context_link_map(write=not args.dry_run)
    print(result["content"] if args.dry_run else f"[context-link-map] wrote {result['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

