"""Phase 13.1-04 semantic uplift smoke benchmark contracts."""
from __future__ import annotations

from src.core.enrichment.benchmarks import evaluate_semantic_uplift_smoke
from src.core.enrichment.evaluation import evaluate_phase13_1_gate


def test_semantic_uplift_smoke_reports_recall_and_ndcg_uplift():
    queries = [
        {
            "profile_name": "standard",
            "relevant_ids": ["p1", "p3"],
            "baseline_ranked_ids": ["x1", "p1", "x2", "x3", "x4"],
            "enriched_ranked_ids": ["p1", "p3", "x2", "x3", "x4"],
        },
        {
            "profile_name": "deep",
            "relevant_ids": ["p9"],
            "baseline_ranked_ids": ["x8", "x7", "p9", "x6"],
            "enriched_ranked_ids": ["p9", "x8", "x7", "x6"],
        },
    ]

    report = evaluate_semantic_uplift_smoke(queries, k=3)
    assert report["query_count"] == 2
    assert report["recall_uplift"] > 0.0
    assert report["ndcg_uplift"] > 0.0
    assert "deep" in report["profile_metrics"]


def test_phase13_1_gate_passes_when_observed_metrics_clear_thresholds():
    verdict = evaluate_phase13_1_gate(
        retrieval_readiness={"coverage": 0.9},
        color_finish_accuracy={"delta_to_perfect": 0.08},
        semantic_uplift={"recall_uplift": 0.04, "ndcg_uplift": 0.02},
    )
    assert verdict.passed is True
    assert verdict.fail_reasons == ()
