"""Phase 13.1-04 retrieval-readiness benchmark contracts."""
from __future__ import annotations

from src.core.enrichment.benchmarks import evaluate_retrieval_readiness


def test_retrieval_readiness_reports_overall_and_profile_coverage():
    rows = [
        {"profile_name": "quick", "trust": {"retrieval_ready": True, "critical_missing_fields": []}},
        {"profile_name": "quick", "trust": {"retrieval_ready": False, "critical_missing_fields": ["title"]}},
        {"profile_name": "standard", "trust": {"retrieval_ready": True, "critical_missing_fields": []}},
        {"profile_name": "deep", "trust": {"retrieval_ready": True, "critical_missing_fields": []}},
    ]

    report = evaluate_retrieval_readiness(rows)

    assert report["total_count"] == 4
    assert report["ready_count"] == 3
    assert report["coverage"] == 0.75
    assert report["profile_coverage"]["quick"]["coverage"] == 0.5
    assert report["profile_coverage"]["standard"]["coverage"] == 1.0
    assert report["critical_missing_counts"]["title"] == 1
