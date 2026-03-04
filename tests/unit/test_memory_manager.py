from __future__ import annotations

from datetime import timedelta
import shutil
from pathlib import Path
import uuid

from src.memory.memory_manager import (
    LongTermMemory,
    ShortTermMemory,
    WorkingMemory,
    ensure_memory_layout,
)


def _new_temp_dir() -> Path:
    base = Path.cwd() / "memory_test_runs"
    base.mkdir(parents=True, exist_ok=True)
    run_dir = base / f"memory-tests-{uuid.uuid4().hex[:8]}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def test_working_short_and_long_term_memory_roundtrip(monkeypatch):
    run_dir = _new_temp_dir()
    try:
        memory_root = run_dir / "memory_data"
        monkeypatch.setenv("AI_MEMORY_ROOT", str(memory_root))

        ensure_memory_layout()

        working = WorkingMemory()
        working.update_context("current_task", "memory-integration")
        working.track_file("AGENTS.md", "modified")
        working.track_command("python scripts/memory/session_start.py", success=True)
        working.add_insight("working memory persisted")
        working.add_next_step("wire session end hook")
        saved_path = working.save()

        assert saved_path.exists()
        latest = WorkingMemory.load_latest()
        assert latest is not None
        assert latest["context"]["current_task"] == "memory-integration"
        assert latest["insights"] == ["working memory persisted"]

        short_term = ShortTermMemory()
        short_term.append_event("task_completed", {"task": "15-memory"})
        short_term.append_event("decision", {"decision": "keep hooks best-effort"})

        summary = short_term.summarize_day()
        assert summary["count"] == 2
        assert summary["types"]["task_completed"] == 1
        assert summary["types"]["decision"] == 1

        decisions = short_term.query(event_type="decision", last_n_days=1)
        assert len(decisions) == 1
        assert decisions[0]["decision"] == "keep hooks best-effort"

        long_term = LongTermMemory()
        index = long_term.record_event("task_complete", source="unit-test")
        assert index["event_counters"]["task_complete"] == 1

        output = long_term.write_phase_evolution(
            phase_name="future-memory",
            summary="memory hooks implemented",
            highlights=["2 x task_completed", "1 x decision"],
        )
        assert output.exists()
        assert output.read_text(encoding="utf-8").startswith("# Phase future-memory Evolution")
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_cleanup_expired_working_sessions(monkeypatch):
    run_dir = _new_temp_dir()
    try:
        memory_root = run_dir / "memory_data"
        monkeypatch.setenv("AI_MEMORY_ROOT", str(memory_root))

        paths = ensure_memory_layout()
        session_file = paths.working / "session-stale.json"
        session_file.write_text("{}", encoding="utf-8")

        stale_ts = session_file.stat().st_mtime - timedelta(hours=48).total_seconds()
        # Set file mtime to stale timestamp.
        import os

        os.utime(session_file, (stale_ts, stale_ts))

        removed = WorkingMemory.cleanup_expired(max_age_hours=24)
        assert removed == 1
        assert not session_file.exists()
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)
