from __future__ import annotations

import io
from pathlib import Path
import shutil
import sys
import uuid

import scripts.memory.phase_complete as phase_complete
import scripts.memory.pre_tool_update as pre_tool_update
import scripts.memory.session_end as session_end
import scripts.memory.session_start as session_start
import scripts.memory.task_complete as task_complete
from src.memory.event_log import iter_events


def _new_run_dir() -> Path:
    base = Path.cwd() / "memory_test_runs"
    base.mkdir(parents=True, exist_ok=True)
    run_dir = base / f"hook-lifecycle-{uuid.uuid4().hex[:8]}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def test_lifecycle_event_coverage(monkeypatch):
    run_dir = _new_run_dir()
    try:
        memory_root = run_dir / "memory_data"
        monkeypatch.setenv("AI_MEMORY_ROOT", str(memory_root))

        monkeypatch.setattr(session_start, "sync_agents_memory_section", lambda: (False, "noop"))
        monkeypatch.setattr(session_start, "_refresh_context_docs", lambda _sha: [])
        monkeypatch.setattr(session_end, "sync_agents_memory_section", lambda: (False, "noop"))
        monkeypatch.setattr(task_complete, "sync_agents_memory_section", lambda: (False, "noop"))
        monkeypatch.setattr(phase_complete, "sync_agents_memory_section", lambda: (False, "noop"))

        assert session_start.main() == 0
        result = pre_tool_update.record_pre_tool_event(
            provider="codex",
            session_key="hook-a",
            window_hint="w-a",
            raw_input='{"tool_input":{"command":"git status"}}',
        )
        assert result["event_write"]["ok"] is True
        assert result["write_duration_ms"] < 500

        monkeypatch.setattr(sys, "argv", ["session_end.py", "--task", "hook-task", "--status", "ok"])
        assert session_end.main() == 0

        monkeypatch.setattr(sys, "argv", ["task_complete.py", "--task", "16-05", "--phase", "16"])
        assert task_complete.main() == 0

        monkeypatch.setattr(sys, "argv", ["phase_complete.py", "--phase", "16", "--summary", "done"])
        assert phase_complete.main() == 0

        types = {event["event_type"] for event in iter_events(root=memory_root)}
        assert {"session_start", "pre_tool", "session_end", "task_complete", "phase_complete"} <= types
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_cross_terminal_peer_visibility(monkeypatch):
    run_dir = _new_run_dir()
    try:
        memory_root = run_dir / "memory_data"
        monkeypatch.setenv("AI_MEMORY_ROOT", str(memory_root))

        pre_tool_update.record_pre_tool_event(
            provider="codex",
            session_key="terminal-a",
            window_hint="A",
            raw_input='{"tool_input":{"command":"python a.py"}}',
        )
        second = pre_tool_update.record_pre_tool_event(
            provider="codex",
            session_key="terminal-b",
            window_hint="B",
            raw_input='{"tool_input":{"command":"python b.py"}}',
        )
        assert second["peer"] is not None
        assert second["peer"]["session_id"].endswith("terminal-a")
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_pretool_main_is_non_blocking_on_event_failure(monkeypatch):
    run_dir = _new_run_dir()
    try:
        memory_root = run_dir / "memory_data"
        monkeypatch.setenv("AI_MEMORY_ROOT", str(memory_root))
        monkeypatch.setattr(pre_tool_update, "append_event", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
        monkeypatch.setattr(sys, "argv", ["pre_tool_update.py", "--provider", "codex", "--session-key", "x"])
        monkeypatch.setattr(sys, "stdin", io.StringIO('{"tool_input":{"command":"git status"}}'))
        assert pre_tool_update.main() == 0
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)

