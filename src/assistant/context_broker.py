"""Graph-first context broker with reason-coded fallback and token budgets."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
import time
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
_TOKEN_RE = re.compile(r"\S+")


def _default_graph_fetcher(query: str, top_k: int) -> list[str]:
    """Default graph fetcher using Neo4j/Graphiti knowledge graph.

    This is the PRIMARY context source for all operations.
    Falls back gracefully if graph is unavailable.

    Uses Graphiti's semantic search directly for natural language queries.
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        import asyncio
        from src.core.graphiti_client import get_graphiti_client

        client = get_graphiti_client()
        if not client:
            # Graph not enabled or unavailable - fallback will handle
            logger.debug("Graph client not available")
            return []

        # Run async search in sync context
        async def _async_search():
            return await client.search(query=query, num_results=min(top_k, 10))

        # Check if we're already in an async context
        try:
            loop = asyncio.get_running_loop()
            # Already in async context - can't use asyncio.run()
            # Return empty to fallback
            logger.debug("Already in async context, cannot use asyncio.run()")
            return []
        except RuntimeError:
            # Not in async context - safe to use asyncio.run()
            logger.debug(f"Running graph search for query: {query}")
            search_results = asyncio.run(_async_search())
            logger.debug(f"Graph search returned {len(search_results) if search_results else 0} results")

        if not search_results:
            logger.debug("Graph search returned empty results")
            return []

        # Format results as context snippets
        snippets = []
        for result in search_results[:top_k]:
            # Graphiti returns Entity nodes with name and summary
            if hasattr(result, 'name') and hasattr(result, 'summary'):
                snippet = f"[{result.name}] {result.summary[:200]}"
                snippets.append(snippet)
                logger.debug(f"Added snippet from Entity: {result.name}")
            elif isinstance(result, dict):
                name = result.get('name', '')
                summary = result.get('summary', '')
                if name:
                    snippet = f"[{name}] {summary[:200]}"
                    snippets.append(snippet)
                    logger.debug(f"Added snippet from dict: {name}")

        logger.debug(f"Returning {len(snippets)} snippets from graph")
        return snippets

    except Exception as e:
        # Graph unavailable - fallback will handle this
        # Log the error for debugging but don't crash
        logger.warning(f"Graph fetch failed: {e}", exc_info=True)
        return []


def get_context(query: str, *, top_k: int = 10, max_tokens: int = 2500) -> ContextBundle:
    """Convenience function to get context using the default graph-first approach.

    This is the recommended way to retrieve context in any Python code.
    Always uses Neo4j/Graphiti knowledge graph as primary source.

    Args:
        query: Natural language query or file path to search for
        top_k: Maximum number of results to return
        max_tokens: Target token budget for context

    Returns:
        ContextBundle with snippets, provenance, and telemetry

    Example:
        >>> from src.assistant.context_broker import get_context
        >>> bundle = get_context("files that import embeddings")
        >>> print(bundle.output_text)
        >>> print(f"Source: {bundle.telemetry['graph_used']}")
    """
    return assemble_context(query=query, top_k=top_k, target_tokens=max_tokens)


class FallbackReason(str, Enum):
    GRAPH_EMPTY = "graph_empty"
    GRAPH_ERROR = "graph_error"
    SNAPSHOT_EMPTY = "snapshot_empty"
    DOCS_USED = "docs_used"
    BASELINE_USED = "baseline_used"
    TOKEN_COMPACTION = "token_compaction"


@dataclass(frozen=True)
class ContextBundle:
    query: str
    query_class: str
    snippets: list[str]
    output_text: str
    telemetry: dict[str, object]
    provenance: list[dict[str, str]]


def _estimate_tokens(text: str) -> int:
    # Lightweight estimation for gating; exact tokenizer not required for guardrail.
    words = len(_TOKEN_RE.findall(text))
    return int(words * 1.3) + 1


def _classify_query(query: str) -> str:
    lowered = query.lower()
    if any(token in lowered for token in ["trigger", "depends", "calls", "flow", "relationship"]):
        return "relational"
    if any(token in lowered for token in ["how", "steps", "procedure", "run", "execute"]):
        return "procedural"
    if any(token in lowered for token in ["status", "health", "state", "current", "latest"]):
        return "status"
    return "factual"


