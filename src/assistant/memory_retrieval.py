"""Scoped memory retrieval service for chat routing/runtime context."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
import re
from typing import Any, List, Literal

from src.models import AssistantMemoryFact

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[a-z0-9]{3,}", re.IGNORECASE)


def _tokens(value: str) -> set[str]:
    return {token.lower() for token in _TOKEN_RE.findall(value or "")}


def _relevance_score(*, query_tokens: set[str], fact: AssistantMemoryFact) -> float:
    if not query_tokens:
        return 0.0
    key_tokens = _tokens(fact.fact_key or "")
    text_tokens = _tokens(fact.fact_value_text or "")
    overlap_key = len(query_tokens & key_tokens)
    overlap_text = len(query_tokens & text_tokens)
    trust = float(fact.trust_score or 0.0)
    return (overlap_key * 2.0) + (overlap_text * 1.0) + trust


def retrieve_memory_facts(
    *,
    store_id: int,
    user_id: int,
    query: str,
    top_k: int = 5,
    scope: str = "team",
) -> list[dict[str, Any]]:
    """Retrieve memory facts with tenant/user scope filtering and provenance."""
    now = datetime.now(timezone.utc)
    limit = min(max(int(top_k), 1), 20)
    query_tokens = _tokens(query)

    rows = (
        AssistantMemoryFact.query.filter(
            AssistantMemoryFact.store_id == store_id,
            AssistantMemoryFact.is_active.is_(True),
            (AssistantMemoryFact.expires_at.is_(None) | (AssistantMemoryFact.expires_at > now)),
        )
        .order_by(AssistantMemoryFact.updated_at.desc())
        .all()
    )

    if scope == "user":
        rows = [row for row in rows if row.user_id in {None, user_id}]

    scored: list[tuple[float, AssistantMemoryFact]] = []
    for row in rows:
        score = _relevance_score(query_tokens=query_tokens, fact=row)
        if score <= 0.0:
            continue
        scored.append((score, row))

    scored.sort(key=lambda item: (item[0], item[1].trust_score or 0.0, item[1].updated_at), reverse=True)
    selected = scored[:limit]
    output: list[dict[str, Any]] = []
    for score, row in selected:
        output.append(
            {
                "fact_id": row.id,
                "fact_key": row.fact_key,
                "fact_value_text": row.fact_value_text,
                "source": row.source,
                "trust_score": float(row.trust_score or 0.0),
                "relevance_score": score,
                "provenance": row.provenance_json or {},
                "expires_at": row.expires_at.isoformat() if row.expires_at else None,
            }
        )
    return output


# ===========================================
# Enhanced Memory Retrieval (Phase 13.2)
# ===========================================

@dataclass
class MemoryResult:
    """
    Memory retrieval result with relevance scoring.

    Supports both database facts and graph-derived memories.
    """
    content: str
    relevance_score: float
    source: str  # 'facts', 'graph', 'lexical'
    metadata: dict


RetrievalMode = Literal['vector', 'lexical', 'blend']


def retrieve_relevant_memories(
    query: str,
    store_id: str,
    limit: int = 10,
    include_graph: bool = True,
    retrieval_mode: RetrievalMode = 'blend'
) -> List[MemoryResult]:
    """
    Retrieve relevant memories with vector + lexical blend scoring.

    Supports three retrieval modes:
    - 'vector': Embedding similarity only
    - 'lexical': Keyword matching only (fallback when vector unavailable)
    - 'blend': Combine vector + lexical with weighted scoring (default)

    Args:
        query: Search query text
        store_id: Store ID for multi-tenant filtering
        limit: Maximum results to return (default 10)
        include_graph: Whether to include graph-backed memories (default True)
        retrieval_mode: Retrieval strategy ('vector', 'lexical', 'blend')

    Returns:
        List of MemoryResult objects sorted by relevance

    Example:
        >>> memories = retrieve_relevant_memories(
        ...     query="product enrichment quality",
        ...     store_id="store_123",
        ...     limit=5,
        ...     retrieval_mode='blend'
        ... )
    """
    results: List[MemoryResult] = []

    # Convert store_id to int if needed for database query
    try:
        store_id_int = int(store_id) if isinstance(store_id, str) else store_id
    except (ValueError, TypeError):
        logger.warning(f"Invalid store_id format: {store_id}")
        return []

    if retrieval_mode == 'vector':
        # Vector-only retrieval
        results = _vector_search(query, store_id_int, limit * 2)
        if not results:
            logger.warning("Vector search failed - falling back to lexical")
            results = _lexical_search(query, store_id_int, limit * 2)

    elif retrieval_mode == 'lexical':
        # Lexical-only retrieval
        results = _lexical_search(query, store_id_int, limit * 2)

    else:  # blend mode (default)
        # Get both vector and lexical results
        vector_results = _vector_search(query, store_id_int, limit * 2)
        lexical_results = _lexical_search(query, store_id_int, limit * 2)

        if not vector_results:
            # Vector search failed - use lexical only
            logger.warning("Vector search unavailable - using lexical fallback")
            results = lexical_results
        else:
            # Merge and re-rank with combined scores
            results = _blend_results(vector_results, lexical_results)

    # Add graph evidence if enabled
    if include_graph:
        try:
            graph_results = _query_graph_memories(query, store_id, limit)
            results.extend(graph_results)
        except Exception as e:
            logger.warning(f"Graph memory query failed: {e}")
            # Continue without graph results (fail-open)

    # Sort by relevance and limit
    results.sort(key=lambda r: r.relevance_score, reverse=True)
    return results[:limit]


def _vector_search(query: str, store_id: int, limit: int) -> List[MemoryResult]:
    """
    Perform vector similarity search using embeddings.

    Returns empty list on failure (fail-open).
    """
    try:
        # Placeholder for actual vector search implementation
        # Would use sentence-transformers embeddings from AssistantMemoryFact
        # For now, return empty to indicate vector search not yet implemented
        logger.debug("Vector search not yet implemented - will be added in future update")
        return []

    except Exception as e:
        logger.warning(f"Vector search failed: {e}")
        return []


def _lexical_search(query: str, store_id: int, limit: int) -> List[MemoryResult]:
    """
    Perform lexical keyword matching search.

    This is the fallback when vector search is unavailable.
    """
    try:
        query_tokens = _tokens(query)
        if not query_tokens:
            return []

        now = datetime.now(timezone.utc)
        rows = (
            AssistantMemoryFact.query.filter(
                AssistantMemoryFact.store_id == store_id,
                AssistantMemoryFact.is_active.is_(True),
                (AssistantMemoryFact.expires_at.is_(None) | (AssistantMemoryFact.expires_at > now)),
            )
            .order_by(AssistantMemoryFact.updated_at.desc())
            .all()
        )

        scored: List[tuple[float, AssistantMemoryFact]] = []
        for row in rows:
            score = _relevance_score(query_tokens=query_tokens, fact=row)
            if score > 0.0:
                scored.append((score, row))

        scored.sort(key=lambda x: x[0], reverse=True)

        results: List[MemoryResult] = []
        for score, row in scored[:limit]:
            results.append(MemoryResult(
                content=row.fact_value_text or row.fact_key or "",
                relevance_score=score,
                source='lexical',
                metadata={
                    'fact_id': row.id,
                    'fact_key': row.fact_key,
                    'trust_score': float(row.trust_score or 0.0),
                    'provenance': row.provenance_json or {},
                }
            ))

        return results

    except Exception as e:
        logger.warning(f"Lexical search failed: {e}")
        return []


def _blend_results(
    vector_results: List[MemoryResult],
    lexical_results: List[MemoryResult]
) -> List[MemoryResult]:
    """
    Blend vector and lexical results with weighted scoring.

    Combined score = 0.7 * vector_score + 0.3 * lexical_score
    """
    # Normalize scores to 0-1 range
    if vector_results:
        max_vector = max(r.relevance_score for r in vector_results)
        if max_vector > 0:
            for r in vector_results:
                r.relevance_score = r.relevance_score / max_vector

    if lexical_results:
        max_lexical = max(r.relevance_score for r in lexical_results)
        if max_lexical > 0:
            for r in lexical_results:
                r.relevance_score = r.relevance_score / max_lexical

    # Build combined result set with blended scores
    result_map: dict[str, MemoryResult] = {}

    # Add vector results (weight 0.7)
    for r in vector_results:
        key = r.content[:100]  # Simple dedup key
        result_map[key] = MemoryResult(
            content=r.content,
            relevance_score=r.relevance_score * 0.7,
            source='vector',
            metadata=r.metadata
        )

    # Merge lexical results (weight 0.3)
    for r in lexical_results:
        key = r.content[:100]
        if key in result_map:
            # Update score with lexical component
            result_map[key].relevance_score += r.relevance_score * 0.3
        else:
            # Add as lexical-only result
            result_map[key] = MemoryResult(
                content=r.content,
                relevance_score=r.relevance_score * 0.3,
                source='lexical',
                metadata=r.metadata
            )

    return list(result_map.values())


def _query_graph_memories(query: str, store_id: str, limit: int) -> List[MemoryResult]:
    """
    Query graph for relevant episode memories.

    Returns empty list on error (fail-open).
    """
    try:
        # Lazy import to avoid circular dependency
        from src.assistant.governance.graph_oracle_adapter import query_graph_evidence

        # Query graph for relevant evidence
        # Note: This is a placeholder - actual implementation would query
        # graph episodes directly rather than using oracle adapter
        logger.debug(f"Graph memory query for: {query}")

        # Placeholder - would query Graphiti for relevant episodes
        return []

    except ImportError:
        logger.debug("Graph oracle adapter not available")
        return []
    except Exception as e:
        logger.warning(f"Graph memory query failed: {e}")
        return []

