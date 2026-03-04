from __future__ import annotations

import io
from pathlib import Path
import shutil
import sys
import uuid

import pytest

import scripts.memory.pre_tool_update as pre_tool_update
import scripts.memory.session_start as session_start
from src.assistant.context_broker import assemble_context
from src.memory.event_log import iter_events
from src.memory.event_schema import EventType


def _new_run_dir() -> Path:
    base = Path.cwd() / "memory_test_runs"
    base.mkdir(parents=True, exist_ok=True)
    run_dir = base / f"phase16-e2e-{uuid.uuid4().hex[:8]}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def test_graph_attempt_occurs_on_every_broker_call():
    graph_bundle = assemble_context(
        query="what triggers pre_tool update",
        graph_fetcher=lambda _query, _top_k: ["scripts/memory/pre_tool_update.py -> src/assistant/context_broker.py"],
        snapshot_fetcher=lambda _query, _top_k: [],
        docs_limit=0,
    )
    fallback_bundle = assemble_context(
        query="zzzxxyyqqq",
        graph_fetcher=lambda _query, _top_k: (_ for _ in ()).throw(RuntimeError("graph down")),
        snapshot_fetcher=lambda _query, _top_k: [],
        docs_limit=0,
    )

    assert graph_bundle.telemetry["graph_attempted"] is True
    assert fallback_bundle.telemetry["graph_attempted"] is True
    assert graph_bundle.telemetry["graph_used"] is True
    assert fallback_bundle.telemetry["fallback_used"] is True
    assert fallback_bundle.telemetry["fallback_reason"] in {"graph_error", "docs_used", "baseline_used", "token_compaction"}


def test_hook_pipeline_updates_memory_between_sessions(monkeypatch):
    run_dir = _new_run_dir()
    try:
        memory_root = run_dir / ".memory"
        monkeypatch.setenv("AI_MEMORY_ROOT", str(memory_root))
        monkeypatch.setattr(session_start, "sync_agents_memory_section", lambda: (False, "noop"))
        monkeypatch.setattr(session_start, "_refresh_context_docs", lambda _sha: [])

        assert session_start.main() == 0
        first = pre_tool_update.record_pre_tool_event(
            provider="codex",
            session_key="phase16-a",
            window_hint="a",
            raw_input='{"tool_input":{"command":"git status"}}',
        )
        second = pre_tool_update.record_pre_tool_event(
            provider="codex",
            session_key="phase16-b",
            window_hint="b",
            raw_input='{"tool_input":{"command":"git status"}}',
        )

        assert first["event_write"]["ok"] is True
        assert second["event_write"]["ok"] is True
        assert second["peer"] is not None

        event_types = {event["event_type"] for event in iter_events(root=memory_root)}
        assert EventType.SESSION_START.value in event_types
        assert EventType.PRE_TOOL.value in event_types
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_non_blocking_pretool_contract_preserved(monkeypatch):
    run_dir = _new_run_dir()
    try:
        memory_root = run_dir / ".memory"
        monkeypatch.setenv("AI_MEMORY_ROOT", str(memory_root))
        monkeypatch.setattr(pre_tool_update, "append_event", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
        monkeypatch.setattr(sys, "argv", ["pre_tool_update.py", "--provider", "codex", "--session-key", "phase16-safe"])
        monkeypatch.setattr(sys, "stdin", io.StringIO('{"tool_input":{"command":"git status"}}'))
        assert pre_tool_update.main() == 0
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)
