#!/usr/bin/env python3
"""CLI writer for canonical memory events."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.memory.event_log import append_event  # noqa: E402
from src.memory.event_schema import EventType, create_event  # noqa: E402


def _safe_id(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "-", value).strip("-").lower()
    return cleaned or "default"


def _parse_json_object(raw: str, *, field_name: str) -> dict[str, Any]:
    candidate = raw.strip()
    if len(candidate) >= 2 and candidate[0] == "'" and candidate[-1] == "'":
        candidate = candidate[1:-1]
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{field_name} must be valid JSON object") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"{field_name} must be a JSON object")
    return parsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write validated events to .memory/events/YYYY-MM-DD.jsonl")
    parser.add_argument("--event-type", required=True, choices=[item.value for item in EventType], help="Event type")
    parser.add_argument("--provider", default="codex", help="Provider name, for example: codex")
    parser.add_argument("--session-key", required=True, help="Stable terminal/session key")
    parser.add_argument("--source", default="record-event-cli", help="Event source label")
    parser.add_argument("--scope", default="{}", help="JSON object with scope metadata")
    parser.add_argument("--payload", default="{}", help="JSON object payload")
    parser.add_argument("--provenance", default="{}", help="JSON object provenance fields")
    parser.add_argument("--dry-run", action="store_true", help="Validate only, do not append")
    parser.add_argument("--fail-open", action="store_true", help="Return 0 even if append fails")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        scope = _parse_json_object(args.scope, field_name="scope")
        payload = _parse_json_object(args.payload, field_name="payload")
        provenance = _parse_json_object(args.provenance, field_name="provenance")
        session_id = f"session-{_safe_id(args.provider)}-{_safe_id(args.session_key)}"
        envelope = create_event(
            event_type=args.event_type,
            provider=args.provider,
            session_id=session_id,
            source=args.source,
            scope=scope,
            payload=payload,
            provenance=provenance,
        )
        if args.dry_run:
            print(json.dumps(envelope.to_dict(), ensure_ascii=True))
            print("[event] dry_run=ok")
            return 0

        result = append_event(envelope, fail_open=args.fail_open)
        tag = "PASS" if result.get("ok") else "WARN"
        print(
            f"[event:{tag}] id={result.get('event_id')} type={args.event_type} "
            f"path={result.get('path')} duration_ms={result.get('write_duration_ms')}"
        )
        if not result.get("ok") and not args.fail_open:
            return 1
        return 0
    except Exception as exc:
        print(f"[event:ERROR] {exc}")
        return 0 if args.fail_open else 1


if __name__ == "__main__":
    raise SystemExit(main())
