#!/usr/bin/env python3
"""Risk-tier gate: classify changed files against risk-policy.json and emit required checks.

Usage:
    python scripts/governance/risk_tier_gate.py --changed-files <file1> <file2> ...
    python scripts/governance/risk_tier_gate.py --from-git-diff  # reads working tree diff
    python scripts/governance/risk_tier_gate.py --from-staged-diff  # reads staged diff

Exit codes:
    0 — classification complete (always exits 0; consumers decide gate logic)

Output (JSON to stdout):
    {
        "tier": "critical"|"high"|"standard"|"low",
        "required_checks": [...],
        "block_merge_on_failure": bool,
        "matched_files": { "<file>": "<tier>" },
        "policy_version": "1.0.0"
    }
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = REPO_ROOT / "risk-policy.json"

TIER_ORDER = ["critical", "high", "standard", "low"]


def load_policy() -> dict:
    if not POLICY_PATH.exists():
        print(f"ERROR: risk-policy.json not found at {POLICY_PATH}", file=sys.stderr)
        sys.exit(2)
    with POLICY_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def classify_file(path: str, policy: dict) -> str:
    """Return the highest-risk tier that matches path."""
    # Override list always wins
    for override in policy.get("override_to_critical", []):
        if fnmatch.fnmatch(path, override):
            return "critical"

    resolution = policy.get("tier_resolution", "highest_match_wins")
    matched_tier = "low"

    for tier_name in TIER_ORDER:
        tier = policy["tiers"].get(tier_name, {})
        for pattern in tier.get("paths", []):
            if fnmatch.fnmatch(path, pattern):
                if resolution == "highest_match_wins":
                    # critical is highest — return immediately
                    if tier_name == "critical":
                        return "critical"
                    # Track highest seen so far
                    if TIER_ORDER.index(tier_name) < TIER_ORDER.index(matched_tier):
                        matched_tier = tier_name
                break

    return matched_tier


def resolve_overall_tier(file_tiers: dict[str, str]) -> str:
    """Highest tier among all files wins."""
    if not file_tiers:
        return "low"
    return min(file_tiers.values(), key=lambda t: TIER_ORDER.index(t))


def get_changed_files_from_git(staged_only: bool = False) -> list[str]:
    try:
        if staged_only:
            result = subprocess.run(
                ["git", "diff", "--name-only", "--cached"],
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=True,
            )
            return [f.strip() for f in result.stdout.splitlines() if f.strip()]

        result = subprocess.run(
            ["git", "diff", "--name-only"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            check=True,
        )
        files = [f.strip() for f in result.stdout.splitlines() if f.strip()]
        if not files:
            # Fallback for clean working tree: staged files
            result = subprocess.run(
                ["git", "diff", "--name-only", "--cached"],
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=True,
            )
            files = [f.strip() for f in result.stdout.splitlines() if f.strip()]
        return files
    except subprocess.CalledProcessError as exc:
        print(f"ERROR: git diff failed: {exc}", file=sys.stderr)
        sys.exit(2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Risk-tier gate classifier")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--changed-files",
        nargs="+",
        metavar="FILE",
        help="Explicit list of changed file paths (relative to repo root)",
    )
    group.add_argument(
        "--from-git-diff",
        action="store_true",
        help="Auto-detect changed files from working tree git diff",
    )
    group.add_argument(
        "--from-staged-diff",
        action="store_true",
        help="Auto-detect changed files from staged git diff",
    )
    parser.add_argument(
        "--policy",
        default=str(POLICY_PATH),
        help="Path to risk-policy.json (default: repo root)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    policy = load_policy()

    if args.from_git_diff:
        changed_files = get_changed_files_from_git(staged_only=False)
    elif args.from_staged_diff:
        changed_files = get_changed_files_from_git(staged_only=True)
    else:
        changed_files = args.changed_files or []

    if not changed_files:
        # No files changed — emit low tier
        result = {
            "tier": "low",
            "required_checks": policy["tiers"]["low"]["required_checks"],
            "block_merge_on_failure": policy["tiers"]["low"]["block_merge_on_failure"],
            "matched_files": {},
            "policy_version": policy.get("version", "unknown"),
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    file_tiers: dict[str, str] = {}
    for f in changed_files:
        file_tiers[f] = classify_file(f, policy)

    overall_tier = resolve_overall_tier(file_tiers)
    tier_config = policy["tiers"][overall_tier]

    result = {
        "tier": overall_tier,
        "required_checks": tier_config["required_checks"],
        "block_merge_on_failure": tier_config["block_merge_on_failure"],
        "matched_files": file_tiers,
        "policy_version": policy.get("version", "unknown"),
    }

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
