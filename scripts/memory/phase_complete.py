#!/usr/bin/env python3
"""PhaseComplete memory synthesis hook."""

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
    parser = argparse.ArgumentParser(description="Synthesize short-term memory into long-term phase notes.")
    parser.add_argument("--phase", required=True, help="Phase label (for example: 15 or future-memory)")
    parser.add_argument("--summary", required=True, help="High-level phase summary")
    parser.add_argument("--days", type=int, default=30, help="How many recent days to scan for highlights")
    return parser.parse_args()


def _build_highlights(events: list[dict]) -> list[str]:
    if not events:
        return []
    totals: dict[str, int] = {}
    for event in events:
        key = str(event.get("type") or "unknown")
        totals[key] = totals.get(key, 0) + 1
    return [f"{count} x {event_type}" for event_type, count in sorted(totals.items())]


def main() -> int:
    args = parse_args()
    try:
        short_term = ShortTermMemory()
        events = short_term.query(last_n_days=args.days, limit=2000)
        highlights = _build_highlights(events)

        long_term = LongTermMemory()
        output = long_term.write_phase_evolution(
            phase_name=args.phase,
            summary=args.summary,
            highlights=highlights,
        )
        long_term.record_event("phase_complete", source="phase-complete-hook")
        short_term.append_event(
            "phase_completed",
            {
                "phase": args.phase,
                "summary": args.summary,
                "highlight_count": len(highlights),
                "long_term_path": output.as_posix(),
            },
        )
        append_event(
            create_event(
                event_type=EventType.PHASE_COMPLETE,
                provider="codex",
                session_id=f"session-codex-phase-{args.phase}",
                source="scripts/memory/phase_complete.py",
                scope={"phase": args.phase},
                payload={
                    "phase": args.phase,
                    "summary": args.summary,
                    "highlight_count": len(highlights),
                    "long_term_path": output.as_posix(),
                },
                provenance={"hook": "phase_complete"},
            ),
            fail_open=True,
        )
        _, sync_message = sync_agents_memory_section()

        print(f"[Memory] Phase synthesis written: {output}")
        print(f"[Memory] Highlights: {len(highlights)}")
        print(f"[Memory] {sync_message}")
        return 0
    except Exception as exc:  # pragma: no cover - defensive best-effort hook
        print(f"[Memory] WARNING: PhaseComplete hook failed: {exc}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
