#!/usr/bin/env python3
"""SessionEnd memory finalize hook."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.memory.event_log import append_event  # noqa: E402
from src.memory.event_schema import EventType, create_event  # noqa: E402
from src.memory.memory_manager import LongTermMemory, ShortTermMemory, WorkingMemory  # noqa: E402
from scripts.memory.sync_agents_memory import sync_agents_memory_section  # noqa: E402


def _load_context_file(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Persist working/short-term memory at session end.")
    parser.add_argument("--context-file", help="Optional JSON payload describing session context")
    parser.add_argument("--insight", action="append", default=[], help="Insight to append (repeatable)")
    parser.add_argument("--next-step", action="append", default=[], help="Next step to append (repeatable)")
    parser.add_argument("--task", help="Current task id/name")
    parser.add_argument("--status", default="completed", help="Session outcome status")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        payload = _load_context_file(Path(args.context_file).resolve() if args.context_file else None)
        working = WorkingMemory(
            session_id=payload.get("session_id"),
            started_at=payload.get("started_at"),
        )

        working.merge_context(payload.get("context"))
        if args.task:
            working.update_context("current_task", args.task)

        for item in payload.get("recent_files", []):
            path = str(item.get("path") or "")
            action = str(item.get("action") or "updated")
            if path:
                working.track_file(path, action)

        for item in payload.get("recent_commands", []):
            cmd = str(item.get("cmd") or "")
            if not cmd:
                continue
            success = bool(item.get("success", True))
            exit_code = item.get("exit_code")
            working.track_command(cmd, success=success, exit_code=exit_code)

        for insight in payload.get("insights", []):
            working.add_insight(str(insight))
        for insight in args.insight:
            working.add_insight(insight)
        for step in payload.get("next_steps", []):
            working.add_next_step(str(step))
        for step in args.next_step:
            working.add_next_step(step)

        session_file = working.save()

        short_term = ShortTermMemory()
        short_term.append_event(
            "session_end",
            {
                "session_id": working.session_id,
                "status": args.status,
                "task": (working.context or {}).get("current_task"),
                "insight_count": len(working.insights),
            },
        )
        for insight in working.insights:
            short_term.append_event("session_insight", {"session_id": working.session_id, "content": insight})

        LongTermMemory().record_event("session_end", source="session-end-hook")
        append_event(
            create_event(
                event_type=EventType.SESSION_END,
                provider="codex",
                session_id=working.session_id,
                source="scripts/memory/session_end.py",
                scope={"phase": "16"},
                payload={
                    "status": args.status,
                    "task": (working.context or {}).get("current_task"),
                    "insight_count": len(working.insights),
                    "next_step_count": len(working.next_steps),
                },
                provenance={"hook": "session_end"},
            ),
            fail_open=True,
        )
        _, sync_message = sync_agents_memory_section()

        print(f"[Memory] Session persisted: {session_file.name}")
        print(f"[Memory] Short-term insights appended: {len(working.insights)}")
        print(f"[Memory] {sync_message}")
        return 0
    except Exception as exc:  # pragma: no cover - defensive best-effort hook
        print(f"[Memory] WARNING: SessionEnd finalize failed: {exc}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
