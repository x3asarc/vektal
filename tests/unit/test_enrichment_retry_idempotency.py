"""Phase 13.1-02 retry and idempotency contracts."""
from __future__ import annotations

import pytest

from src.core.enrichment.idempotency import EnrichmentIdempotencyCache, compute_enrichment_hash
from src.core.enrichment.retries import RetryExhaustedError, RetryPolicy, execute_with_retry


def test_idempotency_hash_is_policy_aware():
    payload = {"sku": "P-001", "title": "Acrylfarbe Rot 20ml"}
    key_v1 = compute_enrichment_hash(product_payload=payload, policy_version=1, profile_name="standard")
    key_v2 = compute_enrichment_hash(product_payload=payload, policy_version=2, profile_name="standard")
    assert key_v1 != key_v2


def test_idempotency_cache_reuses_value():
    cache = EnrichmentIdempotencyCache(ttl_seconds=60)
    key = "abc"
    value, reused = cache.get_or_set(key, lambda: {"result": 1})
    assert reused is False
    assert value == {"result": 1}

    value2, reused2 = cache.get_or_set(key, lambda: {"result": 2})
    assert reused2 is True
    assert value2 == {"result": 1}


def test_execute_with_retry_recovers_from_transient_error():
    state = {"attempts": 0}

    def operation():
        state["attempts"] += 1
        if state["attempts"] < 3:
            raise TimeoutError("temporary")
        return {"ok": True}

    result = execute_with_retry(
        operation=operation,
        classify_error=lambda exc: "timeout" if isinstance(exc, TimeoutError) else "server_error",
        policy=RetryPolicy(max_attempts=3),
    )
    assert result.result == {"ok": True}
    assert result.attempts == 3
    assert result.exhausted is False


def test_execute_with_retry_blocks_non_retryable():
    def operation():
        raise ValueError("bad schema")

    with pytest.raises(RetryExhaustedError) as exc:
        execute_with_retry(
            operation=operation,
            classify_error=lambda _: "schema_error",
            policy=RetryPolicy(max_attempts=3),
        )
    assert "non_retryable" in exc.value.reason_codes
