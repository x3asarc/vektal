#!/usr/bin/env python3
"""Build a markdown evidence index from Playwright screenshot artifacts.

Usage:
    python scripts/harness/ui/evidence_index.py \
        --results-dir test-results/playwright-artifacts \
        --output test-results/playwright-artifacts/EVIDENCE_INDEX.md
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path


def build_index(results_dir: Path, output: Path) -> None:
    screenshots = sorted(results_dir.glob("**/*.png"))
    traces = sorted(results_dir.glob("**/*.zip"))

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    lines = [
        "# Playwright Evidence Index",
        "",
        f"Generated: `{now}`",
        f"Results dir: `{results_dir}`",
        "",
        "## Screenshots",
        "",
    ]

    if screenshots:
        for shot in screenshots:
            rel = shot.relative_to(results_dir) if shot.is_relative_to(results_dir) else shot
            test_name = shot.stem.replace("-", " ").replace("_", " ").title()
            lines.append(f"### {test_name}")
            lines.append(f"- File: `{rel}`")
            lines.append(f"- Size: {shot.stat().st_size:,} bytes")
            lines.append("")
    else:
        lines.append("_No screenshots captured. Screenshots are taken on test failure._")
        lines.append("")

    lines += [
        "## Traces",
        "",
    ]

    if traces:
        for trace in traces:
            rel = trace.relative_to(results_dir) if trace.is_relative_to(results_dir) else trace
            lines.append(f"- `{rel}` ({trace.stat().st_size:,} bytes)")
        lines.append("")
        lines.append("View traces: `npx playwright show-trace <path-to-trace.zip>`")
    else:
        lines.append("_No traces captured. Traces are recorded on first retry._")

    lines += [
        "",
        "## Coverage Note",
        "",
        "These artifacts are the browser-evidence first-class proof referenced in HARNESS_GAPS.md.",
        "Check `check_harness_slas.py` for coverage gap analysis.",
    ]

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Evidence index written to {output}")
    print(f"  Screenshots: {len(screenshots)}")
    print(f"  Traces: {len(traces)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Playwright evidence index")
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.results_dir.exists():
        args.results_dir.mkdir(parents=True, exist_ok=True)
    build_index(args.results_dir, args.output)


if __name__ == "__main__":
    main()
