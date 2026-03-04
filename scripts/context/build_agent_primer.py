#!/usr/bin/env python3
"""Generate docs/AGENT_START_HERE.md from planning and memory snapshots."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.memory.materializers import discover_sessions  # noqa: E402


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _extract_state_line(content: str, label: str) -> str:
    pattern = re.compile(rf"^\*\*{re.escape(label)}:\*\*\s*(.+)$", re.MULTILINE)
    match = pattern.search(content)
    return match.group(1).strip() if match else "N/A"


def _extract_next_actions(content: str, limit: int = 5) -> list[str]:
    actions: list[str] = []
    for line in content.splitlines():
        candidate = line.strip()
        if not candidate:
            continue
        if candidate.startswith("- [ ]"):
            actions.append(candidate[5:].strip())
        elif re.match(r"^\d+\.\s+", candidate):
            actions.append(re.sub(r"^\d+\.\s+", "", candidate).strip())
        elif candidate.startswith("- "):
            actions.append(candidate[2:].strip())
        if len(actions) >= limit:
            break
    return actions


def _git_sha(repo_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return (result.stdout or "").strip() or "unknown"
    except Exception:
        pass
    return "unknown"


def _latest_working_context(repo_root: Path) -> tuple[str, str]:
    working_dir = repo_root / ".memory" / "working"
    if not working_dir.exists():
        return "N/A", "N/A"
    files = sorted(working_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return "N/A", "N/A"
    latest = files[0]
    try:
        payload = json.loads(latest.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return latest.name, "N/A"
    task = str((payload.get("context") or {}).get("current_task") or "N/A")
    return latest.name, task


def build_agent_primer(
    *,
    repo_root: Path = REPO_ROOT,
    output_path: Path | None = None,
    now_iso: str | None = None,
    git_sha: str | None = None,
    write: bool = True,
) -> dict[str, Any]:
    """Build AGENT_START_HERE markdown and optionally write to docs/."""

    now_value = now_iso or _utc_now_iso()
    sha = git_sha or _git_sha(repo_root)

    state_text = _safe_read(repo_root / ".planning" / "STATE.md")
    roadmap_text = _safe_read(repo_root / ".planning" / "ROADMAP.md")
    next_tasks_text = _safe_read(repo_root / ".planning" / "NEXT_TASKS.md")

    phase = _extract_state_line(state_text, "Phase")
    gate = _extract_state_line(state_text, "Gate Status")
    target = _extract_state_line(state_text, "Target Milestone")
    actions = _extract_next_actions(next_tasks_text) or _extract_next_actions(roadmap_text)
    latest_working_file, latest_working_task = _latest_working_context(repo_root)
    sessions = discover_sessions(root=repo_root / ".memory")

    lines = [
        "# AGENT START HERE",
        "",
        f"- Last refreshed: {now_value}",
        f"- Source commit: `{sha}`",
        "",
        "## Current Runtime Snapshot",
        f"- Phase: {phase}",
        f"- Gate Status: {gate}",
        f"- Target Milestone: {target}",
        "",
        "## Immediate Blockers / Next Actions",
    ]
    if actions:
        lines.extend([f"- {item}" for item in actions[:5]])
    else:
        lines.append("- N/A")

    lines.extend(
        [
            "",
            "## Priority Links",
            "- `.planning/ROADMAP.md`",
            "- `.planning/STATE.md`",
            "- `.planning/phases/16-agent-context-os/16-PLAN.md`",
            "- `.planning/phases/16-agent-context-os/16-RESEARCH.md`",
            "- `docs/MASTER_MAP.md`",
            "",
            "## Folder Summary Pointers",
            "- `docs/FOLDER_SUMMARIES.md`",
            "- `docs/CONTEXT_LINK_MAP.md`",
            "",
            "## Memory Snapshot",
            f"- Working sessions discovered: {len(sessions)}",
            f"- Latest working file: {latest_working_file}",
            f"- Latest working task: {latest_working_task}",
            "- View paths:",
            "  - `.memory/working/{session_id}.json`",
            "  - `.memory/short-term/{date}.jsonl`",
            "  - `.memory/long-term/index.json`",
            "",
        ]
    )

    content = "\n".join(lines)
    target = output_path or (repo_root / "docs" / "AGENT_START_HERE.md")
    if write:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return {"path": str(target), "content": content}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate docs/AGENT_START_HERE.md")
    parser.add_argument("--dry-run", action="store_true", help="Render without writing file")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_agent_primer(write=not args.dry_run)
    print(result["content"] if args.dry_run else f"[primer] wrote {result['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
