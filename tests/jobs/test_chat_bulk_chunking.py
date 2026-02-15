"""Phase 10-03 chunk planner tests for chat bulk orchestration."""
from __future__ import annotations

import pytest

from src.api.v1.chat.bulk import (
    BulkPlanError,
    MAX_BULK_SKUS,
    MAX_CHUNK_INPUTS,
    normalize_bulk_skus,
    plan_chunks,
)


def test_normalize_bulk_skus_dedupes_and_preserves_order():
    normalized = normalize_bulk_skus(["sku-1", "SKU-2", "sku-1", "Sku-3"])
    assert normalized == ["SKU-1", "SKU-2", "SKU-3"]


def test_plan_chunks_enforces_input_bounds_and_lineage():
    raw = [f"SKU-{idx:04d}" for idx in range(1, 321)]
    plan = plan_chunks(raw_skus=raw, requested_chunk_size=250)

    assert plan.total_skus == 320
    assert len(plan.chunks) >= 2
    for chunk in plan.chunks:
        assert len(chunk.skus) <= MAX_CHUNK_INPUTS
        assert chunk.chunk_id.startswith("chunk-")
        assert chunk.replay_key.startswith("bulk:")
        assert isinstance(chunk.lineage["chunk_index"], int)
        assert chunk.lineage["sku_count"] == len(chunk.skus)


def test_bulk_limit_exceeded_raises_clear_error():
    raw = [f"SKU-{idx:05d}" for idx in range(1, MAX_BULK_SKUS + 2)]
    with pytest.raises(BulkPlanError) as exc:
        plan_chunks(raw_skus=raw)
    assert exc.value.error_type == "bulk-limit-exceeded"
    assert str(MAX_BULK_SKUS) in exc.value.detail


def test_invalid_sku_raises_validation_error():
    with pytest.raises(BulkPlanError) as exc:
        normalize_bulk_skus(["SKU-100", "###bad###"])
    assert exc.value.error_type == "invalid-sku"
