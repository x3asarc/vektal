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
    """Default graph fetcher using Neo4j knowledge graph.

    This is the PRIMARY context source for all operations.
    Falls back gracefully if graph is unavailable.

    Uses direct Neo4j queries against the existing graph schema.
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        from neo4j import GraphDatabase
        import os

        uri = os.getenv('NEO4J_URI')
        user = os.getenv('NEO4J_USER', 'neo4j')
        password = os.getenv('NEO4J_PASSWORD')

        if not password:
            logger.debug("Neo4j password not set")
            return []

        logger.debug(f"Querying graph for: {query}")

        # Extract meaningful keywords from query (words longer than 3 chars)
        import re
        words = [w for w in re.findall(r'\w+', query) if len(w) > 3]
        if not words:
            logger.debug("No meaningful keywords in query")
            return []

        # Use the most specific term (usually the longest word)
        search_term = max(words, key=len)
        logger.debug(f"Using search term: {search_term}")

        driver = GraphDatabase.driver(uri, auth=(user, password), connection_timeout=5.0)

        # Simple text search across File nodes using the key term
        cypher = """
        MATCH (f:File)
        WHERE f.path IS NOT NULL AND f.summary IS NOT NULL
        AND (toLower(f.path) CONTAINS toLower($search_text)
             OR toLower(f.summary) CONTAINS toLower($search_text))
        RETURN f.path AS path, f.summary AS summary
        LIMIT $limit
        """

        with driver.session() as session:
            result = session.run(cypher, search_text=search_term, limit=top_k)
            records = list(result)

        driver.close()

        if not records:
            logger.debug("No graph results found")
            return []

        # Format as context snippets
        snippets = []
        for record in records:
            path = record.get("path", "")
            summary = record.get("summary", "")
            if path:
                snippets.append(f"[{path}] {summary[:200]}")

        logger.debug(f"Returning {len(snippets)} snippets from graph")
        return snippets

    except Exception as e:
        # Graph unavailable - fallback will handle this
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
        import logging
        logging.debug(f"assemble_context: Calling graph fetcher with query='{query}', top_k={top_k}")
        graph_results = effective_graph_fetcher(query, top_k)
        logging.debug(f"assemble_context: Got {len(graph_results) if graph_results else 0} results")
        if graph_results:
            snippets.extend([item for item in graph_results if isinstance(item, str) and item.strip()])
            provenance.extend([{"source": "graph", "path": "graph://query"} for _ in snippets])
            graph_used = True
        else:
            fallback_used = True
            fallback_reason = FallbackReason.GRAPH_EMPTY
    except Exception as e:
        import logging
        logging.error(f"assemble_context: Exception during graph fetch: {e}", exc_info=True)
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

