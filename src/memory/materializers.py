"""Replay-based materializers for working, short-term, and long-term memory views."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from src.memory.event_log import iter_events
from src.memory.memory_manager import ensure_memory_layout, get_memory_paths

EPOCH_ISO = "1970-01-01T00:00:00Z"


def _sorted_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(events, key=lambda item: (str(item.get("created_at", "")), str(item.get("event_id", ""))))


def _write_json(path: Path, payload: dict[str, Any], *, write: bool) -> None:
    if not write:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]], *, write: bool) -> None:
    if not write:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(row, ensure_ascii=True, sort_keys=True) for row in rows]
    if lines:
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        path.write_text("", encoding="utf-8")


def _extract_commands(payload: dict[str, Any]) -> list[str]:
    commands: list[str] = []
    value = payload.get("command")
    if isinstance(value, str) and value.strip():
        commands.append(value.strip())
    nested = payload.get("commands")
    if isinstance(nested, list):
        for item in nested:
            if isinstance(item, str) and item.strip():
                commands.append(item.strip())
    return commands


def _extract_file_events(payload: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    file_path = payload.get("file_path")
    action = payload.get("action")
    if isinstance(file_path, str) and file_path.strip():
        rows.append({"path": file_path.strip(), "action": str(action or "unknown")})
    bulk = payload.get("files")
    if isinstance(bulk, list):
        for item in bulk:
            if not isinstance(item, dict):
                continue
            path = item.get("path")
            if isinstance(path, str) and path.strip():
                rows.append({"path": path.strip(), "action": str(item.get("action") or "unknown")})
    return rows


def build_working_view(
    session_id: str,
    *,
    root: Path | None = None,
    day_from: str | None = None,
    day_to: str | None = None,
    write: bool = True,
) -> dict[str, Any]:
    """Build `.memory/working/{session_id}.json` from append-only events."""

    paths = ensure_memory_layout(root=root)
    events = list(iter_events(root=root, day_from=day_from, day_to=day_to, session_id=session_id))
    ordered = _sorted_events(events)

    context: dict[str, Any] = {}
    recent_commands: list[dict[str, Any]] = []
    recent_files: list[dict[str, Any]] = []
    insights: list[str] = []
    next_steps: list[str] = []
    source_event_ids: list[str] = []

    for event in ordered:
        payload = dict(event.get("payload") or {})
        source_event_ids.append(str(event.get("event_id") or ""))

        payload_context = payload.get("context")
        if isinstance(payload_context, dict):
            context.update(payload_context)

        for command in _extract_commands(payload):
            recent_commands.append(
                {
                    "cmd": command,
                    "timestamp": event.get("created_at"),
                    "stage": event.get("event_type"),
                }
            )

        for file_event in _extract_file_events(payload):
            recent_files.append(
                {
                    "path": file_event["path"],
                    "action": file_event["action"],
                    "timestamp": event.get("created_at"),
                }
            )

        insight = payload.get("insight")
        if isinstance(insight, str) and insight.strip():
            insights.append(insight.strip())
        payload_insights = payload.get("insights")
        if isinstance(payload_insights, list):
            for item in payload_insights:
                if isinstance(item, str) and item.strip():
                    insights.append(item.strip())

        step = payload.get("next_step")
        if isinstance(step, str) and step.strip():
            next_steps.append(step.strip())
        payload_steps = payload.get("next_steps")
        if isinstance(payload_steps, list):
            for item in payload_steps:
                if isinstance(item, str) and item.strip():
                    next_steps.append(item.strip())

    started_at = EPOCH_ISO
    updated_at = EPOCH_ISO
    if ordered:
        started_at = str(ordered[0].get("created_at") or EPOCH_ISO)
        updated_at = str(ordered[-1].get("created_at") or EPOCH_ISO)

    view = {
        "session_id": session_id,
        "started_at": started_at,
        "updated_at": updated_at,
        "context": context,
        "recent_files": recent_files[-200:],
        "recent_commands": recent_commands[-200:],
        "insights": insights[-200:],
        "next_steps": next_steps[-200:],
        "source_event_ids": [item for item in source_event_ids if item][-1000:],
    }

    target = paths.working / f"{session_id}.json"
    _write_json(target, view, write=write)
    return {
        "path": str(target),
        "session_id": session_id,
        "event_count": len(ordered),
        "view": view,
    }


def _summarize_event(event: dict[str, Any]) -> str:
    payload = dict(event.get("payload") or {})
    command = payload.get("command")
    if isinstance(command, str) and command.strip():
        return command.strip()
    if payload:
        keys = sorted(payload.keys())
        return f"payload_keys={','.join(keys)}"
    return "no_payload"


def build_short_term_view(
    day: str,
    *,
    root: Path | None = None,
    write: bool = True,
) -> dict[str, Any]:
    """Build `.memory/short-term/{day}.jsonl` from event logs for one day."""

    paths = ensure_memory_layout(root=root)
    events = _sorted_events(list(iter_events(root=root, day_from=day, day_to=day)))
    rows: list[dict[str, Any]] = []
    for event in events:
        rows.append(
            {
                "timestamp": event.get("created_at"),
                "type": event.get("event_type"),
                "session_id": event.get("session_id"),
                "summary": _summarize_event(event),
                "source_event_id": event.get("event_id"),
                "provenance": event.get("provenance") or {},
            }
        )
    target = paths.short_term / f"{day}.jsonl"
    _write_jsonl(target, rows, write=write)
    return {"path": str(target), "date": day, "count": len(rows), "rows": rows}


def build_long_term_index(
    *,
    root: Path | None = None,
    day_from: str | None = None,
    day_to: str | None = None,
    write: bool = True,
) -> dict[str, Any]:
    """Build deterministic long-term index from append-only events."""

    paths = ensure_memory_layout(root=root)
    events = _sorted_events(list(iter_events(root=root, day_from=day_from, day_to=day_to)))

    counters: Counter[str] = Counter()
    phase_summaries: list[dict[str, Any]] = []
    last_updated = EPOCH_ISO
    for event in events:
        event_type = str(event.get("event_type") or "unknown")
        counters[event_type] += 1
        last_updated = str(event.get("created_at") or last_updated)
        if event_type == "phase_complete":
            payload = dict(event.get("payload") or {})
            phase = payload.get("phase")
            if phase:
                phase_summaries.append(
                    {
                        "phase": str(phase),
                        "summary": str(payload.get("summary") or ""),
                        "updated_at": str(event.get("created_at") or EPOCH_ISO),
                        "source_event_id": str(event.get("event_id") or ""),
                    }
                )

    index = {
        "version": 1,
        "generated_from": "src.memory.materializers.build_long_term_index",
        "last_updated": last_updated,
        "event_counters": {key: counters[key] for key in sorted(counters)},
        "phase_summaries": phase_summaries,
    }

    _write_json(paths.long_term_index, index, write=write)
    return {"path": str(paths.long_term_index), "event_count": len(events), "index": index}


def discover_event_days(*, root: Path | None = None) -> list[str]:
    """List event days from `.memory/events/*.jsonl`."""

    paths = ensure_memory_layout(root=root)
    days = []
    for file_path in sorted(paths.events.glob("*.jsonl")):
        if file_path.stem:
            days.append(file_path.stem)
    return days


def discover_sessions(
    *,
    root: Path | None = None,
    day_from: str | None = None,
    day_to: str | None = None,
) -> list[str]:
    """List unique session IDs from event logs."""

    sessions = {str(event.get("session_id")) for event in iter_events(root=root, day_from=day_from, day_to=day_to)}
    return sorted(item for item in sessions if item and item != "None")

