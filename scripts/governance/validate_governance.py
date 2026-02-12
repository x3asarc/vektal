#!/usr/bin/env python3
"""Validate governance baseline artifacts and task report gates."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


REQUIRED_ARTIFACTS = [
    Path("AGENTS.md"),
    Path("STANDARDS.md"),
    Path(".rules"),
    Path("FAILURE_JOURNEY.md"),
    Path("ops/STRUCTURE_SPEC.md"),
    Path("docs/MASTER_MAP.md"),
    Path(".planning/ROADMAP.md"),
    Path(".planning/STATE.md"),
]

REQUIRED_REPORTS = [
    "self-check.md",
    "review.md",
    "structure-audit.md",
    "integrity-audit.md",
]


@dataclass
class CheckResult:
    ok: bool
    message: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate governance artifacts and report set.")
    parser.add_argument("--phase", required=True, help="Phase identifier (example: 07)")
    parser.add_argument("--task", required=True, help="Task identifier (example: 07.1-governance-baseline-dry-run)")
    parser.add_argument("--repo-root", default=".", help="Repository root path")
    return parser.parse_args()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_iso(ts: str) -> datetime:
    value = ts.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def require_regex(text: str, pattern: str, label: str) -> CheckResult:
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        return CheckResult(False, f"Missing or empty required field: {label}")
    value = match.group(1).strip()
    if not value:
        return CheckResult(False, f"Empty required field: {label}")
    return CheckResult(True, f"{label} present")


def validate_required_artifacts(root: Path) -> list[CheckResult]:
    results: list[CheckResult] = []
    for rel_path in REQUIRED_ARTIFACTS:
        full = root / rel_path
        results.append(
            CheckResult(full.exists(), f"Artifact {'found' if full.exists() else 'missing'}: {rel_path}")
        )
    return results


def validate_report_set(root: Path, phase: str, task: str) -> tuple[list[CheckResult], Path]:
    report_dir = root / "reports" / phase / task
    results: list[CheckResult] = []
    if not report_dir.exists():
        return [CheckResult(False, f"Report directory missing: {report_dir}")], report_dir

    files = sorted([p.name for p in report_dir.iterdir() if p.is_file()])
    results.append(
        CheckResult(
            files == sorted(REQUIRED_REPORTS),
            f"Report files {'valid' if files == sorted(REQUIRED_REPORTS) else 'invalid'}: {files}",
        )
    )
    return results, report_dir


def validate_report_fields(report_dir: Path) -> list[CheckResult]:
    results: list[CheckResult] = []

    self_check = read_text(report_dir / "self-check.md")
    results.append(require_regex(self_check, r"^Task:\s*`?(.+?)`?$", "self-check Task"))
    results.append(require_regex(self_check, r"^Owner:\s*`?(.+?)`?$", "self-check Owner"))
    results.append(require_regex(self_check, r"^Status:\s*`?(.+?)`?$", "self-check Status"))

    review = read_text(report_dir / "review.md")
    results.append(require_regex(review, r"^Task:\s*`?(.+?)`?$", "review Task"))
    results.append(require_regex(review, r"^Owner:\s*`?(.+?)`?$", "review Owner"))
    results.append(require_regex(review, r"^Status:\s*`?(.+?)`?$", "review Status"))
    results.append(require_regex(review, r"^pass_1_timestamp:\s*`?(.+?)`?$", "review pass_1_timestamp"))
    results.append(require_regex(review, r"^plan_context_opened_at:\s*`?(.+?)`?$", "review plan_context_opened_at"))
    results.append(require_regex(review, r"^pass_2_timestamp:\s*`?(.+?)`?$", "review pass_2_timestamp"))

    structure = read_text(report_dir / "structure-audit.md")
    results.append(require_regex(structure, r"^Task:\s*`?(.+?)`?$", "structure Task"))
    results.append(require_regex(structure, r"^Owner:\s*`?(.+?)`?$", "structure Owner"))
    results.append(require_regex(structure, r"^Status:\s*`?(.+?)`?$", "structure Status"))

    integrity = read_text(report_dir / "integrity-audit.md")
    results.append(require_regex(integrity, r"^Task:\s*`?(.+?)`?$", "integrity Task"))
    results.append(require_regex(integrity, r"^Owner:\s*`?(.+?)`?$", "integrity Owner"))
    results.append(require_regex(integrity, r"^Status:\s*`?(.+?)`?$", "integrity Status"))

    return results


def validate_blind_order(report_dir: Path) -> CheckResult:
    review = read_text(report_dir / "review.md")
    p1 = re.search(r"^pass_1_timestamp:\s*`?(.+?)`?$", review, re.MULTILINE)
    ctx = re.search(r"^plan_context_opened_at:\s*`?(.+?)`?$", review, re.MULTILINE)
    p2 = re.search(r"^pass_2_timestamp:\s*`?(.+?)`?$", review, re.MULTILINE)

    if not (p1 and ctx and p2):
        return CheckResult(False, "Blind review ordering fields missing")

    try:
        t1 = parse_iso(p1.group(1))
        tc = parse_iso(ctx.group(1))
        t2 = parse_iso(p2.group(1))
    except Exception as exc:  # pragma: no cover - defensive parse guard
        return CheckResult(False, f"Invalid timestamp format: {exc}")

    if not (t1 < tc <= t2):
        return CheckResult(False, "Blind review ordering invalid (expected pass_1 < plan_context_opened_at <= pass_2)")
    return CheckResult(True, "Blind review ordering valid")


def validate_roadmap_state_markers(root: Path) -> list[CheckResult]:
    results: list[CheckResult] = []
    roadmap = read_text(root / ".planning/ROADMAP.md")
    state = read_text(root / ".planning/STATE.md")

    results.append(
        CheckResult("## Governance Baseline v1" in roadmap, "ROADMAP governance section present")
    )
    results.append(
        CheckResult("## Governance Gate Snapshot" in state, "STATE governance gate snapshot present")
    )
    results.append(
        CheckResult("## StructureGuardian Audit Trail" in state, "STATE structure audit trail present")
    )
    return results


def main() -> int:
    args = parse_args()
    root = Path(args.repo_root).resolve()
    phase = args.phase
    task = args.task

    checks: list[CheckResult] = []
    checks.extend(validate_required_artifacts(root))
    report_set_checks, report_dir = validate_report_set(root, phase, task)
    checks.extend(report_set_checks)

    if report_dir.exists():
        checks.extend(validate_report_fields(report_dir))
        checks.append(validate_blind_order(report_dir))

    checks.extend(validate_roadmap_state_markers(root))

    failed = [c for c in checks if not c.ok]
    for item in checks:
        tag = "PASS" if item.ok else "FAIL"
        print(f"[{tag}] {item.message}")

    if failed:
        print(f"\nGovernance validation failed: {len(failed)} check(s).")
        return 1
    print("\nGovernance validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

