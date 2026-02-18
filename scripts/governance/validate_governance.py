#!/usr/bin/env python3
"""Validate governance baseline artifacts and Compound Engineering OS gate loop."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
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

REQUIRED_ROLE_FILES = [
    Path("ops/governance/roles/README.md"),
    Path("ops/governance/roles/phase-manager.md"),
    Path("ops/governance/roles/builder.md"),
    Path("ops/governance/roles/reviewer.md"),
    Path("ops/governance/roles/structure-guardian.md"),
    Path("ops/governance/roles/integrity-warden.md"),
    Path("ops/governance/roles/context-curator.md"),
]


@dataclass
class CheckResult:
    ok: bool
    message: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate governance artifacts and report set.")
    parser.add_argument("--phase", required=True, help="Phase identifier (example: 07)")
    parser.add_argument("--task", required=True, help="Task identifier (example: 07.1-governance-baseline-dry-run)")
    parser.add_argument("--mode", choices=["baseline", "full-loop"], default="baseline", help="Validation depth")
    parser.add_argument("--plan-id", help="Plan id used by the task (example: 02)")
    parser.add_argument("--plan-path", help="Explicit task PLAN.md path")
    parser.add_argument("--max-master-map-age-days", type=int, default=1, help="Max age for MASTER_MAP batch date")
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


def extract_status(text: str) -> str | None:
    match = re.search(r"^Status:\s*`?(.+?)`?$", text, re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip()


def validate_binary_gate_status(report_dir: Path, require_green: bool) -> list[CheckResult]:
    results: list[CheckResult] = []
    files = {
        "self-check": report_dir / "self-check.md",
        "review": report_dir / "review.md",
        "structure-audit": report_dir / "structure-audit.md",
        "integrity-audit": report_dir / "integrity-audit.md",
    }

    for label, path in files.items():
        text = read_text(path)
        status = extract_status(text)
        if status is None:
            results.append(CheckResult(False, f"{label} missing Status field"))
            continue
        if status not in {"GREEN", "RED"}:
            results.append(CheckResult(False, f"{label} status must be GREEN or RED (got: {status})"))
            continue
        results.append(CheckResult(True, f"{label} status is binary ({status})"))
        if require_green:
            results.append(CheckResult(status == "GREEN", f"{label} status GREEN required for full-loop"))
    return results


def validate_review_blocking_policy(report_dir: Path, require_green: bool) -> list[CheckResult]:
    review = read_text(report_dir / "review.md")
    results: list[CheckResult] = []

    findings = re.findall(r"^\[(Critical|High|Medium|Low)\]\s+\[([^\]]+)\]", review, re.MULTILINE)
    blocking: list[tuple[str, str]] = []
    for sev, cat in findings:
        sev_n = sev.strip()
        cat_n = cat.strip().lower()
        if sev_n in {"Critical", "High"}:
            blocking.append((sev_n, cat))
        elif sev_n == "Medium" and ("security" in cat_n or "dependency" in cat_n):
            blocking.append((sev_n, cat))

    if blocking:
        preview = ", ".join([f"{sev}/{cat}" for sev, cat in blocking[:4]])
        results.append(CheckResult(False, f"Blocking findings present per policy: {preview}"))
    else:
        results.append(CheckResult(True, "No blocking findings per policy"))

    blocking_decl = re.search(r"^\d+\.\s*Blocking findings present:\s*`?(Yes|No)`?", review, re.MULTILINE | re.IGNORECASE)
    if blocking_decl:
        declared_yes = blocking_decl.group(1).lower() == "yes"
        results.append(CheckResult(declared_yes == bool(blocking), "Review blocking declaration matches findings"))

    merge_decl = re.search(r"^\d+\.\s*Merge recommendation:\s*`?(GREEN|RED)`?", review, re.MULTILINE)
    if merge_decl:
        expected = "RED" if blocking else "GREEN"
        results.append(CheckResult(merge_decl.group(1) == expected, f"Merge recommendation matches policy ({expected})"))

    if require_green:
        status = extract_status(review) or ""
        results.append(CheckResult(status == "GREEN" and not blocking, "Review gate GREEN with no blocking findings"))
    return results


def validate_master_map_cadence(root: Path, max_age_days: int) -> CheckResult:
    text = read_text(root / "docs/MASTER_MAP.md")
    m = re.search(r"^Last batch update:\s*(\d{4}-\d{2}-\d{2})\s*$", text, re.MULTILINE)
    if not m:
        return CheckResult(False, "MASTER_MAP missing Last batch update date")
    try:
        updated = date.fromisoformat(m.group(1))
    except ValueError:
        return CheckResult(False, "MASTER_MAP Last batch update date format invalid")
    today = datetime.now(timezone.utc).date()
    age = (today - updated).days
    return CheckResult(age <= max_age_days, f"MASTER_MAP batch update age {age}d (max {max_age_days}d)")


def validate_state_task_tracking(root: Path, phase: str, task: str) -> list[CheckResult]:
    state = read_text(root / ".planning/STATE.md")
    checks = [
        CheckResult(task in state, "STATE references current task id"),
        CheckResult("## Governance Gate Snapshot" in state, "STATE has governance gate snapshot"),
    ]

    report_base = f"reports/{phase}/{task}/"
    checks.extend(
        [
            CheckResult(f"{report_base}self-check.md" in state, "STATE links self-check evidence"),
            CheckResult(f"{report_base}review.md" in state, "STATE links review evidence"),
            CheckResult(f"{report_base}structure-audit.md" in state, "STATE links structure evidence"),
            CheckResult(f"{report_base}integrity-audit.md" in state, "STATE links integrity evidence"),
            CheckResult("docs/MASTER_MAP.md" in state, "STATE links context sync evidence"),
        ]
    )
    return checks


def validate_roadmap_task_tracking(root: Path, task: str) -> list[CheckResult]:
    roadmap = read_text(root / ".planning/ROADMAP.md")
    return [
        CheckResult("Canonical governance spec" in roadmap, "ROADMAP marks canonical governance spec"),
        CheckResult("## Governance Baseline v1" in roadmap, "ROADMAP governance baseline section present"),
        CheckResult(task in roadmap, "ROADMAP governance board references task id"),
    ]


def validate_rules_file(root: Path) -> list[CheckResult]:
    rules_path = root / ".rules"
    text = read_text(rules_path)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    checks: list[CheckResult] = []

    invalid_nested = [ln for ln in lines if "&&" in ln or "||" in ln or ln.startswith("-") or ln.startswith("*")]
    checks.append(CheckResult(not invalid_nested, ".rules uses one-rule-per-line with no nested logic markers"))
    checks.append(CheckResult(any(ln.startswith("dependency_policy=") for ln in lines), ".rules defines dependency policy"))
    checks.append(CheckResult(any(ln.startswith("license_policy=") for ln in lines), ".rules defines license policy"))
    checks.append(CheckResult(any("kiss_warning_loc_threshold=500" in ln for ln in lines), ".rules includes KISS warning threshold"))
    checks.append(CheckResult(any("kiss_exception_loc_threshold=800" in ln for ln in lines), ".rules includes KISS exception threshold"))
    return checks


def validate_task_plan_exists(root: Path, task: str, plan_path: str | None, phase: str, plan_id: str | None) -> list[CheckResult]:
    checks: list[CheckResult] = []
    resolved: Path | None = None

    if plan_path:
        candidate = root / plan_path
        if candidate.exists():
            resolved = candidate

    if resolved is None:
        matches = list((root / ".planning" / "phases").glob(f"*/{task}/PLAN.md"))
        if matches:
            resolved = matches[0]

    if resolved is None and plan_id:
        normalized = plan_id.zfill(2) if plan_id.isdigit() else plan_id
        phase_prefix = phase.zfill(2) if phase.isdigit() else phase
        matches = list((root / ".planning" / "phases").glob(f"*/{phase_prefix}-{normalized}-PLAN.md"))
        if matches:
            resolved = matches[0]

    if resolved is None:
        checks.append(CheckResult(False, "Task PLAN.md not found (.planning/phases/<phase>/<task>/PLAN.md or mapped plan)"))
        return checks

    checks.append(CheckResult(True, f"Task plan found: {resolved.relative_to(root)}"))
    text = read_text(resolved)

    is_execute_schema = "<objective>" in text or "<tasks>" in text
    if is_execute_schema:
        required_tokens = [
            "<objective>",
            "<tasks>",
            "<verification>",
        ]
        for token in required_tokens:
            checks.append(CheckResult(token in text, f"Execute-plan token present: {token}"))
    else:
        required_sections = [
            "## Objective",
            "## Scope In",
            "## Scope Out",
            "## Atomic Checklist",
            "## Risks",
            "## Definition of Done",
            "## Gate Evidence Links",
        ]
        for section in required_sections:
            checks.append(CheckResult(section in text, f"Task plan section present: {section}"))
    return checks


def validate_failure_journey_rollout(root: Path) -> list[CheckResult]:
    text = read_text(root / "FAILURE_JOURNEY.md").lower()
    return [
        CheckResult("anti-drift" in text or "drift loop" in text, "FAILURE_JOURNEY contains anti-drift handling example"),
        CheckResult("anti-stubborn" in text or "stubborn loop" in text, "FAILURE_JOURNEY contains anti-stubborn handling example"),
    ]


def validate_journey_synthesis_cadence(root: Path, phase: str) -> CheckResult:
    int_part_match = re.match(r"^(\d+)", phase)
    if not int_part_match:
        return CheckResult(True, "Journey synthesis cadence check skipped for non-integer phase")
    phase_num = int(int_part_match.group(1))
    if phase_num % 3 != 0:
        return CheckResult(True, f"Journey synthesis not due on phase {phase_num}")
    files = [p for p in (root / "reports" / "meta").glob("journey-synthesis-*.md") if "template" not in p.name]
    return CheckResult(bool(files), f"Journey synthesis published for phase window ending at {phase_num}")


def validate_integrity_policy_signal(report_dir: Path, root: Path) -> list[CheckResult]:
    checks: list[CheckResult] = []
    text = read_text(report_dir / "integrity-audit.md")

    # Require explicit checklist outcomes for key integrity controls.
    for label_pattern, label_name in [
        (r"Unknown package risk", "Unknown package risk"),
        (r"Dependency pinning and lockfile evidence", "Dependency pinning and lockfile evidence"),
        (r"License policy compliance.*", "License policy compliance"),
        (r"Secret scan status", "Secret scan status"),
    ]:
        pattern = rf"^\d+\.\s*{label_pattern}:\s*`?(Pass|Fail|Action Required|N/A)`?\s*$"
        match = re.search(pattern, text, re.MULTILINE)
        checks.append(CheckResult(bool(match), f"Integrity checklist field present: {label_name}"))
        if match and match.group(1) in {"Fail", "Action Required"}:
            checks.append(CheckResult(False, f"Integrity blocking state for: {label_name}"))

    dep_line = re.search(r"^\d+\.\s*Added or changed dependencies:\s*`?(.+?)`?\s*$", text, re.MULTILINE)
    known_good = re.search(r"^\d+\.\s*Known-good registry checks:\s*`?(.+?)`?\s*$", text, re.MULTILINE)
    suppressions = re.search(r"^\d+\.\s*Suppressions with expiration date:\s*`?(.+?)`?\s*$", text, re.MULTILINE)

    checks.append(CheckResult(bool(dep_line), "Integrity dependency evidence line present"))
    checks.append(CheckResult(bool(known_good), "Integrity known-good registry line present"))
    checks.append(CheckResult(bool(suppressions), "Integrity suppressions line present"))

    dep_val = dep_line.group(1).strip().lower() if dep_line else ""
    if dep_val and dep_val not in {"n/a", "none"}:
        lockfiles = [
            root / "requirements.txt",
            root / "package-lock.json",
            root / "frontend/package-lock.json",
        ]
        checks.append(CheckResult(any(p.exists() for p in lockfiles), "Lockfile/pinning evidence present for dependency changes"))

    return checks


def validate_required_spec_sections(root: Path) -> list[CheckResult]:
    checks: list[CheckResult] = []

    agents = read_text(root / "AGENTS.md")
    for section in [
        "## Mission and non-negotiables",
        "## Role authority boundaries",
        "## Gate policy and blocking rules",
        "## Emergency bypass protocol",
        "## KISS limits",
        "## Artifact contract",
    ]:
        checks.append(CheckResult(section in agents, f"AGENTS section present: {section}"))

    standards = read_text(root / "STANDARDS.md")
    for section in [
        "## Severity taxonomy",
        "## Blocking matrix",
        "## Review checklist",
        "## Evidence format",
        "## Preventive rules loop",
    ]:
        checks.append(CheckResult(section in standards, f"STANDARDS section present: {section}"))

    structure = read_text(root / "ops/STRUCTURE_SPEC.md")
    for section in [
        "## Canonical map",
        "## Naming rules",
        "## File placement rules",
        "## Auto-move policy",
    ]:
        checks.append(CheckResult(section in structure, f"STRUCTURE_SPEC section present: {section}"))

    master = read_text(root / "docs/MASTER_MAP.md")
    for section in [
        "## TOC",
        "## Project Map",
        "## Module Index",
        "## Data and Logic Flow",
        "## Active Plans",
        "## Governance Links",
        "## Journey Synthesis Links",
    ]:
        checks.append(CheckResult(section in master, f"MASTER_MAP section present: {section}"))

    return checks


def validate_role_definition_linkage(root: Path) -> list[CheckResult]:
    checks: list[CheckResult] = []
    for rel_path in REQUIRED_ROLE_FILES:
        full = root / rel_path
        checks.append(CheckResult(full.exists(), f"Role definition {'found' if full.exists() else 'missing'}: {rel_path}"))

    agents = read_text(root / "AGENTS.md")
    for rel_path in REQUIRED_ROLE_FILES[1:]:
        checks.append(CheckResult(rel_path.as_posix() in agents, f"AGENTS links role definition: {rel_path.as_posix()}"))

    policy = read_text(root / "solutionsos/compound-engineering-os-policy.md")
    checks.append(CheckResult("ops/governance/roles/" in policy, "Policy references canonical role definitions path"))
    return checks


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

    if args.mode == "full-loop":
        checks.extend(validate_required_spec_sections(root))
        checks.extend(validate_role_definition_linkage(root))
        checks.extend(validate_rules_file(root))
        checks.extend(validate_task_plan_exists(root, task, args.plan_path, phase, args.plan_id))
        if report_dir.exists():
            checks.extend(validate_binary_gate_status(report_dir, require_green=True))
            checks.extend(validate_review_blocking_policy(report_dir, require_green=True))
            checks.extend(validate_integrity_policy_signal(report_dir, root))
        checks.extend(validate_state_task_tracking(root, phase, task))
        checks.extend(validate_roadmap_task_tracking(root, task))
        checks.append(validate_master_map_cadence(root, args.max_master_map_age_days))
        checks.extend(validate_failure_journey_rollout(root))
        checks.append(validate_journey_synthesis_cadence(root, phase))

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
