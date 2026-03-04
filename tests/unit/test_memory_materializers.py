from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import uuid

from scripts.memory.materialize_views import run_materialization
from src.memory.event_log import append_event, event_log_path_for_day
from src.memory.event_schema import EventType, create_event
from src.memory.materializers import build_long_term_index, build_short_term_view, build_working_view


def _new_run_dir() -> Path:
    base = Path.cwd() / "memory_test_runs"
    base.mkdir(parents=True, exist_ok=True)
    run_dir = base / f"materializers-{uuid.uuid4().hex[:8]}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def _write_sample_events() -> None:
    append_event(
        create_event(
            event_type=EventType.SESSION_START,
            provider="codex",
            session_id="session-codex-a",
            source="test",
            created_at="2026-03-03T10:00:00Z",
            payload={"context": {"current_task": "phase16"}},
        )
    )
    append_event(
        create_event(
            event_type=EventType.PRE_TOOL,
            provider="codex",
            session_id="session-codex-a",
            source="test",
            created_at="2026-03-03T10:01:00Z",
            payload={"command": "git status", "file_path": "src/memory/event_log.py", "action": "read"},
        )
    )
    append_event(
        create_event(
            event_type=EventType.PHASE_COMPLETE,
            provider="codex",
            session_id="session-codex-a",
            source="test",
            created_at="2026-03-03T10:02:00Z",
            payload={"phase": "16", "summary": "materializers online"},
        )
    )


def _file_hash(path: Path) -> str:
    content = path.read_bytes()
    return hashlib.sha256(content).hexdigest()


def test_materializers_are_deterministic(monkeypatch):
    run_dir = _new_run_dir()
    try:
        memory_root = run_dir / "memory_data"
        monkeypatch.setenv("AI_MEMORY_ROOT", str(memory_root))
        _write_sample_events()

        first = build_working_view("session-codex-a")
        first_hash = _file_hash(Path(first["path"]))
        second = build_working_view("session-codex-a")
        second_hash = _file_hash(Path(second["path"]))
        assert first_hash == second_hash

        day_first = build_short_term_view("2026-03-03")
        day_first_hash = _file_hash(Path(day_first["path"]))
        day_second = build_short_term_view("2026-03-03")
        day_second_hash = _file_hash(Path(day_second["path"]))
        assert day_first_hash == day_second_hash

        index_first = build_long_term_index()
        index_first_hash = _file_hash(Path(index_first["path"]))
        index_second = build_long_term_index()
        index_second_hash = _file_hash(Path(index_second["path"]))
        assert index_first_hash == index_second_hash
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_invalid_event_lines_are_ignored(monkeypatch):
    run_dir = _new_run_dir()
    try:
        memory_root = run_dir / "memory_data"
        monkeypatch.setenv("AI_MEMORY_ROOT", str(memory_root))
        _write_sample_events()
        event_path = event_log_path_for_day("2026-03-03")
        with event_path.open("a", encoding="utf-8") as handle:
            handle.write("not-json\n")
            handle.write("{\"bad\": true}\n")

        result = build_short_term_view("2026-03-03")
        assert result["count"] == 3
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_provenance_is_present_in_materialized_outputs(monkeypatch):
    run_dir = _new_run_dir()
    try:
        memory_root = run_dir / "memory_data"
        monkeypatch.setenv("AI_MEMORY_ROOT", str(memory_root))
        _write_sample_events()

        working = build_working_view("session-codex-a")
        view = working["view"]
        assert view["source_event_ids"]
        assert all(item.startswith("evt-") for item in view["source_event_ids"])

        short_term = build_short_term_view("2026-03-03")
        assert short_term["rows"][0]["source_event_id"].startswith("evt-")
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_incremental_mode_matches_full_after_change(monkeypatch):
    run_dir = _new_run_dir()
    try:
        memory_root = run_dir / "memory_data"
        monkeypatch.setenv("AI_MEMORY_ROOT", str(memory_root))
        _write_sample_events()

        args_full = type("Args", (), {"mode": "full", "day": None, "session_id": None, "dry_run": False})()
        run_materialization(args_full)

        append_event(
            create_event(
                event_type=EventType.POST_TOOL,
                provider="codex",
                session_id="session-codex-a",
                source="test",
                created_at="2026-03-03T10:03:00Z",
                payload={"command": "pytest -q tests/unit/test_memory_materializers.py"},
            )
        )

        args_inc = type("Args", (), {"mode": "incremental", "day": None, "session_id": None, "dry_run": False})()
        run_materialization(args_inc)
        inc_working = Path(memory_root / "working" / "session-codex-a.json").read_text(encoding="utf-8")

        run_materialization(args_full)
        full_working = Path(memory_root / "working" / "session-codex-a.json").read_text(encoding="utf-8")

        assert json.loads(inc_working) == json.loads(full_working)
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)

