#!/usr/bin/env python3
"""PreTool memory live-sync updater for Codex terminals."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import sys
import time
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.assistant.context_broker import assemble_context  # noqa: E402
from src.memory.event_log import append_event  # noqa: E402
from src.memory.event_schema import EventType, create_event  # noqa: E402
from src.memory.memory_manager import ShortTermMemory, WorkingMemory, get_memory_paths  # noqa: E402


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    candidate = str(value).strip()
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(candidate)
    except ValueError:
        return None


def _to_safe_id(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "-", value).strip("-").lower()
    return cleaned or "default"


def _extract_command(payload: Any, *, depth: int = 0) -> str | None:
    if depth > 6:
        return None
    if isinstance(payload, str):
        raw = payload.strip()
        if not raw:
            return None
        if raw.startswith("{") or raw.startswith("["):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                return raw
            return _extract_command(parsed, depth=depth + 1)
        return raw

    if isinstance(payload, dict):
        for key in ("command", "cmd"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        for key in ("tool_input", "input", "params", "arguments", "payload", "data"):
            if key in payload:
                result = _extract_command(payload[key], depth=depth + 1)
                if result:
                    return result
        for value in payload.values():
            result = _extract_command(value, depth=depth + 1)
            if result:
                return result
        return None

    if isinstance(payload, list):
        for item in payload:
            result = _extract_command(item, depth=depth + 1)
            if result:
                return result
    return None


def _load_payload(raw_input: str) -> Any:
    if not raw_input.strip():
        return {}
    try:
        return json.loads(raw_input)
    except json.JSONDecodeError:
        return raw_input.strip()


def _latest_peer_session(
    *,
    own_session_id: str,
    max_age_minutes: int = 20,
) -> dict[str, Any] | None:
    paths = get_memory_paths()
    window = datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)
    files = sorted(paths.working.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for file_path in files:
        if file_path.stem == own_session_id:
            continue
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        recent_ts = _parse_iso(payload.get("updated_at")) or _parse_iso(payload.get("started_at"))
        if not recent_ts:
            recent_ts = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
        if recent_ts < window:
            return None
        return payload
    return None


def record_pre_tool_event(
    *,
    provider: str,
    session_key: str,
    window_hint: str | None,
    raw_input: str,
) -> dict[str, Any]:
    started = time.perf_counter()
    payload = _load_payload(raw_input)
    command = _extract_command(payload)

    # GRAPH-FIRST: Auto-query Neo4j/Graphiti knowledge graph before every tool use
    # This ensures graph context is ALWAYS retrieved automatically
    broker_bundle = assemble_context(
        query=command or "pre_tool_command",
        top_k=5,  # Increased from 1 for better context coverage
        target_tokens=1000,  # Reasonable token budget for hook context
    )

    session_id = f"session-{_to_safe_id(provider)}-{_to_safe_id(session_key)}"
    working = WorkingMemory.load_for_session(session_id=session_id)
    working.update_context("provider", provider)
    if window_hint:
        working.update_context("window_hint", window_hint)
    working.update_context("last_seen_at", datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"))
    if command:
        working.track_command(command, success=None, stage="pre_tool")
        working.update_context("last_command", command)
    working.update_context("last_broker_telemetry", broker_bundle.telemetry)
    session_file = working.save()

    short_term = ShortTermMemory()
    short_term.append_event(
        "command_observed",
        {
            "provider": provider,
            "session_id": session_id,
            "window_hint": window_hint,
            "command": command,
        },
    )
    event_write = append_event(
        create_event(
            event_type=EventType.PRE_TOOL,
            provider=provider,
            session_id=session_id,
            source="scripts/memory/pre_tool_update.py",
            scope={"phase": "16"},
            payload={
                "command": command,
                "window_hint": window_hint,
                "broker_telemetry": broker_bundle.telemetry,
            },
            provenance={"hook": "pre_tool", "provider": provider},
        ),
        fail_open=True,
    )
    peer = _latest_peer_session(own_session_id=session_id)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
    return {
        "session_file": session_file,
        "command": command,
        "peer": peer,
        "event_write": event_write,
        "broker_telemetry": broker_bundle.telemetry,
        "write_duration_ms": elapsed_ms,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record pre-tool memory activity for live terminal sync.")
    parser.add_argument("--provider", default="codex", help="Provider label")
    parser.add_argument("--session-key", required=True, help="Stable per-terminal/session key")
    parser.add_argument("--window-hint", help="Optional terminal/window hint")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    raw_input = sys.stdin.read()
    try:
        result = record_pre_tool_event(
            provider=args.provider,
            session_key=args.session_key,
            window_hint=args.window_hint,
            raw_input=raw_input,
        )
        if result.get("peer"):
            peer = result["peer"]
            peer_task = (peer.get("context") or {}).get("current_task") or "N/A"
            peer_cmd = (peer.get("context") or {}).get("last_command") or "N/A"
            print(f"[Memory] Peer active: {peer.get('session_id')} task={peer_task} cmd={peer_cmd}")
        return 0
    except Exception as exc:  # pragma: no cover - defensive best-effort hook
        print(f"[Memory] WARNING: pre-tool live sync failed: {exc}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
