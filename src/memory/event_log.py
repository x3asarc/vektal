"""Append-only event log primitives for .memory/events JSONL files."""

from __future__ import annotations

from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import time
from typing import Any, Iterable, Iterator, Mapping

from src.memory.event_schema import EventEnvelope, EventType, validate_event
from src.memory.memory_manager import ensure_memory_layout, get_memory_paths
from src.memory.text_sanitizer import sanitize_dict

LOCK_TIMEOUT_SECONDS = 2.0
LOCK_POLL_INTERVAL_SECONDS = 0.01


def _normalize_day(value: date | datetime | str | None = None) -> date:
    if value is None:
        return datetime.now(timezone.utc).date()
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        return datetime.strptime(value, "%Y-%m-%d").date()
    raise ValueError("day must be date/datetime/YYYY-MM-DD")


def event_log_path_for_day(day: date | datetime | str | None = None, *, root: Path | None = None) -> Path:
    """Resolve canonical event log path for a given day."""

    paths = ensure_memory_layout(root=root)
    target_day = _normalize_day(day)
    return paths.events / f"{target_day.strftime('%Y-%m-%d')}.jsonl"


def _acquire_lock(lock_path: Path, *, timeout_seconds: float = LOCK_TIMEOUT_SECONDS) -> bool:
    deadline = time.perf_counter() + timeout_seconds
    while time.perf_counter() < deadline:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            return True
        except FileExistsError:
            time.sleep(LOCK_POLL_INTERVAL_SECONDS)
        except PermissionError:
            # Windows may raise EACCES while another writer is rotating lock ownership.
            time.sleep(LOCK_POLL_INTERVAL_SECONDS)
    return False


def _release_lock(lock_path: Path) -> None:
    lock_path.unlink(missing_ok=True)


def append_event(
    event: EventEnvelope | Mapping[str, Any],
    *,
    root: Path | None = None,
    fail_open: bool = False,
) -> dict[str, Any]:
    """Append one validated event to the canonical daily JSONL log."""

    started = time.perf_counter()
    event_dict = event.to_dict() if isinstance(event, EventEnvelope) else dict(event)
    validated = validate_event(event_dict)
    # Sanitize to prevent Windows-1252 encoding issues
    validated = sanitize_dict(validated)

    target = event_log_path_for_day(validated["created_at"][:10], root=root)
    target.parent.mkdir(parents=True, exist_ok=True)
    lock_path = Path(f"{target}.lock")
    if not _acquire_lock(lock_path):
        if fail_open:
            return {
                "ok": False,
                "path": str(target),
                "event_id": validated["event_id"],
                "error": "lock_timeout",
                "write_duration_ms": round((time.perf_counter() - started) * 1000, 3),
                "bytes_written": 0,
            }
        raise TimeoutError(f"Unable to acquire event log lock: {lock_path}")

    bytes_written = 0
    try:
        line = json.dumps(validated, ensure_ascii=True) + "\n"
        with target.open("a", encoding="utf-8") as handle:
            handle.write(line)
            handle.flush()
        bytes_written = len(line.encode("utf-8"))
    finally:
        _release_lock(lock_path)

    return {
        "ok": True,
        "path": str(target),
        "event_id": validated["event_id"],
        "event_type": validated["event_type"],
        "write_duration_ms": round((time.perf_counter() - started) * 1000, 3),
        "bytes_written": bytes_written,
    }


def _event_files_in_range(
    *,
    root: Path | None = None,
    day_from: date | datetime | str | None = None,
    day_to: date | datetime | str | None = None,
) -> list[Path]:
    paths = get_memory_paths(root=root)
    events_dir = paths.events
    events_dir.mkdir(parents=True, exist_ok=True)
    lower = _normalize_day(day_from) if day_from is not None else None
    upper = _normalize_day(day_to) if day_to is not None else None
    files = sorted(events_dir.glob("*.jsonl"))
    selected: list[Path] = []
    for file_path in files:
        try:
            file_day = datetime.strptime(file_path.stem, "%Y-%m-%d").date()
        except ValueError:
            continue
        if lower and file_day < lower:
            continue
        if upper and file_day > upper:
            continue
        selected.append(file_path)
    return selected


def iter_events(
    *,
    root: Path | None = None,
    day_from: date | datetime | str | None = None,
    day_to: date | datetime | str | None = None,
    session_id: str | None = None,
    event_types: Iterable[EventType | str] | None = None,
    limit: int | None = None,
) -> Iterator[dict[str, Any]]:
    """Iterate validated events with optional filters."""

    allowed_types: set[str] | None = None
    if event_types is not None:
        allowed_types = set()
        for item in event_types:
            allowed_types.add(item.value if isinstance(item, EventType) else str(item))

    yielded = 0
    for file_path in _event_files_in_range(root=root, day_from=day_from, day_to=day_to):
        for line in file_path.read_text(encoding="utf-8").splitlines():
            raw = line.strip()
            if not raw:
                continue
            try:
                parsed = json.loads(raw)
                validated = validate_event(parsed)
            except (json.JSONDecodeError, ValueError):
                continue
            if session_id and validated.get("session_id") != session_id:
                continue
            if allowed_types is not None and validated.get("event_type") not in allowed_types:
                continue
            yield validated
            yielded += 1
            if limit is not None and yielded >= limit:
                return