def _read_doc_fallback_snippets(query: str, *, limit: int = 6) -> tuple[list[str], list[dict[str, str]]]:
    tokens = {token.lower() for token in _TOKEN_RE.findall(query) if len(token) >= 3}
    candidates = [
        REPO_ROOT / "docs" / "AGENT_START_HERE.md",
        REPO_ROOT / "docs" / "FOLDER_SUMMARIES.md",
        REPO_ROOT / "docs" / "CONTEXT_LINK_MAP.md",
    ]
    snippets: list[str] = []
    provenance: list[dict[str, str]] = []
    for path in candidates:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if tokens and not any(token in stripped.lower() for token in tokens):
                continue
            snippets.append(stripped)
            provenance.append({"source": "docs", "path": path.relative_to(REPO_ROOT).as_posix()})
            if len(snippets) >= limit:
                return snippets, provenance
    return snippets, provenance


def assemble_context(
    *,
    query: str,
    graph_fetcher: Callable[[str, int], list[str]] | None = None,
    snapshot_fetcher: Callable[[str, int], list[str]] | None = None,
    docs_limit: int = 6,
    top_k: int = 10,
    target_tokens: int = 2500,
    hard_cap_tokens: int = 4000,
) -> ContextBundle:
    """Assemble context with mandatory graph attempt and structured fallbacks.

    By default, uses Neo4j/Graphiti knowledge graph as primary context source.
    Pass explicit graph_fetcher=None to disable graph queries.
    """

    started = time.perf_counter()
    query_class = _classify_query(query)
    snippets: list[str] = []
    provenance: list[dict[str, str]] = []
    fallback_used = False
    fallback_reason: FallbackReason | None = None
    graph_used = False

    # Use default graph fetcher if none provided
    effective_graph_fetcher = graph_fetcher if graph_fetcher is not None else _default_graph_fetcher

    graph_attempted = True
    try:
        graph_results = effective_graph_fetcher(query, top_k)
        if graph_results:
            snippets.extend([item for item in graph_results if isinstance(item, str) and item.strip()])
            provenance.extend([{"source": "graph", "path": "graph://query"} for _ in snippets])
            graph_used = True
        else:
            fallback_used = True
            fallback_reason = FallbackReason.GRAPH_EMPTY
    except Exception:
        fallback_used = True
        fallback_reason = FallbackReason.GRAPH_ERROR

    if fallback_used and not snippets:
        try:
            snapshot_results = (snapshot_fetcher or (lambda _query, _k: []))(query, top_k)
        except Exception:
            snapshot_results = []
        valid_snapshot = [item for item in snapshot_results if isinstance(item, str) and item.strip()]
        if valid_snapshot:
            snippets.extend(valid_snapshot)
            provenance.extend([{"source": "snapshot", "path": "snapshot://local"} for _ in valid_snapshot])
            if fallback_reason is None:
                fallback_reason = FallbackReason.SNAPSHOT_EMPTY

    if not snippets:
        doc_snippets, doc_provenance = _read_doc_fallback_snippets(query, limit=docs_limit)
        if doc_snippets:
            snippets.extend(doc_snippets)
            provenance.extend(doc_provenance)
            fallback_used = True
            fallback_reason = FallbackReason.DOCS_USED

    if not snippets:
        baseline = [
            "No high-confidence context found in graph or docs.",
            "Fallback baseline response used to keep flow non-blocking.",
        ]
        snippets.extend(baseline)
        provenance.extend([{"source": "baseline", "path": "baseline://default"} for _ in baseline])
        fallback_used = True
        fallback_reason = FallbackReason.BASELINE_USED

    token_count = sum(_estimate_tokens(item) for item in snippets)
    compaction_applied = False
    while snippets and token_count > hard_cap_tokens:
        snippets.pop()
        if provenance:
            provenance.pop()
        token_count = sum(_estimate_tokens(item) for item in snippets)
        compaction_applied = True
        fallback_reason = FallbackReason.TOKEN_COMPACTION

    output_text = "\n".join(snippets)
    telemetry = {
        "graph_attempted": graph_attempted,
        "graph_used": graph_used,
        "fallback_used": fallback_used,
        "fallback_reason": fallback_reason.value if fallback_reason else None,
        "latency_ms": round((time.perf_counter() - started) * 1000, 3),
        "assembled_tokens": token_count,
        "query_class": query_class,
        "target_tokens": target_tokens,
        "hard_cap_tokens": hard_cap_tokens,
        "compaction_applied": compaction_applied,
    }
    return ContextBundle(
        query=query,
        query_class=query_class,
        snippets=snippets,
        output_text=output_text,
        telemetry=telemetry,
        provenance=provenance,
    )

