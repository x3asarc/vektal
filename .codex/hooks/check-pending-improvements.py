#!/usr/bin/env python3
"""
SessionStart Hook: Check for pending auto-improvements.
Notifies user of escalated improvements that need review.
"""

import json
import subprocess
import sys
from pathlib import Path


def _startup_watchdog_and_heartbeat() -> None:
    commands = [
        [
            sys.executable,
            "scripts/hooks/antigravity_watchdog.py",
            "--spawn",
            "--provider",
            "claude",
        ],
        [
            sys.executable,
            "scripts/hooks/antigravity_notify.py",
            "--provider",
            "claude",
            "--source",
            "session_start",
            "--heartbeat",
            "--window-hint",
            "claude",
        ],
    ]
    for command in commands:
        try:
            subprocess.run(command, check=False, capture_output=True, text=True)
        except Exception:
            continue


def _notify_pending_improvements(pending_count: int) -> None:
    title = "Antigravity: Claude Review Needed"
    message = f"{pending_count} pending improvement(s) require manual review."
    try:
        subprocess.run(
            [
                sys.executable,
                "scripts/hooks/antigravity_notify.py",
                "--provider",
                "claude",
                "--source",
                "session_start",
                "--force",
                "--title",
                title,
                "--message",
                message,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception:
        # Never block session startup due to optional notification plumbing.
        return


def main() -> int:
    _startup_watchdog_and_heartbeat()
    escalation_file = Path(".claude/escalations/pending-improvements.json")

    if not escalation_file.exists():
        print("No pending improvements")
        return 0

    try:
        with escalation_file.open(encoding="utf-8") as handle:
            escalations = json.load(handle)
    except Exception as exc:
        print(f"Could not read escalations: {exc}")
        return 0

    pending = [entry for entry in escalations if entry.get("status") == "pending"]

    if not pending:
        print("No pending improvements")
        return 0

    _notify_pending_improvements(len(pending))

    print(f"\n{len(pending)} pending improvement(s) need review:")
    print(f"  Location: {escalation_file}")
    print()

    for i, improvement in enumerate(pending[:3], 1):
        print(f"  {i}. Phase {improvement.get('phase')}-{improvement.get('plan')}")
        print(f"     Root cause: {improvement.get('root_cause')}")
        print(f"     Proposed: {improvement.get('proposed_fix', 'N/A')[:60]}...")
        print(f"     Confidence: {improvement.get('confidence', 0):.0%}")
        print()

    if len(pending) > 3:
        print(f"  ... and {len(pending) - 3} more")
        print()

    print("  Review file and apply manually if appropriate")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
