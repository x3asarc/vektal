#!/usr/bin/env python3
"""Rebuild memory materialized views from append-only events."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.memory.materializers import (  # noqa: E402
    build_long_term_index,
    build_short_term_view,
    build_working_view,
    discover_event_days,
    discover_sessions,
)
from src.memory.memory_manager import ensure_memory_layout  # noqa: E402


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _checkpoint_path(root: Path | None = None) -> Path:
    paths = ensure_memory_layout(root=root)
    return paths.root / "materializers" / "checkpoint.json"


def _load_checkpoint(root: Path | None = None) -> dict[str, Any] | None:
    path = _checkpoint_path(root=root)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _save_checkpoint(payload: dict[str, Any], *, root: Path | None = None) -> None:
    path = _checkpoint_path(root=root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _changed_days_since(last_run_epoch: float, *, root: Path | None = None) -> list[str]:
    paths = ensure_memory_layout(root=root)
    changed: list[str] = []
    for event_file in sorted(paths.events.glob("*.jsonl")):
        if event_file.stat().st_mtime > last_run_epoch:
            changed.append(event_file.stem)
    return changed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Materialize memory views from append-only event logs.")
    parser.add_argument("--mode", choices=["full", "incremental"], default="full")
    parser.add_argument("--day", help="Optional day override in YYYY-MM-DD format")
    parser.add_argument("--session-id", help="Optional session scope override")
    parser.add_argument("--dry-run", action="store_true", help="Compute views without writing files")
    return parser.parse_args()


def _resolve_days(args: argparse.Namespace, *, root: Path | None = None) -> list[str]:
    if args.day:
        return [args.day]
    if args.mode == "full":
        return discover_event_days(root=root)
    checkpoint = _load_checkpoint(root=root)
    if not checkpoint or "last_run_epoch" not in checkpoint:
        return discover_event_days(root=root)
    return _changed_days_since(float(checkpoint["last_run_epoch"]), root=root)


def run_materialization(args: argparse.Namespace) -> dict[str, Any]:
    days = _resolve_days(args)
    sessions = [args.session_id] if args.session_id else discover_sessions(
        day_from=min(days) if days else None,
        day_to=max(days) if days else None,
    )

    changed_views: list[str] = []
    event_count_total = 0

    for session_id in sessions:
        result = build_working_view(
            session_id,
            day_from=min(days) if days else None,
            day_to=max(days) if days else None,
            write=not args.dry_run,
        )
        event_count_total += int(result.get("event_count") or 0)
        changed_views.append(result["path"])

    for day in days:
        result = build_short_term_view(day, write=not args.dry_run)
        event_count_total += int(result.get("count") or 0)
        changed_views.append(result["path"])

    long_term = build_long_term_index(
        day_from=min(days) if days else None,
        day_to=max(days) if days else None,
        write=not args.dry_run,
    )
    changed_views.append(long_term["path"])

    report = {
        "mode": args.mode,
        "dry_run": bool(args.dry_run),
        "timestamp": _utc_now_iso(),
        "days": days,
        "sessions": sessions,
        "event_count_total": event_count_total,
        "changed_views": changed_views,
    }

    if not args.dry_run:
        _save_checkpoint(
            {
                "last_run_at": report["timestamp"],
                "last_run_epoch": datetime.now(timezone.utc).timestamp(),
                "mode": args.mode,
                "days": days,
                "sessions": sessions,
            }
        )
    return report


def main() -> int:
    args = parse_args()
    report = run_materialization(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

