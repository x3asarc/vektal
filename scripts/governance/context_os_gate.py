#!/usr/bin/env python3
"""Context OS governance gate with binary GREEN/RED output."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import statistics
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.memory.event_log import iter_events
DOC_PATHS = [
    Path("docs/AGENT_START_HERE.md"),
    Path("docs/FOLDER_SUMMARIES.md"),
    Path("docs/CONTEXT_LINK_MAP.md"),
]
GRAPH_ATTEMPT_THRESHOLD = 0.95
TOKEN_MEDIAN_THRESHOLD = 2500
TOKEN_P95_THRESHOLD = 4000
HOOK_LATENCY_P95_MS = 20.0
CROSS_TERMINAL_MAX_SECONDS = 5.0


@dataclass(frozen=True)
class MetricResult:
    name: str
    passed: bool
    threshold: str
    value: dict[str, Any]
    reason_code: str | None
    remediation: str


@dataclass(frozen=True)
class GateResult:
    status: str
    checked_at: str
    window_hours: int
    metrics: list[MetricResult]
    failed_reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "checked_at": self.checked_at,
            "window_hours": self.window_hours,
            "metrics": [asdict(metric) for metric in self.metrics],
            "failed_reasons": self.failed_reasons,
        }


def _parse_iso(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if not candidate:
        return None
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(candidate)
    except ValueError:
        return None


def _to_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(float(item) for item in values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * max(0.0, min(1.0, p))
    lower_index = int(rank)
    upper_index = min(lower_index + 1, len(ordered) - 1)
    fraction = rank - lower_index
    lower = ordered[lower_index]
    upper = ordered[upper_index]
    return lower + (upper - lower) * fraction


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _event_window(
    *,
    memory_root: Path | None,
    cutoff: datetime,
    now: datetime,
) -> list[dict[str, Any]]:
    day_from = cutoff.date().isoformat()
    day_to = now.date().isoformat()
    rows: list[dict[str, Any]] = []
    for event in iter_events(root=memory_root, day_from=day_from, day_to=day_to):
        created = _parse_iso(event.get("created_at"))
        if created is None:
            continue
        if created < cutoff or created > now:
            continue
        rows.append(event)
    rows.sort(key=lambda item: str(item.get("created_at") or ""))
    return rows


def _metric_docs_freshness(
    *,
    repo_root: Path,
    session_start_events: list[dict[str, Any]],
    now: datetime,
    window_hours: int,
) -> MetricResult:
    max_age = timedelta(hours=window_hours)
    refreshed_suffixes: set[str] = set()
    for event in session_start_events:
        payload = event.get("payload") or {}
        refreshed = payload.get("docs_refreshed")
        if not isinstance(refreshed, list):
            continue
        for item in refreshed:
            if not isinstance(item, str):
                continue
            refreshed_suffixes.add(Path(item).as_posix().lower())

    docs_info: dict[str, Any] = {}
    missing_docs: list[str] = []
    stale_docs: list[str] = []
    for rel_path in DOC_PATHS:
        abs_path = repo_root / rel_path
        key = rel_path.as_posix()
        if not abs_path.exists():
            docs_info[key] = {"exists": False, "age_hours": None, "refreshed_in_window": False}
            missing_docs.append(key)
            continue
        modified = datetime.fromtimestamp(abs_path.stat().st_mtime, tz=timezone.utc)
        age = now - modified
        was_refreshed = any(path.endswith(key.lower()) for path in refreshed_suffixes)
        docs_info[key] = {
            "exists": True,
            "age_hours": round(age.total_seconds() / 3600.0, 3),
            "refreshed_in_window": was_refreshed,
        }
        if age > max_age and not was_refreshed:
            stale_docs.append(key)

    passed = not missing_docs and not stale_docs
    reason_code = None
    if missing_docs:
        reason_code = "DOC_MISSING"
    elif stale_docs:
        reason_code = "DOC_STALE"

    return MetricResult(
        name="context_freshness",
        passed=passed,
        threshold=f"all docs <= {window_hours}h old or refreshed in-session",
        value={"docs": docs_info, "missing_docs": missing_docs, "stale_docs": stale_docs},
        reason_code=reason_code,
        remediation="Run session/doc refresh commands, then re-run the gate.",
    )


def _metric_event_signal_completeness(pre_tool_events: list[dict[str, Any]]) -> MetricResult:
    required_nested = [
        "graph_attempted",
        "graph_used",
        "fallback_used",
        "fallback_reason",
        "latency_ms",
        "assembled_tokens",
    ]
    if not pre_tool_events:
        return MetricResult(
            name="event_signal_completeness",
            passed=False,
            threshold="required fields present in 100% of pre_tool events",
            value={"total_events": 0, "complete_events": 0, "completeness_rate": 0.0},
            reason_code="NO_EVENT_SIGNALS",
            remediation="Generate pre_tool traffic and ensure hook writes broker_telemetry payload.",
        )

    complete = 0
    missing_details: list[dict[str, Any]] = []
    for event in pre_tool_events:
        payload = event.get("payload") or {}
        telemetry = payload.get("broker_telemetry") if isinstance(payload, dict) else None
        missing: list[str] = []
        if not isinstance(event.get("event_type"), str):
            missing.append("event_type")
        if not isinstance(event.get("created_at"), str):
            missing.append("created_at")
        if not isinstance(event.get("provider"), str):
            missing.append("provider")
        if not isinstance(event.get("session_id"), str):
            missing.append("session_id")
        if not isinstance(telemetry, dict):
            missing.extend(f"payload.broker_telemetry.{field}" for field in required_nested)
        else:
            for field in required_nested:
                if field not in telemetry:
                    missing.append(f"payload.broker_telemetry.{field}")
        if missing:
            missing_details.append({"event_id": event.get("event_id"), "missing": missing})
        else:
            complete += 1

    total = len(pre_tool_events)
    rate = complete / total if total else 0.0
    return MetricResult(
        name="event_signal_completeness",
        passed=complete == total,
        threshold="required fields present in 100% of pre_tool events",
        value={
            "total_events": total,
            "complete_events": complete,
            "completeness_rate": round(rate, 4),
            "examples_missing": missing_details[:5],
        },
        reason_code=None if complete == total else "EVENT_SIGNAL_MISSING",
        remediation="Ensure pre_tool hooks emit full broker telemetry fields in canonical event payload.",
    )


def _metric_graph_attempt_rate(samples: list[dict[str, Any]]) -> MetricResult:
    values = [sample.get("graph_attempted") for sample in samples if isinstance(sample.get("graph_attempted"), bool)]
    total = len(values)
    attempts = sum(1 for item in values if item)
    rate = (attempts / total) if total else 0.0
    passed = total > 0 and rate >= GRAPH_ATTEMPT_THRESHOLD
    reason = None
    if total == 0:
        reason = "NO_GRAPH_TELEMETRY"
    elif rate < GRAPH_ATTEMPT_THRESHOLD:
        reason = "GRAPH_ATTEMPT_RATE_LOW"
    return MetricResult(
        name="graph_attempt_rate",
        passed=passed,
        threshold=f">= {int(GRAPH_ATTEMPT_THRESHOLD * 100)}%",
        value={"sample_count": total, "attempt_count": attempts, "rate": round(rate, 4)},
        reason_code=reason,
        remediation="Route all context retrieval through assemble_context graph-first path before fallback.",
    )


def _metric_token_budget(samples: list[dict[str, Any]]) -> MetricResult:
    tokens = [float(sample.get("assembled_tokens")) for sample in samples if _is_number(sample.get("assembled_tokens"))]
    if not tokens:
        return MetricResult(
            name="token_budget",
            passed=False,
            threshold=f"median <= {TOKEN_MEDIAN_THRESHOLD}, p95 <= {TOKEN_P95_THRESHOLD}",
            value={"sample_count": 0, "median": None, "p95": None},
            reason_code="NO_TOKEN_TELEMETRY",
            remediation="Emit assembled_tokens in broker telemetry and generate retrieval traffic.",
        )

    median_value = float(statistics.median(tokens))
    p95_value = _percentile(tokens, 0.95)
    passed = median_value <= TOKEN_MEDIAN_THRESHOLD and p95_value <= TOKEN_P95_THRESHOLD
    reason = None
    if median_value > TOKEN_MEDIAN_THRESHOLD or p95_value > TOKEN_P95_THRESHOLD:
        reason = "TOKEN_BUDGET_EXCEEDED"
    return MetricResult(
        name="token_budget",
        passed=passed,
        threshold=f"median <= {TOKEN_MEDIAN_THRESHOLD}, p95 <= {TOKEN_P95_THRESHOLD}",
        value={
            "sample_count": len(tokens),
            "median": round(median_value, 3),
            "p95": round(p95_value, 3),
        },
        reason_code=reason,
        remediation="Reduce low-priority snippets first, then compact older history while preserving governance constraints.",
    )


def _metric_hook_latency(samples: list[dict[str, Any]], total_pre_tool_events: int) -> MetricResult:
    latencies = [float(sample.get("latency_ms")) for sample in samples if _is_number(sample.get("latency_ms"))]
    blocking_incidents = max(0, total_pre_tool_events - len(latencies))
    if not latencies:
        return MetricResult(
            name="hook_latency",
            passed=False,
            threshold=f"p95 < {HOOK_LATENCY_P95_MS}ms and blocking_incidents = 0",
            value={"sample_count": 0, "p95_ms": None, "blocking_incidents": blocking_incidents},
            reason_code="NO_LATENCY_TELEMETRY",
            remediation="Ensure pre_tool events include broker latency telemetry on every invocation.",
        )

    p95_value = _percentile(latencies, 0.95)
    passed = p95_value < HOOK_LATENCY_P95_MS and blocking_incidents == 0
    reason = None
    if blocking_incidents > 0:
        reason = "HOOK_BLOCKING_INCIDENT"
    elif p95_value >= HOOK_LATENCY_P95_MS:
        reason = "HOOK_LATENCY_P95_HIGH"
    return MetricResult(
        name="hook_latency",
        passed=passed,
        threshold=f"p95 < {HOOK_LATENCY_P95_MS}ms and blocking_incidents = 0",
        value={
            "sample_count": len(latencies),
            "p95_ms": round(p95_value, 3),
            "blocking_incidents": blocking_incidents,
        },
        reason_code=reason,
        remediation="Keep pre_tool hook fail-open, remove expensive operations from hot path, and verify append duration.",
    )


def _metric_cross_terminal(samples: list[dict[str, Any]]) -> MetricResult:
    points: list[tuple[datetime, str]] = []
    for sample in samples:
        created = sample.get("created_at")
        session_id = sample.get("session_id")
        if not isinstance(created, datetime):
            continue
        if not isinstance(session_id, str) or not session_id.strip():
            continue
        points.append((created, session_id.strip()))
    points.sort(key=lambda item: item[0])

    distinct_sessions = sorted({session for _, session in points})
    if len(distinct_sessions) < 2:
        return MetricResult(
            name="cross_terminal_visibility",
            passed=False,
            threshold=f"inter-session update gap <= {CROSS_TERMINAL_MAX_SECONDS}s",
            value={"distinct_sessions": len(distinct_sessions), "min_inter_session_seconds": None},
            reason_code="NO_CROSS_TERMINAL_SIGNAL",
            remediation="Run at least two terminal sessions using unique session keys and verify shared updates.",
        )

    min_gap: float | None = None
    for idx in range(1, len(points)):
        prev_ts, prev_session = points[idx - 1]
        curr_ts, curr_session = points[idx]
        if prev_session == curr_session:
            continue
        gap = (curr_ts - prev_ts).total_seconds()
        if min_gap is None or gap < min_gap:
            min_gap = gap

    if min_gap is None:
        return MetricResult(
            name="cross_terminal_visibility",
            passed=False,
            threshold=f"inter-session update gap <= {CROSS_TERMINAL_MAX_SECONDS}s",
            value={"distinct_sessions": len(distinct_sessions), "min_inter_session_seconds": None},
            reason_code="NO_CROSS_TERMINAL_SIGNAL",
            remediation="Generate alternating pre_tool activity across terminals.",
        )

    passed = min_gap <= CROSS_TERMINAL_MAX_SECONDS
    return MetricResult(
        name="cross_terminal_visibility",
        passed=passed,
        threshold=f"inter-session update gap <= {CROSS_TERMINAL_MAX_SECONDS}s",
        value={
            "distinct_sessions": len(distinct_sessions),
            "min_inter_session_seconds": round(min_gap, 3),
        },
        reason_code=None if passed else "CROSS_TERMINAL_DELAY",
        remediation="Increase hook frequency or reduce visibility tick to keep cross-terminal updates under 5 seconds.",
    )


def run_gate(
    *,
    window_hours: int = 24,
    repo_root: Path | None = None,
    memory_root: Path | None = None,
    now: datetime | None = None,
) -> GateResult:
    """Evaluate Context OS health and return binary GREEN/RED result."""

    checked_at = now or datetime.now(timezone.utc)
    if checked_at.tzinfo is None:
        checked_at = checked_at.replace(tzinfo=timezone.utc)
    effective_repo = (repo_root or PROJECT_ROOT).resolve()
    effective_memory = memory_root.resolve() if memory_root else None
    cutoff = checked_at - timedelta(hours=max(1, int(window_hours)))

    events = _event_window(memory_root=effective_memory, cutoff=cutoff, now=checked_at)
    pre_tool_events = [event for event in events if event.get("event_type") == "pre_tool"]
    session_start_events = [event for event in events if event.get("event_type") == "session_start"]

    samples: list[dict[str, Any]] = []
    for event in pre_tool_events:
        payload = event.get("payload")
        telemetry = payload.get("broker_telemetry") if isinstance(payload, dict) else None
        if not isinstance(telemetry, dict):
            continue
        samples.append(
            {
                "event_id": event.get("event_id"),
                "session_id": event.get("session_id"),
                "created_at": _parse_iso(event.get("created_at")),
                "graph_attempted": telemetry.get("graph_attempted"),
                "graph_used": telemetry.get("graph_used"),
                "fallback_used": telemetry.get("fallback_used"),
                "fallback_reason": telemetry.get("fallback_reason"),
                "latency_ms": telemetry.get("latency_ms"),
                "assembled_tokens": telemetry.get("assembled_tokens"),
            }
        )

    metrics = [
        _metric_docs_freshness(
            repo_root=effective_repo,
            session_start_events=session_start_events,
            now=checked_at,
            window_hours=window_hours,
        ),
        _metric_event_signal_completeness(pre_tool_events),
        _metric_graph_attempt_rate(samples),
        _metric_token_budget(samples),
        _metric_hook_latency(samples, len(pre_tool_events)),
        _metric_cross_terminal(samples),
    ]
    failed_reasons = [metric.reason_code for metric in metrics if not metric.passed and metric.reason_code]
    status = "GREEN" if not failed_reasons else "RED"
    return GateResult(
        status=status,
        checked_at=_to_iso(checked_at),
        window_hours=int(window_hours),
        metrics=metrics,
        failed_reasons=failed_reasons,
    )


def _render_human(result: GateResult) -> str:
    lines = [f"Context OS Gate verdict: {result.status}"]
    for metric in result.metrics:
        marker = "PASS" if metric.passed else "FAIL"
        reason = f" reason={metric.reason_code}" if metric.reason_code else ""
        lines.append(f"- [{marker}] {metric.name}{reason}")
    if result.failed_reasons:
        lines.append(f"Failed reasons: {', '.join(result.failed_reasons)}")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Context OS governance gate (binary GREEN/RED).")
    parser.add_argument("--window-hours", type=int, default=24, help="Metric evaluation window in hours")
    parser.add_argument("--repo-root", type=Path, help="Optional repository root override")
    parser.add_argument("--memory-root", type=Path, help="Optional memory root override")
    parser.add_argument("--json", action="store_true", help="Print structured JSON result")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_gate(
        window_hours=args.window_hours,
        repo_root=args.repo_root,
        memory_root=args.memory_root,
    )
    print(_render_human(result))
    if args.json:
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0 if result.status == "GREEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
