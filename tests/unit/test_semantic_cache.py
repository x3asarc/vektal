"""
Unit tests for semantic cache behavior.
"""

import time

from src.graph.semantic_cache import SemanticCache, CacheConfig


def test_cache_threshold_behavior():
    cache = SemanticCache(CacheConfig(similarity_threshold=0.92, max_entries=10, ttl_seconds=3600))
    cache.store([1.0, 0.0], "q1", [{"path": "a.py"}], 10.0, ["a.py"])

    hit = cache.lookup([0.93, 0.3675])
    miss = cache.lookup([0.91, 0.4146])

    assert hit is not None
    assert hit.query_text == "q1"
    assert miss is None


def test_cache_ttl_eviction():
    cache = SemanticCache(CacheConfig(similarity_threshold=0.92, max_entries=10, ttl_seconds=0))
    cache.store([1.0, 0.0], "q1", [{"path": "a.py"}], 10.0, ["a.py"])
    time.sleep(0.01)
    assert cache.lookup([1.0, 0.0]) is None


def test_cache_invalidation_by_file_path():
    cache = SemanticCache(CacheConfig(similarity_threshold=0.92, max_entries=10, ttl_seconds=3600))
    cache.store([1.0, 0.0], "q1", [{"path": "a.py"}], 10.0, ["a.py"])
    cache.store([0.0, 1.0], "q2", [{"path": "b.py"}], 10.0, ["b.py"])

    removed = cache.invalidate(["a.py"])
    stats = cache.get_cache_stats()

    assert removed == 1
    assert stats["entries"] == 1
