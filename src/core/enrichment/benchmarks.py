"""Benchmark contracts for Phase 13.1 enrichment quality gates."""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Any


def _safe_div(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return float(numerator) / float(denominator)


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def evaluate_retrieval_readiness(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Evaluate retrieval-readiness from enrichment payloads.

    Expected row shape:
    - profile_name: quick|standard|deep
    - trust: { retrieval_ready: bool, critical_missing_fields: list[str] }
    """
    profile_totals: dict[str, int] = defaultdict(int)
    profile_ready: dict[str, int] = defaultdict(int)
    critical_missing_counts: dict[str, int] = defaultdict(int)
    ready_count = 0

    for row in rows:
        profile = str(row.get("profile_name") or "unknown")
        trust = row.get("trust") if isinstance(row.get("trust"), dict) else {}
        retrieval_ready = bool(trust.get("retrieval_ready"))
        profile_totals[profile] += 1
        if retrieval_ready:
            ready_count += 1
            profile_ready[profile] += 1
        missing_fields = trust.get("critical_missing_fields")
        if isinstance(missing_fields, list):
            for field_name in missing_fields:
                critical_missing_counts[str(field_name)] += 1

    total = len(rows)
    profile_coverage = {
        profile: {
            "ready_count": profile_ready.get(profile, 0),
            "total_count": count,
            "coverage": _safe_div(profile_ready.get(profile, 0), count),
        }
        for profile, count in sorted(profile_totals.items())
    }

    return {
        "total_count": total,
        "ready_count": ready_count,
        "coverage": _safe_div(ready_count, total),
        "profile_coverage": profile_coverage,
        "critical_missing_counts": dict(sorted(critical_missing_counts.items())),
    }


def evaluate_color_finish_accuracy(samples: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Evaluate color/finish structured accuracy on audited samples.

    Expected sample shape:
    - predicted_color / audited_color
    - predicted_finish / audited_finish
    """
    color_hits = 0
    color_total = 0
    finish_hits = 0
    finish_total = 0
    profile_totals: dict[str, int] = defaultdict(int)
    profile_hits: dict[str, int] = defaultdict(int)

    for sample in samples:
        profile = str(sample.get("profile_name") or "unknown")
        predicted_color = str(sample.get("predicted_color") or "").strip().lower()
        audited_color = str(sample.get("audited_color") or "").strip().lower()
        predicted_finish = str(sample.get("predicted_finish") or "").strip().lower()
        audited_finish = str(sample.get("audited_finish") or "").strip().lower()

        profile_totals[profile] += 1

        is_color_match = bool(predicted_color and audited_color and predicted_color == audited_color)
        is_finish_match = bool(predicted_finish and audited_finish and predicted_finish == audited_finish)
        # Count field-level totals only when both labels exist.
        if predicted_color and audited_color:
            color_total += 1
            if is_color_match:
                color_hits += 1
        if predicted_finish and audited_finish:
            finish_total += 1
            if is_finish_match:
                finish_hits += 1
        if is_color_match and is_finish_match:
            profile_hits[profile] += 1

    color_accuracy = _safe_div(color_hits, color_total)
    finish_accuracy = _safe_div(finish_hits, finish_total)
    combined_accuracy = _mean([color_accuracy, finish_accuracy])
    profile_accuracy = {
        profile: {
            "strict_match_count": profile_hits.get(profile, 0),
            "total_count": total,
            "strict_accuracy": _safe_div(profile_hits.get(profile, 0), total),
        }
        for profile, total in sorted(profile_totals.items())
    }

    return {
        "sample_count": len(samples),
        "color_accuracy": color_accuracy,
        "finish_accuracy": finish_accuracy,
        "combined_accuracy": combined_accuracy,
        "delta_to_perfect": max(0.0, 1.0 - combined_accuracy),
        "profile_accuracy": profile_accuracy,
    }


def recall_at_k(*, ranked_ids: list[str], relevant_ids: set[str], k: int) -> float:
    if k <= 0 or not relevant_ids:
        return 0.0
    top_k = [str(item) for item in ranked_ids[:k]]
    hits = sum(1 for item in top_k if item in relevant_ids)
    return _safe_div(hits, len(relevant_ids))


def ndcg_at_k(*, ranked_ids: list[str], relevant_ids: set[str], k: int) -> float:
    if k <= 0 or not relevant_ids:
        return 0.0
    top_k = [str(item) for item in ranked_ids[:k]]

    dcg = 0.0
    for idx, doc_id in enumerate(top_k, start=1):
        rel = 1.0 if doc_id in relevant_ids else 0.0
        if rel > 0:
            dcg += rel / math.log2(idx + 1)

    ideal_hits = min(len(relevant_ids), k)
    if ideal_hits <= 0:
        return 0.0
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_hits + 1))
    if idcg <= 0:
        return 0.0
    return dcg / idcg


