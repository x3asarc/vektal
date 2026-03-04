from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import shutil
import uuid

import pytest

from src.memory.event_log import append_event, event_log_path_for_day, iter_events
from src.memory.event_schema import EventType, MAX_PAYLOAD_BYTES, create_event, validate_event


def _new_run_dir() -> Path:
    base = Path.cwd() / "memory_test_runs"
    base.mkdir(parents=True, exist_ok=True)
    run_dir = base / f"event-log-{uuid.uuid4().hex[:8]}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def _sample_event(*, session_id: str = "session-codex-test") -> dict[str, object]:
    return create_event(
        event_type=EventType.PRE_TOOL,
        provider="codex",
        session_id=session_id,
        source="unit-test",
        scope={"phase": "16", "task": "16-01"},
        payload={"command": "git status"},
        provenance={"origin": "test"},
    ).to_dict()


def test_validate_event_accepts_canonical_envelope():
    event = _sample_event()
    validated = validate_event(event)
    assert validated["event_type"] == EventType.PRE_TOOL.value
    assert validated["schema_version"] == 1
    assert validated["scope"]["phase"] == "16"


def test_validate_event_rejects_missing_required_field():
    event = _sample_event()
    event["provider"] = ""
    with pytest.raises(ValueError):
        validate_event(event)


def test_append_and_iter_roundtrip(monkeypatch):
    run_dir = _new_run_dir()
    try:
        memory_root = run_dir / "memory_data"
        monkeypatch.setenv("AI_MEMORY_ROOT", str(memory_root))

        event = _sample_event()
        result = append_event(event)
        assert result["ok"] is True
        assert result["bytes_written"] > 0

        rows = list(iter_events(session_id=event["session_id"]))
        assert len(rows) == 1
        assert rows[0]["payload"]["command"] == "git status"
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_concurrent_append_smoke(monkeypatch):
    run_dir = _new_run_dir()
    try:
        memory_root = run_dir / "memory_data"
        monkeypatch.setenv("AI_MEMORY_ROOT", str(memory_root))

        def _write_one(index: int) -> dict[str, object]:
            event = create_event(
                event_type=EventType.POST_TOOL,
                provider="codex",
                session_id=f"session-codex-{index}",
                source="concurrency-test",
                scope={"phase": "16"},
                payload={"idx": index},
                provenance={"thread": index},
            )
            return append_event(event)

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(_write_one, range(40)))

        assert all(result["ok"] for result in results)
        target = event_log_path_for_day()
        lines = target.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 40
        parsed = [json.loads(line) for line in lines]
        assert all("event_id" in row for row in parsed)
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_payload_size_limit_enforced():
    oversized = "x" * (MAX_PAYLOAD_BYTES + 500)
    with pytest.raises(ValueError):
        create_event(
            event_type=EventType.SESSION_START,
            provider="codex",
            session_id="session-codex-oversized",
            source="unit-test",
            payload={"blob": oversized},
        )

