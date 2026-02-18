#!/usr/bin/env python3
"""Evaluate Phase 13 canary rollback gate from explicit inputs."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.assistant.deployment.canary_guard import evaluate_canary_rollback


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase 13 canary rollback gate evaluator")
    parser.add_argument("--baseline", required=True, type=float, help="Baseline availability (0..1)")
    parser.add_argument("--canary", required=True, type=float, help="Canary availability (0..1)")
    parser.add_argument("--sample-size", required=True, type=int, help="Canary sample size")
    parser.add_argument(
        "--scope-match",
        choices=["true", "false"],
        default="true",
        help="Whether baseline/canary scopes are equivalent",
    )
    parser.add_argument("--threshold-drop", type=float, default=0.05, help="Rollback drop threshold")
    parser.add_argument("--sample-floor", type=int, default=100, help="Minimum sample floor")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    decision = evaluate_canary_rollback(
        baseline_availability=args.baseline,
        canary_availability=args.canary,
        sample_size=args.sample_size,
        scope_match=args.scope_match == "true",
        threshold_drop=args.threshold_drop,
        sample_floor=args.sample_floor,
    )
    print(json.dumps(decision.to_dict(), indent=2, sort_keys=True))
    return 1 if decision.should_rollback else 0


if __name__ == "__main__":
    sys.exit(main())
