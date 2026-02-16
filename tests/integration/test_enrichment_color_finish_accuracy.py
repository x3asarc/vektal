"""Phase 13.1-04 color/finish benchmark contracts."""
from __future__ import annotations

from src.core.enrichment.benchmarks import evaluate_color_finish_accuracy


def test_color_finish_accuracy_reports_combined_delta_and_profile_accuracy():
    samples = [
        {
            "profile_name": "deep",
            "predicted_color": "blue",
            "audited_color": "blue",
            "predicted_finish": "matte",
            "audited_finish": "matte",
        },
        {
            "profile_name": "deep",
            "predicted_color": "red",
            "audited_color": "red",
            "predicted_finish": "glossy",
            "audited_finish": "matte",
        },
        {
            "profile_name": "standard",
            "predicted_color": "green",
            "audited_color": "green",
            "predicted_finish": "metallic",
            "audited_finish": "metallic",
        },
    ]

    report = evaluate_color_finish_accuracy(samples)

    assert report["sample_count"] == 3
    assert round(report["color_accuracy"], 4) == 1.0
    assert round(report["finish_accuracy"], 4) == round(2 / 3, 4)
    assert round(report["combined_accuracy"], 4) == round((1.0 + (2 / 3)) / 2, 4)
    assert report["profile_accuracy"]["deep"]["total_count"] == 2
    assert report["profile_accuracy"]["standard"]["strict_accuracy"] == 1.0
