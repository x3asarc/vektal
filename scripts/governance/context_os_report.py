#!/usr/bin/env python3
"""Render Context OS gate output as JSON or markdown."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.governance.context_os_gate import GateResult, run_gate


def _to_markdown(result: GateResult) -> str:
    lines: list[str] = []
    lines.append("# Context OS Gate Report")
    lines.append("")
    lines.append(f"- Status: `{result.status}`")
    lines.append(f"- Checked at: `{result.checked_at}`")
    lines.append(f"- Window hours: `{result.window_hours}`")
    lines.append("")
    lines.append("| Metric | Status | Threshold | Reason | Remediation |")
    lines.append("| --- | --- | --- | --- | --- |")
    for metric in result.metrics:
        status = "PASS" if metric.passed else "FAIL"
        reason = metric.reason_code or "-"
        remediation = metric.remediation.replace("|", "/")
        lines.append(
            f"| `{metric.name}` | `{status}` | `{metric.threshold}` | `{reason}` | {remediation} |"
        )
    lines.append("")
    lines.append("## Metric Payload")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    lines.append("```")
    return "\n".join(lines)


def _emit(text: str, output_path: Path | None) -> None:
    if output_path is None:
        print(text)
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text + "\n", encoding="utf-8")
    print(str(output_path))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Context OS gate report generator.")
    parser.add_argument("--window-hours", type=int, default=24, help="Metric evaluation window in hours")
    parser.add_argument("--format", choices=["json", "markdown"], default="json", help="Report output format")
    parser.add_argument("--repo-root", type=Path, help="Optional repository root override")
    parser.add_argument("--memory-root", type=Path, help="Optional memory root override")
    parser.add_argument("--output", type=Path, help="Optional output file path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_gate(
        window_hours=args.window_hours,
        repo_root=args.repo_root,
        memory_root=args.memory_root,
    )
    if args.format == "markdown":
        payload = _to_markdown(result)
    else:
        payload = json.dumps(result.to_dict(), indent=2, sort_keys=True)
    _emit(payload, args.output)
    return 0 if result.status == "GREEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