def evaluate_semantic_uplift_smoke(queries: list[dict[str, Any]], *, k: int = 10) -> dict[str, Any]:
    """
    Compare baseline vs enriched ranking quality on fixed query set.

    Query shape:
    - relevant_ids: list[str]
    - baseline_ranked_ids: list[str]
    - enriched_ranked_ids: list[str]
    - profile_name: quick|standard|deep (optional)
    """
    baseline_recall: list[float] = []
    enriched_recall: list[float] = []
    baseline_ndcg: list[float] = []
    enriched_ndcg: list[float] = []
    profile_rows: dict[str, list[dict[str, float]]] = defaultdict(list)

    for query in queries:
        relevant_ids = {str(item) for item in (query.get("relevant_ids") or [])}
        baseline_ids = [str(item) for item in (query.get("baseline_ranked_ids") or [])]
        enriched_ids = [str(item) for item in (query.get("enriched_ranked_ids") or [])]
        profile = str(query.get("profile_name") or "unknown")

        base_recall = recall_at_k(ranked_ids=baseline_ids, relevant_ids=relevant_ids, k=k)
        enrich_recall = recall_at_k(ranked_ids=enriched_ids, relevant_ids=relevant_ids, k=k)
        base_ndcg = ndcg_at_k(ranked_ids=baseline_ids, relevant_ids=relevant_ids, k=k)
        enrich_ndcg = ndcg_at_k(ranked_ids=enriched_ids, relevant_ids=relevant_ids, k=k)

        baseline_recall.append(base_recall)
        enriched_recall.append(enrich_recall)
        baseline_ndcg.append(base_ndcg)
        enriched_ndcg.append(enrich_ndcg)
        profile_rows[profile].append(
            {
                "baseline_recall": base_recall,
                "enriched_recall": enrich_recall,
                "baseline_ndcg": base_ndcg,
                "enriched_ndcg": enrich_ndcg,
            }
        )

    baseline_recall_avg = _mean(baseline_recall)
    enriched_recall_avg = _mean(enriched_recall)
    baseline_ndcg_avg = _mean(baseline_ndcg)
    enriched_ndcg_avg = _mean(enriched_ndcg)

    profile_metrics = {}
    for profile, rows in sorted(profile_rows.items()):
        profile_metrics[profile] = {
            "baseline_recall_at_k": _mean([row["baseline_recall"] for row in rows]),
            "enriched_recall_at_k": _mean([row["enriched_recall"] for row in rows]),
            "baseline_ndcg_at_k": _mean([row["baseline_ndcg"] for row in rows]),
            "enriched_ndcg_at_k": _mean([row["enriched_ndcg"] for row in rows]),
        }

    return {
        "query_count": len(queries),
        "k": k,
        "baseline_recall_at_k": baseline_recall_avg,
        "enriched_recall_at_k": enriched_recall_avg,
        "baseline_ndcg_at_k": baseline_ndcg_avg,
        "enriched_ndcg_at_k": enriched_ndcg_avg,
        "recall_uplift": enriched_recall_avg - baseline_recall_avg,
        "ndcg_uplift": enriched_ndcg_avg - baseline_ndcg_avg,
        "profile_metrics": profile_metrics,
    }
