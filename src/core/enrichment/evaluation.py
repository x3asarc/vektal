"""Evaluation and threshold gating for Phase 13.1 enrichment benchmarks."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


DEFAULT_GATE_THRESHOLDS = {
    "retrieval_readiness_min_coverage": 0.85,
    "color_finish_max_delta": 0.10,
    "semantic_min_recall_uplift": 0.0,
    "semantic_min_ndcg_uplift": 0.0,
}


@dataclass(frozen=True)
class EnrichmentGateVerdict:
    passed: bool
    fail_reasons: tuple[str, ...]
    thresholds: dict[str, float]
    observed: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "fail_reasons": list(self.fail_reasons),
            "thresholds": dict(self.thresholds),
            "observed": dict(self.observed),
        }


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def evaluate_phase13_1_gate(
    *,
    retrieval_readiness: dict[str, Any],
    color_finish_accuracy: dict[str, Any],
    semantic_uplift: dict[str, Any],
    thresholds: dict[str, float] | None = None,
) -> EnrichmentGateVerdict:
    """
    Compute deterministic phase gate verdict from benchmark outputs.
    """
    effective_thresholds = dict(DEFAULT_GATE_THRESHOLDS)
    if thresholds:
        effective_thresholds.update({key: float(value) for key, value in thresholds.items()})

    observed = {
        "retrieval_coverage": _as_float(retrieval_readiness.get("coverage")),
        "color_finish_delta": _as_float(color_finish_accuracy.get("delta_to_perfect"), default=1.0),
        "recall_uplift": _as_float(semantic_uplift.get("recall_uplift")),
        "ndcg_uplift": _as_float(semantic_uplift.get("ndcg_uplift")),
    }

    fail_reasons: list[str] = []
    if observed["retrieval_coverage"] < effective_thresholds["retrieval_readiness_min_coverage"]:
        fail_reasons.append("retrieval_readiness_below_threshold")
    if observed["color_finish_delta"] > effective_thresholds["color_finish_max_delta"]:
        fail_reasons.append("color_finish_delta_above_threshold")
    if observed["recall_uplift"] < effective_thresholds["semantic_min_recall_uplift"]:
        fail_reasons.append("recall_uplift_below_threshold")
    if observed["ndcg_uplift"] < effective_thresholds["semantic_min_ndcg_uplift"]:
        fail_reasons.append("ndcg_uplift_below_threshold")

    return EnrichmentGateVerdict(
        passed=len(fail_reasons) == 0,
        fail_reasons=tuple(fail_reasons),
        thresholds=effective_thresholds,
        observed=observed,
    )
