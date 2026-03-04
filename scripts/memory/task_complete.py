#!/usr/bin/env python3
"""TaskComplete memory hook."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.memory.event_log import append_event  # noqa: E402
from src.memory.event_schema import EventType, create_event  # noqa: E402
from src.memory.memory_manager import LongTermMemory, ShortTermMemory  # noqa: E402
from scripts.memory.sync_agents_memory import sync_agents_memory_section  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Append task completion learnings to memory.")
    parser.add_argument("--task", required=True, help="Task id or label")
    parser.add_argument("--phase", help="Optional phase label")
    parser.add_argument("--outcome", default="success", help="Task outcome (success/failure/etc.)")
    parser.add_argument("--duration-minutes", type=int, help="Duration in minutes")
    parser.add_argument("--tests-added", type=int, default=0, help="Number of tests added")
    parser.add_argument("--file-modified", action="append", default=[], help="Modified file path (repeatable)")
    parser.add_argument("--learning", action="append", default=[], help="Learning captured (repeatable)")
    parser.add_argument("--challenge", action="append", default=[], help="Challenge encountered (repeatable)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        short_term = ShortTermMemory()
        entry = short_term.append_event(
            "task_completed",
            {
                "task": args.task,
                "phase": args.phase,
                "outcome": args.outcome,
                "duration_minutes": args.duration_minutes,
                "tests_added": args.tests_added,
                "files_modified": args.file_modified,
                "learnings": args.learning,
                "challenges": args.challenge,
            },
        )

        long_term = LongTermMemory()
        long_term.record_event("task_complete", source="task-complete-hook")
        if args.learning:
            long_term.append_pattern(
                title=f"Task pattern: {args.task}",
                summary="\n".join(args.learning),
                anti_pattern=args.outcome.lower() not in {"success", "green"},
            )
        append_event(
            create_event(
                event_type=EventType.TASK_COMPLETE,
                provider="codex",
                session_id=f"session-codex-task-{args.task}",
                source="scripts/memory/task_complete.py",
                scope={"phase": str(args.phase or "unknown"), "task": args.task},
                payload={
                    "task": args.task,
                    "phase": args.phase,
                    "outcome": args.outcome,
                    "duration_minutes": args.duration_minutes,
                    "tests_added": args.tests_added,
                    "files_modified": args.file_modified,
                },
                provenance={"hook": "task_complete"},
            ),
            fail_open=True,
        )
        _, sync_message = sync_agents_memory_section()

        print(f"[Memory] Task learning recorded: {entry.get('task')}")
        print(f"[Memory] {sync_message}")
        return 0
    except Exception as exc:  # pragma: no cover - defensive best-effort hook
        print(f"[Memory] WARNING: TaskComplete hook failed: {exc}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
