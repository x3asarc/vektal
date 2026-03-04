from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import shutil
import uuid

from scripts.governance.context_os_gate import run_gate
from src.memory.event_log import append_event
from src.memory.event_schema import EventType, create_event
from src.memory.memory_manager import ensure_memory_layout


def _new_run_dir() -> Path:
    base = Path.cwd() / "memory_test_runs"
    base.mkdir(parents=True, exist_ok=True)
    run_dir = base / f"context-os-gate-{uuid.uuid4().hex[:8]}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def _write_docs(repo_root: Path, *, now: datetime, age_hours: float = 0.1) -> None:
    docs_dir = repo_root / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    for rel in ["AGENT_START_HERE.md", "FOLDER_SUMMARIES.md", "CONTEXT_LINK_MAP.md"]:
        target = docs_dir / rel
        target.write_text(f"# {rel}\n", encoding="utf-8")
        mtime = (now - timedelta(hours=age_hours)).timestamp()
        os.utime(target, (mtime, mtime))


def _append_pre_tool_event(
    *,
    memory_root: Path,
    created_at: datetime,
    session_id: str,
    graph_attempted: bool,
    assembled_tokens: int,
    latency_ms: float,
) -> None:
    append_event(
        create_event(
            event_type=EventType.PRE_TOOL,
            provider="codex",
            session_id=session_id,
            source="tests/unit/test_context_os_gate.py",
            created_at=created_at.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            payload={
                "broker_telemetry": {
                    "graph_attempted": graph_attempted,
                    "graph_used": graph_attempted,
                    "fallback_used": not graph_attempted,
                    "fallback_reason": "graph_empty" if not graph_attempted else None,
                    "latency_ms": latency_ms,
                    "assembled_tokens": assembled_tokens,
                }
            },
        ),
        root=memory_root,
    )


def _metric(result, name: str):
    for item in result.metrics:
        if item.name == name:
            return item
    raise AssertionError(f"metric not found: {name}")


def test_gate_green_when_all_metrics_pass():
    run_dir = _new_run_dir()
    try:
        now = datetime(2026, 3, 3, 12, 0, tzinfo=timezone.utc)
        repo_root = run_dir / "repo"
        memory_root = repo_root / ".memory"
        ensure_memory_layout(root=memory_root)
        _write_docs(repo_root, now=now, age_hours=0.5)

        _append_pre_tool_event(
            memory_root=memory_root,
            created_at=now - timedelta(minutes=10),
            session_id="session-a",
            graph_attempted=True,
            assembled_tokens=1200,
            latency_ms=5.0,
        )
        _append_pre_tool_event(
            memory_root=memory_root,
            created_at=now - timedelta(minutes=10, seconds=-2),
            session_id="session-b",
            graph_attempted=True,
            assembled_tokens=1800,
            latency_ms=8.0,
        )

        result = run_gate(window_hours=24, repo_root=repo_root, memory_root=memory_root, now=now)
        assert result.status == "GREEN"
        assert _metric(result, "graph_attempt_rate").passed is True
        assert _metric(result, "token_budget").passed is True
        assert _metric(result, "hook_latency").passed is True
        assert _metric(result, "cross_terminal_visibility").passed is True
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_gate_red_on_critical_miss():
    run_dir = _new_run_dir()
    try:
        now = datetime(2026, 3, 3, 12, 0, tzinfo=timezone.utc)
        repo_root = run_dir / "repo"
        memory_root = repo_root / ".memory"
        ensure_memory_layout(root=memory_root)
        (repo_root / "docs").mkdir(parents=True, exist_ok=True)
        (repo_root / "docs" / "AGENT_START_HERE.md").write_text("# agent\n", encoding="utf-8")

        result = run_gate(window_hours=24, repo_root=repo_root, memory_root=memory_root, now=now)
        assert result.status == "RED"
        assert "DOC_MISSING" in result.failed_reasons
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_stale_docs_trigger_red_with_reason():
    run_dir = _new_run_dir()
    try:
        now = datetime(2026, 3, 3, 12, 0, tzinfo=timezone.utc)
        repo_root = run_dir / "repo"
        memory_root = repo_root / ".memory"
        ensure_memory_layout(root=memory_root)
        _write_docs(repo_root, now=now, age_hours=30)

        _append_pre_tool_event(
            memory_root=memory_root,
            created_at=now - timedelta(minutes=1),
            session_id="session-a",
            graph_attempted=True,
            assembled_tokens=1000,
            latency_ms=5.0,
        )
        _append_pre_tool_event(
            memory_root=memory_root,
            created_at=now - timedelta(minutes=1, seconds=-2),
            session_id="session-b",
            graph_attempted=True,
            assembled_tokens=1000,
            latency_ms=5.0,
        )

        result = run_gate(window_hours=24, repo_root=repo_root, memory_root=memory_root, now=now)
        freshness = _metric(result, "context_freshness")
        assert freshness.passed is False
        assert freshness.reason_code == "DOC_STALE"
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_graph_attempt_rate_below_threshold_triggers_red():
    run_dir = _new_run_dir()
    try:
        now = datetime(2026, 3, 3, 12, 0, tzinfo=timezone.utc)
        repo_root = run_dir / "repo"
        memory_root = repo_root / ".memory"
        ensure_memory_layout(root=memory_root)
        _write_docs(repo_root, now=now, age_hours=0.2)

        for idx in range(10):
            _append_pre_tool_event(
                memory_root=memory_root,
                created_at=now - timedelta(minutes=10) + timedelta(seconds=idx),
                session_id="session-a" if idx % 2 == 0 else "session-b",
                graph_attempted=idx < 9,
                assembled_tokens=1000,
                latency_ms=4.0,
            )

        result = run_gate(window_hours=24, repo_root=repo_root, memory_root=memory_root, now=now)
        metric = _metric(result, "graph_attempt_rate")
        assert result.status == "RED"
        assert metric.passed is False
        assert metric.reason_code == "GRAPH_ATTEMPT_RATE_LOW"
        assert metric.value["rate"] == 0.9
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_token_and_latency_thresholds_are_computed():
    run_dir = _new_run_dir()
    try:
        now = datetime(2026, 3, 3, 12, 0, tzinfo=timezone.utc)
        repo_root = run_dir / "repo"
        memory_root = repo_root / ".memory"
        ensure_memory_layout(root=memory_root)
        _write_docs(repo_root, now=now, age_hours=0.2)

        _append_pre_tool_event(
            memory_root=memory_root,
            created_at=now - timedelta(minutes=3),
            session_id="session-a",
            graph_attempted=True,
            assembled_tokens=1000,
            latency_ms=10.0,
        )
        _append_pre_tool_event(
            memory_root=memory_root,
            created_at=now - timedelta(minutes=3, seconds=-1),
            session_id="session-b",
            graph_attempted=True,
            assembled_tokens=6000,
            latency_ms=30.0,
        )

        result = run_gate(window_hours=24, repo_root=repo_root, memory_root=memory_root, now=now)
        token_metric = _metric(result, "token_budget")
        latency_metric = _metric(result, "hook_latency")
        assert token_metric.passed is False
        assert latency_metric.passed is False
        assert token_metric.value["median"] > 2500
        assert token_metric.value["p95"] > 4000
        assert latency_metric.value["p95_ms"] >= 20.0
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)
