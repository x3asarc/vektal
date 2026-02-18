#!/usr/bin/env python3
"""Harness gap loop — enforce browser evidence SLAs defined in HARNESS_GAPS.md.

Reads HARNESS_GAPS.md, counts open gaps by priority, compares against SLA targets,
and emits a gap report. Exits 1 if any CRITICAL gap is open (CI blocker).

Usage:
    python scripts/governance/check_harness_slas.py
    python scripts/governance/check_harness_slas.py --report-file reports/harness-slas.md
    python scripts/governance/check_harness_slas.py --strict  # also fail on HIGH gaps
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HARNESS_GAPS_PATH = REPO_ROOT / "HARNESS_GAPS.md"
E2E_TESTS_DIR = REPO_ROOT / "tests" / "e2e"
ARTIFACTS_DIR = REPO_ROOT / "test-results" / "playwright-artifacts"

SLA_DEFAULTS = {
    "e2e_coverage_floor_pct": 60,
    "browser_evidence_required_for": ["critical", "high"],
    "max_gap_age_days": 14,
}


def parse_gap_table(text: str) -> list[dict]:
    """Parse the coverage table from HARNESS_GAPS.md."""
    rows = []
    in_table = False
    for line in text.splitlines():
        if "| Feature Area |" in line:
            in_table = True
            continue
        if in_table and line.startswith("|---"):
            continue
        if in_table and line.startswith("|"):
            cols = [c.strip() for c in line.split("|")[1:-1]]
            if len(cols) >= 5:
                rows.append({
                    "feature": cols[0],
                    "unit_tests": cols[1],
                    "e2e_tests": cols[2],
                    "browser_evidence": cols[3],
                    "priority": cols[4],
                })
        elif in_table and not line.startswith("|"):
            in_table = False
    return rows


def parse_gap_age_table(text: str) -> list[dict]:
    """Parse the gap age tracking table."""
    rows = []
    in_table = False
    for line in text.splitlines():
        if "| Gap |" in line and "Opened" in line:
            in_table = True
            continue
        if in_table and line.startswith("|---"):
            continue
        if in_table and line.startswith("|"):
            cols = [c.strip() for c in line.split("|")[1:-1]]
            if len(cols) >= 4:
                rows.append({
                    "gap": cols[0],
                    "opened": cols[1],
                    "max_age": cols[2],
                    "status": cols[3],
                })
        elif in_table and not line.startswith("|"):
            in_table = False
    return rows


def parse_sla_json(text: str) -> dict:
    """Extract the SLA JSON block from HARNESS_GAPS.md."""
    match = re.search(r"```json\n(.+?)\n```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return SLA_DEFAULTS


def count_e2e_files() -> int:
    if not E2E_TESTS_DIR.exists():
        return 0
    return len(list(E2E_TESTS_DIR.glob("*.e2e.ts")))


def count_screenshots() -> int:
    if not ARTIFACTS_DIR.exists():
        return 0
    return len(list(ARTIFACTS_DIR.glob("**/*.png")))


def check_overdue_gaps(age_rows: list[dict]) -> list[dict]:
    """Find gaps that have exceeded their max age."""
    overdue = []
    today = datetime.now(timezone.utc).date()
    for row in age_rows:
        if row["status"].upper() != "OPEN":
            continue
        try:
            max_date = datetime.strptime(row["max_age"], "%Y-%m-%d").date()
            if today > max_date:
                overdue.append(row)
        except ValueError:
            pass
    return overdue


def build_report(
    coverage_rows: list[dict],
    age_rows: list[dict],
    sla: dict,
    strict: bool,
) -> tuple[str, int]:
    """Build a report and return (report_text, exit_code)."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    total_features = len(coverage_rows)
    has_e2e = sum(1 for r in coverage_rows if "✅" in r["e2e_tests"])
    has_evidence = sum(1 for r in coverage_rows if "✅" in r["browser_evidence"])

    e2e_pct = int(has_e2e / total_features * 100) if total_features else 0
    evidence_pct = int(has_evidence / total_features * 100) if total_features else 0

    critical_gaps = [r for r in coverage_rows if r["priority"] == "CRITICAL" and "❌" in r["e2e_tests"]]
    high_gaps = [r for r in coverage_rows if r["priority"] == "HIGH" and "❌" in r["e2e_tests"]]
    overdue = check_overdue_gaps(age_rows)

    e2e_floor = sla.get("e2e_coverage_floor_pct", 60)
    floor_ok = e2e_pct >= e2e_floor

    exit_code = 0
    issues = []

    if critical_gaps:
        issues.append(f"CRITICAL: {len(critical_gaps)} CRITICAL-priority gap(s) open")
        exit_code = 1

    if strict and high_gaps:
        issues.append(f"HIGH: {len(high_gaps)} HIGH-priority gap(s) open (--strict mode)")
        exit_code = 1

    if not floor_ok:
        issues.append(f"E2E coverage {e2e_pct}% is below floor {e2e_floor}%")
        if strict:
            exit_code = 1

    if overdue:
        issues.append(f"OVERDUE: {len(overdue)} gap(s) exceeded max age")
        exit_code = max(exit_code, 1)

    status = "PASS" if exit_code == 0 else "FAIL"
    e2e_files = count_e2e_files()
    screenshots = count_screenshots()

    lines = [
        "# Harness SLA Report",
        "",
        f"Generated: `{now}`",
        f"Status: **{status}**",
        "",
        "## Coverage Summary",
        "",
        "| Metric | Value | Target |",
        "|--------|-------|--------|",
        f"| E2E coverage | {e2e_pct}% ({has_e2e}/{total_features} features) | >={e2e_floor}% |",
        f"| Browser evidence | {evidence_pct}% ({has_evidence}/{total_features} features) | required for CRITICAL/HIGH |",
        f"| E2E test files | {e2e_files} | -- |",
        f"| Screenshot artifacts | {screenshots} | -- |",
        "",
        "## Open Gaps by Priority",
        "",
    ]

    if critical_gaps:
        lines.append("### [CRITICAL] (CI blocker)")
        for gap in critical_gaps:
            lines.append(f"- {gap['feature']}")
        lines.append("")

    if high_gaps:
        lines.append("### [HIGH]")
        for gap in high_gaps:
            lines.append(f"- {gap['feature']}")
        lines.append("")

    medium_gaps = [r for r in coverage_rows if r["priority"] == "MEDIUM" and "MISSING" in r["e2e_tests"]]
    if medium_gaps:
        lines.append("### [MEDIUM]")
        for gap in medium_gaps:
            lines.append(f"- {gap['feature']}")
        lines.append("")

    if overdue:
        lines.append("### Overdue Gaps")
        for gap in overdue:
            lines.append(f"- {gap['gap']} (due {gap['max_age']})")
        lines.append("")

    if issues:
        lines += ["## Issues", ""]
        for issue in issues:
            lines.append(f"- {issue}")
        lines.append("")

    lines += [
        "## Next Actions",
        "",
        "See `HARNESS_GAPS.md` for closure protocol.",
        "Run `bash scripts/harness/ui/run_e2e.sh` to generate new browser evidence.",
    ]

    return "\n".join(lines) + "\n", exit_code


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Harness SLA checker")
    parser.add_argument("--report-file", type=Path, help="Write report to this file")
    parser.add_argument("--strict", action="store_true", help="Also fail on HIGH gaps")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not HARNESS_GAPS_PATH.exists():
        print(f"ERROR: HARNESS_GAPS.md not found at {HARNESS_GAPS_PATH}", file=sys.stderr)
        return 2

    text = HARNESS_GAPS_PATH.read_text(encoding="utf-8")
    coverage_rows = parse_gap_table(text)
    age_rows = parse_gap_age_table(text)
    sla = parse_sla_json(text)

    report, exit_code = build_report(coverage_rows, age_rows, sla, args.strict)

    # Use UTF-8 writer to handle emoji in HARNESS_GAPS.md on Windows
    sys.stdout.buffer.write(report.encode("utf-8"))
    sys.stdout.buffer.flush()

    if args.report_file:
        args.report_file.parent.mkdir(parents=True, exist_ok=True)
        args.report_file.write_text(report, encoding="utf-8")
        sys.stdout.buffer.write(f"Report written to {args.report_file}\n".encode("utf-8"))
        sys.stdout.buffer.flush()

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
