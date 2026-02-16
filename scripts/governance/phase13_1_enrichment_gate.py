#!/usr/bin/env python3
"""Phase 13.1 enrichment go/no-go gate."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.core.enrichment.evaluation import evaluate_phase13_1_gate


DEFAULT_VERIFICATION_PATH = (
    REPO_ROOT
    / ".planning"
    / "phases"
    / "13.1-product-data-enrichment-protocol-v2-integration"
    / "13.1-VERIFICATION.md"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate Phase 13.1 enrichment release gate.")
    parser.add_argument("--dry-run", action="store_true", help="Use deterministic synthetic benchmark payloads.")
    parser.add_argument(
        "--metrics-json",
        type=Path,
        default=None,
        help="Optional JSON file with keys: retrieval_readiness, color_finish_accuracy, semantic_uplift.",
    )
    parser.add_argument(
        "--verification-path",
        type=Path,
        default=DEFAULT_VERIFICATION_PATH,
        help="Verification artifact required for final go decision.",
    )
    parser.add_argument("--retrieval-min", type=float, default=0.85)
    parser.add_argument("--color-delta-max", type=float, default=0.10)
    parser.add_argument("--recall-uplift-min", type=float, default=0.0)
    parser.add_argument("--ndcg-uplift-min", type=float, default=0.0)
    return parser.parse_args()


def _load_metrics_from_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    required = {"retrieval_readiness", "color_finish_accuracy", "semantic_uplift"}
    missing = sorted(required - set(data.keys()))
    if missing:
        raise ValueError(f"metrics JSON missing keys: {', '.join(missing)}")
    return data


def _synthetic_metrics() -> dict:
    return {
        "retrieval_readiness": {
            "coverage": 0.92,
            "ready_count": 92,
            "total_count": 100,
            "profile_coverage": {
                "quick": {"coverage": 0.90, "ready_count": 30, "total_count": 33},
                "standard": {"coverage": 0.93, "ready_count": 31, "total_count": 33},
                "deep": {"coverage": 0.94, "ready_count": 31, "total_count": 33},
            },
        },
        "color_finish_accuracy": {
            "combined_accuracy": 0.91,
            "delta_to_perfect": 0.09,
            "color_accuracy": 0.92,
            "finish_accuracy": 0.90,
        },
        "semantic_uplift": {
            "recall_uplift": 0.12,
            "ndcg_uplift": 0.08,
            "baseline_recall_at_k": 0.45,
            "enriched_recall_at_k": 0.57,
            "baseline_ndcg_at_k": 0.41,
            "enriched_ndcg_at_k": 0.49,
        },
    }


def main() -> int:
    args = parse_args()

    if args.metrics_json is not None:
        metrics = _load_metrics_from_json(args.metrics_json)
    elif args.dry_run:
        metrics = _synthetic_metrics()
    else:
        raise SystemExit("Provide --dry-run or --metrics-json for gate evaluation.")

    thresholds = {
        "retrieval_readiness_min_coverage": args.retrieval_min,
        "color_finish_max_delta": args.color_delta_max,
        "semantic_min_recall_uplift": args.recall_uplift_min,
        "semantic_min_ndcg_uplift": args.ndcg_uplift_min,
    }

    verdict = evaluate_phase13_1_gate(
        retrieval_readiness=metrics["retrieval_readiness"],
        color_finish_accuracy=metrics["color_finish_accuracy"],
        semantic_uplift=metrics["semantic_uplift"],
        thresholds=thresholds,
    ).to_dict()

    verification_exists = args.verification_path.exists()
    output = {
        "phase": "13.1",
        "gate": "enrichment_go_no_go",
        "verification_path": str(args.verification_path),
        "verification_exists": verification_exists,
        "dry_run": bool(args.dry_run),
        "verdict": verdict,
    }
    print(json.dumps(output, indent=2, sort_keys=True))

    if not verdict["passed"]:
        return 1
    if not verification_exists and not args.dry_run:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
