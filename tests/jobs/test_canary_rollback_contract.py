"""Phase 13-03 canary rollback guard contract tests."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
import os

from src.assistant.deployment.canary_guard import evaluate_canary_rollback


def test_canary_guard_enforces_scope_and_sample_floor_before_rollback():
    scope_mismatch = evaluate_canary_rollback(
        baseline_availability=0.999,
        canary_availability=0.90,
        sample_size=500,
        scope_match=False,
    )
    assert scope_mismatch.should_rollback is False
    assert scope_mismatch.reason == "scope_mismatch"

    below_floor = evaluate_canary_rollback(
        baseline_availability=0.999,
        canary_availability=0.80,
        sample_size=100,
        scope_match=True,
    )
    assert below_floor.should_rollback is False
    assert below_floor.reason == "sample_floor_not_met"


def test_canary_guard_rolls_back_only_on_drop_above_threshold():
    rollback = evaluate_canary_rollback(
        baseline_availability=0.99,
        canary_availability=0.92,
        sample_size=500,
        scope_match=True,
        threshold_drop=0.05,
    )
    assert rollback.should_rollback is True
    assert rollback.reason == "availability_drop_threshold_breached"

    safe = evaluate_canary_rollback(
        baseline_availability=0.99,
        canary_availability=0.96,
        sample_size=500,
        scope_match=True,
        threshold_drop=0.05,
    )
    assert safe.should_rollback is False
    assert safe.reason == "within_threshold"


def test_canary_gate_cli_exit_code_matches_rollback_decision():
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "governance" / "phase13_canary_gate.py"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(repo_root)
    fail = subprocess.run(
        [
            sys.executable,
            str(script),
            "--baseline",
            "0.99",
            "--canary",
            "0.90",
            "--sample-size",
            "500",
            "--scope-match",
            "true",
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        env=env,
    )
    assert fail.returncode == 1
    assert '"should_rollback": true' in fail.stdout.lower()

    pass_run = subprocess.run(
        [
            sys.executable,
            str(script),
            "--baseline",
            "0.99",
            "--canary",
            "0.97",
            "--sample-size",
            "500",
            "--scope-match",
            "true",
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        env=env,
    )
    assert pass_run.returncode == 0
    assert '"should_rollback": false' in pass_run.stdout.lower()
