#!/usr/bin/env python3
"""Sync between Letta memory blocks and repo .memory/ system."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.memory.memory_manager import (
    WorkingMemory,
    ShortTermMemory,
    ensure_memory_layout,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def get_letta_memory_dir() -> Path | None:
    """Get Letta agent memory directory from env."""
    mem_dir = os.getenv("MEMORY_DIR")
    if mem_dir:
        return Path(mem_dir) / "system"
    return None


def sync_repo_to_letta() -> dict:
    """Sync from repo .memory/ to Letta memory blocks."""
    ensure_memory_layout()

    # Load latest working memory
    working = WorkingMemory.load_latest(max_age_hours=24)
    if not working:
        return {"status": "no_working_memory", "synced": False}

    letta_dir = get_letta_memory_dir()
    if not letta_dir:
        return {"status": "no_letta_dir", "synced": False}

    # Update Letta current/session.md
    session_path = letta_dir / "current" / "session.md"
    if session_path.exists():
        content = session_path.read_text(encoding="utf-8")
        # Update context section
        lines = content.split("\n")
        new_lines = []
        in_context = False
        for line in lines:
            if line.startswith("## Current Session"):
                in_context = True
                new_lines.append(line)
                continue
            if in_context and line.startswith("## "):
                in_context = False
            if in_context:
                continue
            new_lines.append(line)

        # Insert new context
        context_section = [
            "## Current Session",
            "",
            f"**Started:** {working.get('started_at', 'unknown')}",
            f"**Last Updated:** {_utc_now_iso()}",
            "",
            f"**Active Task:** {working.get('context', {}).get('current_task', 'N/A')}",
            "",
            "**Files Modified This Session:**",
        ]
        for f in working.get("recent_files", [])[-5:]:
            context_section.append(f"- {f.get('path', 'unknown')} ({f.get('action', 'unknown')})")
        context_section.append("")
        context_section.append("**Insights:**")
        for i in working.get("insights", [])[-5:]:
            context_section.append(f"- {i}")
        context_section.append("")

        # Find insertion point
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.startswith("# "):
                insert_idx = i + 1
                break

        final_lines = lines[:insert_idx] + context_section + new_lines[insert_idx:]
        session_path.write_text("\n".join(final_lines), encoding="utf-8")

    # Update Letta current/next-steps.md
    next_steps_path = letta_dir / "current" / "next-steps.md"
    if next_steps_path.exists() and working.get("next_steps"):
        content = next_steps_path.read_text(encoding="utf-8")
        lines = content.split("\n")
        # Find and update the checklist
        new_lines = []
        for line in lines:
            if line.startswith("## Next Steps"):
                new_lines.append(line)
                new_lines.append("")
                for step in working.get("next_steps", [])[-5:]:
                    new_lines.append(f"- [ ] {step}")
                continue
            if line.strip().startswith("- [ ]"):
                continue  # Skip old items
            new_lines.append(line)
        next_steps_path.write_text("\n".join(new_lines), encoding="utf-8")

    return {
        "status": "success",
        "synced": True,
        "session_updated": session_path.exists(),
        "next_steps_updated": next_steps_path.exists() and working.get("next_steps"),
    }


def sync_letta_to_repo() -> dict:
    """Sync from Letta memory blocks to repo .memory/."""
    letta_dir = get_letta_memory_dir()
    if not letta_dir:
        return {"status": "no_letta_dir", "synced": False}

    ensure_memory_layout()

    # Read Letta current/session.md and extract context
    session_path = letta_dir / "current" / "session.md"
    if not session_path.exists():
        return {"status": "no_session_file", "synced": False}

    # Create/update working memory
    working = WorkingMemory()
    session_content = session_path.read_text(encoding="utf-8")

    # Parse session content for context
    lines = session_content.split("\n")
    for line in lines:
        if line.startswith("**Active Task:**"):
            working.update_context("current_task", line.split(":", 1)[-1].strip())
        elif line.startswith("- ") and "modified" in line.lower():
            # Extract file path
            parts = line.split("(")
            if len(parts) == 2:
                path = parts[0].strip("- ").strip()
                action = parts[1].strip(")").strip()
                working.track_file(path, action)

    working.save()

    return {
        "status": "success",
        "synced": True,
        "working_memory": working.file_path.name,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync Letta and repo memory")
    parser.add_argument(
        "--direction",
        choices=["repo-to-letta", "letta-to-repo"],
        required=True,
        help="Sync direction",
    )
    args = parser.parse_args()

    if args.direction == "repo-to-letta":
        result = sync_repo_to_letta()
    else:
        result = sync_letta_to_repo()

    print(json.dumps(result, indent=2))
    return 0 if result.get("synced") else 1


if __name__ == "__main__":
    raise SystemExit(main())