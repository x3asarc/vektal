from __future__ import annotations

import json
from pathlib import Path
import shutil
import uuid

from scripts.memory.pre_tool_update import _extract_command, record_pre_tool_event


def _new_run_dir() -> Path:
    base = Path.cwd() / "memory_test_runs"
    base.mkdir(parents=True, exist_ok=True)
    run_dir = base / f"pretool-{uuid.uuid4().hex[:8]}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def test_extract_command_nested_payload():
    payload = {
        "tool": "Bash",
        "tool_input": {
            "command": "pytest tests/unit/test_memory_pretool_update.py -q",
        },
    }
    cmd = _extract_command(payload)
    assert cmd == "pytest tests/unit/test_memory_pretool_update.py -q"


def test_record_pre_tool_event_persists_session(monkeypatch):
    run_dir = _new_run_dir()
    try:
        memory_root = run_dir / "memory_data"
        monkeypatch.setenv("AI_MEMORY_ROOT", str(memory_root))

        payload = json.dumps({"tool_input": {"command": "git status"}})
        result = record_pre_tool_event(
            provider="codex",
            session_key="session-abc",
            window_hint="codex-proof",
            raw_input=payload,
        )
        session_file = result["session_file"]
        assert session_file.exists()
        data = json.loads(session_file.read_text(encoding="utf-8"))
        assert data["context"]["provider"] == "codex"
        assert data["context"]["last_command"] == "git status"
        assert data["recent_commands"][-1]["stage"] == "pre_tool"
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)
