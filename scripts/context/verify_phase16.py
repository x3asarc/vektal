#!/usr/bin/env python3
"""Verification harness for Phase 16 Context OS closure evidence."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.memory.event_log import iter_events

GATE_COMMAND = "python scripts/governance/context_os_gate.py --window-hours 24 --json"
RUNBOOK_PATH = Path("docs/runbooks/context-os-operations.md")
REQUIRED_SUMMARY_DIRS = ["`src/`", "`scripts/`", "`.planning/`", "`docs/`", "`tests/`", "`ops/`"]


@dataclass(frozen=True)
class ScenarioCheck:
    name: str
    passed: bool
    details: dict[str, Any]
    reason_code: str | None = None


def _to_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_iso(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(candidate)
    except ValueError:
        return None


def _run_command(command: list[str], *, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _extract_json_payload(raw_output: str) -> dict[str, Any]:
    for idx, char in enumerate(raw_output):
        if char != "{":
            continue
        try:
            return json.loads(raw_output[idx:])
        except json.JSONDecodeError:
            continue
    raise ValueError("No JSON payload found in command output")


def _metric(gate_payload: dict[str, Any], name: str) -> dict[str, Any] | None:
    for item in gate_payload.get("metrics", []):
        if item.get("name") == name:
            return item
    return None


def _check_warm_start() -> ScenarioCheck:
    target = REPO_ROOT / "docs" / "AGENT_START_HERE.md"
    if not target.exists():
        return ScenarioCheck(
            name="new_agent_warm_start",
            passed=False,
            reason_code="AGENT_START_DOC_MISSING",
            details={"path": target.as_posix()},
        )
    text = target.read_text(encoding="utf-8", errors="ignore")
    required_markers = [
        "Current Runtime Snapshot",
        "Priority Links",
        "Folder Summary Pointers",
    ]
    missing = [marker for marker in required_markers if marker not in text]
    return ScenarioCheck(
        name="new_agent_warm_start",
        passed=not missing,
        reason_code=None if not missing else "AGENT_START_DOC_INCOMPLETE",
        details={"path": target.as_posix(), "missing_markers": missing},
    )


def _check_folder_summary_coverage() -> ScenarioCheck:
    target = REPO_ROOT / "docs" / "FOLDER_SUMMARIES.md"
    if not target.exists():
        return ScenarioCheck(
            name="folder_summary_coverage",
            passed=False,
            reason_code="FOLDER_SUMMARIES_MISSING",
            details={"path": target.as_posix()},
        )
    text = target.read_text(encoding="utf-8", errors="ignore")
    missing = [entry for entry in REQUIRED_SUMMARY_DIRS if entry not in text]
    return ScenarioCheck(
        name="folder_summary_coverage",
        passed=not missing,
        reason_code=None if not missing else "FOLDER_SUMMARY_COVERAGE_GAP",
        details={"path": target.as_posix(), "missing_entries": missing},
    )


def _check_graph_attempt_rate(gate_payload: dict[str, Any]) -> ScenarioCheck:
    metric = _metric(gate_payload, "graph_attempt_rate")
    if metric is None:
        return ScenarioCheck(
            name="graph_first_attempt_rate",
            passed=False,
            reason_code="GRAPH_ATTEMPT_METRIC_MISSING",
            details={},
        )
    value = metric.get("value") or {}
    rate = value.get("rate")
    passed = bool(metric.get("passed")) and isinstance(rate, (int, float)) and float(rate) >= 0.95
    return ScenarioCheck(
        name="graph_first_attempt_rate",
        passed=passed,
        reason_code=None if passed else "GRAPH_ATTEMPT_RATE_LOW",
        details={"rate": rate, "metric": metric},
    )


def _check_fallback_reason_quality(*, window_hours: int) -> ScenarioCheck:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=window_hours)
    fallback_samples = 0
    missing_reason = 0

    day_from = cutoff.date().isoformat()
    day_to = now.date().isoformat()
    for event in iter_events(root=None, day_from=day_from, day_to=day_to):
        created = _parse_iso(event.get("created_at"))
        if created is None or created < cutoff:
            continue
        if event.get("event_type") != "pre_tool":
            continue
        payload = event.get("payload") or {}
        telemetry = payload.get("broker_telemetry") if isinstance(payload, dict) else None
        if not isinstance(telemetry, dict):
            continue
        if telemetry.get("fallback_used") is True:
            fallback_samples += 1
            reason = telemetry.get("fallback_reason")
            if not isinstance(reason, str) or not reason.strip():
                missing_reason += 1

    passed = missing_reason == 0
    reason = None if passed else "FALLBACK_REASON_MISSING"
    return ScenarioCheck(
        name="fallback_reason_quality",
        passed=passed,
        reason_code=reason,
        details={
            "fallback_samples": fallback_samples,
            "missing_reason_count": missing_reason,
        },
    )


def _check_cross_terminal(gate_payload: dict[str, Any]) -> ScenarioCheck:
    metric = _metric(gate_payload, "cross_terminal_visibility")
    if metric is None:
        return ScenarioCheck(
            name="cross_terminal_visibility",
            passed=False,
            reason_code="CROSS_TERMINAL_METRIC_MISSING",
            details={},
        )
    passed = bool(metric.get("passed"))
    return ScenarioCheck(
        name="cross_terminal_visibility",
        passed=passed,
        reason_code=None if passed else str(metric.get("reason_code") or "CROSS_TERMINAL_FAIL"),
        details={"metric": metric},
    )


def _check_token_latency(gate_payload: dict[str, Any]) -> ScenarioCheck:
    token_metric = _metric(gate_payload, "token_budget")
    latency_metric = _metric(gate_payload, "hook_latency")
    if token_metric is None or latency_metric is None:
        return ScenarioCheck(
            name="token_and_latency_budgets",
            passed=False,
            reason_code="BUDGET_METRICS_MISSING",
            details={"token_metric": token_metric, "latency_metric": latency_metric},
        )
    passed = bool(token_metric.get("passed")) and bool(latency_metric.get("passed"))
    return ScenarioCheck(
        name="token_and_latency_budgets",
        passed=passed,
        reason_code=None if passed else "BUDGET_THRESHOLD_FAIL",
        details={"token_metric": token_metric, "latency_metric": latency_metric},
    )


def _check_runbook_present() -> ScenarioCheck:
    target = REPO_ROOT / RUNBOOK_PATH
    passed = target.exists()
    return ScenarioCheck(
        name="runbook_present",
        passed=passed,
        reason_code=None if passed else "RUNBOOK_MISSING",
        details={"path": RUNBOOK_PATH.as_posix()},
    )


def _run_integration_suite() -> ScenarioCheck:
    result = _run_command(
        [sys.executable, "-m", "pytest", "-q", "tests/integration/test_phase16_context_os_e2e.py"],
        timeout=300,
    )
    passed = result.returncode == 0
    return ScenarioCheck(
        name="phase16_integration_suite",
        passed=passed,
        reason_code=None if passed else "PHASE16_INTEGRATION_FAIL",
        details={
            "returncode": result.returncode,
            "stdout_tail": (result.stdout or "")[-1200:],
            "stderr_tail": (result.stderr or "")[-1200:],
        },
    )


def verify_phase16(*, mode: str, window_hours: int) -> tuple[dict[str, Any], int]:
    gate_proc = _run_command(
        [sys.executable, "scripts/governance/context_os_gate.py", "--window-hours", str(window_hours), "--json"],
        timeout=120,
    )
    gate_payload: dict[str, Any]
    gate_error: str | None = None
    try:
        gate_payload = _extract_json_payload(gate_proc.stdout or "")
    except Exception as exc:
        gate_error = str(exc)
        gate_payload = {
            "status": "RED",
            "failed_reasons": ["GATE_OUTPUT_PARSE_ERROR"],
            "metrics": [],
        }

    scenarios = [
        _check_warm_start(),
        _check_folder_summary_coverage(),
        _check_graph_attempt_rate(gate_payload),
        _check_fallback_reason_quality(window_hours=window_hours),
        _check_cross_terminal(gate_payload),
        _check_token_latency(gate_payload),
        _check_runbook_present(),
    ]
    if mode == "full":
        scenarios.append(_run_integration_suite())

    scenario_pass = all(item.passed for item in scenarios)
    gate_green = str(gate_payload.get("status")) == "GREEN"
    overall_green = scenario_pass and gate_green and gate_proc.returncode == 0 and gate_error is None

    payload = {
        "status": "GREEN" if overall_green else "RED",
        "checked_at": _to_iso(datetime.now(timezone.utc)),
        "mode": mode,
        "gate_command": GATE_COMMAND,
        "gate_returncode": gate_proc.returncode,
        "gate_parse_error": gate_error,
        "gate": gate_payload,
        "scenarios": [asdict(item) for item in scenarios],
        "evidence_paths": [
            "docs/AGENT_START_HERE.md",
            "docs/FOLDER_SUMMARIES.md",
            "docs/CONTEXT_LINK_MAP.md",
            "docs/runbooks/context-os-operations.md",
            "scripts/governance/context_os_gate.py",
            "tests/integration/test_phase16_context_os_e2e.py",
        ],
    }
    return payload, (0 if overall_green else 1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify Phase 16 Context OS readiness.")
    parser.add_argument("--mode", choices=["quick", "full"], default="quick")
    parser.add_argument("--window-hours", type=int, default=24)
    parser.add_argument("--output", type=Path, help="Optional output JSON path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload, exit_code = verify_phase16(mode=args.mode, window_hours=args.window_hours)
    text = json.dumps(payload, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
        print(str(args.output))
    else:
        print(text)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
