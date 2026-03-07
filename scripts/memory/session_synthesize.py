#!/usr/bin/env python3
"""Session synthesis script - extracts insights from session and writes to memory."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.memory.memory_manager import (
    ShortTermMemory,
    WorkingMemory,
    LongTermMemory,
    ensure_memory_layout,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def synthesize_session(
    session_id: str | None = None,
    insights: list[str] | None = None,
    decisions: list[dict] | None = None,
    files_modified: list[str] | None = None,
    next_steps: list[str] | None = None,
) -> dict:
    """Synthesize session into memory systems."""
    ensure_memory_layout()

    # Load working memory if session_id provided
    working = None
    if session_id:
        working = WorkingMemory.load_for_session(session_id)

    # Build synthesis entry
    entry = {
        "timestamp": _utc_now_iso(),
        "type": "session_synthesis",
        "insights": insights or [],
        "decisions": decisions or [],
        "files_modified": files_modified or [],
        "next_steps": next_steps or [],
    }

    # Append to short-term memory
    stm = ShortTermMemory()
    stm.append_event("session_synthesis", entry)

    # Check for patterns to promote
    ltm = LongTermMemory()
    for insight in entry.get("insights", []):
        if "pattern:" in insight.lower():
            # Extract pattern name and create long-term doc
            pattern_name = insight.split("pattern:")[-1].strip()
            ltm.append_pattern(
                title=pattern_name,
                summary=insight,
                anti_pattern="anti-pattern" in insight.lower(),
            )

    ltm.record_event("session_synthesis", source="session-synthesize-script")

    return {
        "status": "success",
        "short_term_updated": True,
        "patterns_promoted": len([i for i in entry.get("insights", []) if "pattern:" in i.lower()]),
        "timestamp": entry["timestamp"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Synthesize session to memory")
    parser.add_argument("--session-id", help="Session ID to load working memory")
    parser.add_argument("--insights", nargs="*", default=[], help="Insight strings")
    parser.add_argument("--decisions", nargs="*", default=[], help="Decision JSON strings")
    parser.add_argument("--files", nargs="*", default=[], help="Modified file paths")
    parser.add_argument("--next-steps", nargs="*", default=[], help="Next step strings")
    args = parser.parse_args()

    decisions = []
    for d in args.decisions:
        try:
            decisions.append(json.loads(d))
        except json.JSONDecodeError:
            decisions.append({"raw": d})

    result = synthesize_session(
        session_id=args.session_id,
        insights=args.insights,
        decisions=decisions,
        files_modified=args.files,
        next_steps=args.next_steps,
    )

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())