"""
Semantic cache for near-identical knowledge graph queries.
"""

import time
from dataclasses import dataclass, field
from collections import OrderedDict
from typing import Any, Dict, List, Optional

import numpy as np


@dataclass
class CacheConfig:
    similarity_threshold: float = 0.92
    max_entries: int = 1000
    ttl_seconds: int = 3600


@dataclass
class CachedResult:
    embedding: np.ndarray
    query_text: str
    result: Any
    timestamp: float
    duration_ms: float
    referenced_paths: List[str] = field(default_factory=list)


class SemanticCache:
    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or CacheConfig()
        self._entries: "OrderedDict[str, CachedResult]" = OrderedDict()
        self._hit_count = 0
        self._miss_count = 0
        self._hit_latency_ms_total = 0.0
        self._miss_latency_ms_total = 0.0

    @staticmethod
    def _normalize(vec: List[float]) -> Optional[np.ndarray]:
        if not vec:
            return None
        arr = np.array(vec, dtype=np.float32)
        norm = np.linalg.norm(arr)
        if norm == 0.0:
            return None
        return arr / norm

    def _evict_expired(self) -> None:
        now = time.time()
        expired = [k for k, entry in self._entries.items() if now - entry.timestamp > self.config.ttl_seconds]
        for key in expired:
            self._entries.pop(key, None)

    def lookup(self, query_embedding: List[float]) -> Optional[CachedResult]:
        start = time.time()
        self._evict_expired()
        normalized_query = self._normalize(query_embedding)
        if normalized_query is None:
            self._miss_count += 1
            self._miss_latency_ms_total += (time.time() - start) * 1000
            return None

        best_key = None
        best_score = -1.0
        for key, entry in self._entries.items():
            score = float(np.dot(normalized_query, entry.embedding))
            if score > best_score:
                best_score = score
                best_key = key

        if best_key is None or best_score < self.config.similarity_threshold:
            self._miss_count += 1
            self._miss_latency_ms_total += (time.time() - start) * 1000
            return None

        self._entries.move_to_end(best_key)
        self._hit_count += 1
        self._hit_latency_ms_total += (time.time() - start) * 1000
        return self._entries[best_key]

    def store(
        self,
        query_embedding: List[float],
        query_text: str,
        result: Any,
        duration_ms: float,
        referenced_paths: Optional[List[str]] = None,
    ) -> bool:
        normalized_query = self._normalize(query_embedding)
        if normalized_query is None:
            return False

        key = f"{int(time.time() * 1000)}:{len(self._entries)}"
        self._entries[key] = CachedResult(
            embedding=normalized_query,
            query_text=query_text,
            result=result,
            timestamp=time.time(),
            duration_ms=duration_ms,
            referenced_paths=referenced_paths or [],
        )
        self._entries.move_to_end(key)

        while len(self._entries) > self.config.max_entries:
            self._entries.popitem(last=False)
        return True

    def invalidate(self, file_paths: List[str]) -> int:
        if not file_paths:
            return 0
        paths = set(file_paths)
        removed = 0
        keys_to_remove = []
        for key, entry in self._entries.items():
            if any(path in paths for path in entry.referenced_paths):
                keys_to_remove.append(key)
        for key in keys_to_remove:
            self._entries.pop(key, None)
            removed += 1
        return removed

    def get_cache_stats(self) -> Dict[str, Any]:
        hits = self._hit_count
        misses = self._miss_count
        total = hits + misses
        return {
            "entries": len(self._entries),
            "hit_count": hits,
            "miss_count": misses,
            "hit_rate": (hits / total) if total else 0.0,
            "avg_hit_latency_ms": (self._hit_latency_ms_total / hits) if hits else 0.0,
            "avg_miss_latency_ms": (self._miss_latency_ms_total / misses) if misses else 0.0,
        }


_SEMANTIC_CACHE: Optional[SemanticCache] = None


def get_semantic_cache() -> SemanticCache:
    global _SEMANTIC_CACHE
    if _SEMANTIC_CACHE is None:
        _SEMANTIC_CACHE = SemanticCache()
    return _SEMANTIC_CACHE
