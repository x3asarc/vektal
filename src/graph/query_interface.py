"""
Unified query interface for LLMs to interact with the knowledge graph.

Provides template-based queries for common developer/AI tasks and
natural language fallback for more complex scenarios.

Phase 14 - Codebase Knowledge Graph & Continual Learning
"""

import time
import logging
import re
import json
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from src.graph.query_templates import QUERY_TEMPLATES, execute_template
from src.graph.search_expand_bridge import search_then_expand
from src.graph.semantic_cache import get_semantic_cache
from src.graph.convention_checker import check_against_conventions, load_default_conventions
from src.core.embeddings import generate_embedding
from src.core.synthex_entities import EpisodeType

logger = logging.getLogger(__name__)
_ARCHITECTURE_KEYWORDS = (
    "architecture",
    "architectural",
    "convention",
    "refactor",
    "design",
    "pattern",
    "guardrail",
    "dependency",
    "dependencies",
)


def _runtime_backend_mode() -> str:
    state_path = Path(".graph/runtime-backend.json")
    if not state_path.exists():
        return ""
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
        mode = payload.get("mode", "")
        return mode if isinstance(mode, str) else ""
    except Exception:
        return ""


def _normalize_query_path(path: str) -> str:
    return path.replace("\\", "/")


@dataclass
class QueryResult:
    """Result of a knowledge graph query."""
    success: bool = False
    data: List[Dict[str, Any]] = field(default_factory=list)
    query_type: str = "template"  # "template" or "natural_language"
    template_used: Optional[str] = None
    cypher_generated: Optional[str] = None  # For natural language
    duration_ms: float = 0.0
    error: Optional[str] = None
    source: str = "template"
    discrepancy_flagged: bool = False
    conventions_checked: List[str] = field(default_factory=list)


def _emit_episode(episode_type: EpisodeType, payload: Dict[str, Any]) -> None:
    """Best-effort async episode emission."""
    if os.environ.get("GRAPH_DISABLE_ASYNC_EMIT", "false").lower() == "true":
        return
    disable_on_fallback = os.environ.get("GRAPH_DISABLE_EPISODE_EMIT_ON_FALLBACK", "true").lower() == "true"
    if disable_on_fallback and _runtime_backend_mode() == "local_snapshot":
        return
    try:
        from src.tasks.graphiti_sync import emit_episode
        emit_episode.delay(episode_type.value, "global", payload)
    except Exception as e:
        logger.debug("Episode emission skipped: %s", e)


def _emit_reasoning_trace(result: QueryResult, query: str) -> None:
    if not result.success:
        return
    payload = {
        "query_text": query,
        "template_used": result.template_used,
        "cypher_generated": result.cypher_generated,
        "result_summary": f"rows={len(result.data)} source={result.source}",
        "duration_ms": result.duration_ms,
        "was_cache_hit": result.source == "semantic_cache",
    }
    _emit_episode(EpisodeType.QUERY_REASONING_TRACE, payload)


def _filesystem_fallback_paths(template_name: Optional[str], params: Dict[str, Any], query: str) -> List[str]:
    """
    Return fallback paths when graph returns null but filesystem has evidence.
    """
    path = params.get("file_path")
    if path and Path(path).exists():
        return [path]

    # Coarse fallback: extract explicit path-like token from query and verify it exists.
    token_match = re.search(r'([\w./-]+\.(py|md|json|yml|yaml|ts|tsx|js|jsx))', query)
    if token_match:
        candidate = token_match.group(1)
        if Path(candidate).exists():
            return [candidate]

    return []


def _is_architectural_query(query: str) -> bool:
    lowered = query.lower()
    return any(keyword in lowered for keyword in _ARCHITECTURE_KEYWORDS)


def match_query_to_template(query: str) -> Optional[tuple]:
    """
    Match a natural language query to a pre-built template.
    
    Args:
        query: Natural language query string.
        
    Returns:
        (template_name, params) tuple or None if no match.
    """
    query = query.lower().strip()
    
    # "what imports X" or "X imported by" -> imports template
    if match := re.search(r'what imports ([\w./\\-]+)', query):
        return "imported_by", {"file_path": _normalize_query_path(match.group(1))}
    
    # "what does X depend on" or "X imports" -> imported_by template
    if match := re.search(r'what does ([\w./\\-]+) depend on', query):
        return "imports", {"file_path": _normalize_query_path(match.group(1))}
    
    # "find similar to X" -> similar_files template
    if match := re.search(r'find similar to ([\w./\\-]+)', query):
        return "similar_files", {"file_path": _normalize_query_path(match.group(1)), "limit": 5, "threshold": 0.6}
    
    # "what implements Phase X" -> phase_code template
    if match := re.search(r'what implements phase ([\d.]+)', query):
        return "phase_code", {"phase": match.group(1)}
        
    # "impact radius of X" -> impact_radius template
    if match := re.search(r'impact radius of ([\w./\\-]+)', query):
        return "impact_radius", {"file_path": _normalize_query_path(match.group(1))}
        
    # "callers of function X" -> function_callers template
    if match := re.search(r'callers of function ([\w.]+)', query):
        return "function_callers", {"function_name": match.group(1)}
        
    return None


def query_with_bridge(query_text: str, compact: bool = False) -> QueryResult:
    """
    Run bridge retrieval for unmatched natural-language queries.
    """
    bridge = search_then_expand(query_text, compact=compact)
    data = bridge.initial_nodes + bridge.expanded_nodes
    return QueryResult(
        success=bool(data),
        data=data,
        query_type="natural_language",
        source="bridge",
        error=None if data else "No bridge results found",
    )


def query_graph(query: str, use_natural_language: bool = False, compact: bool = False) -> QueryResult:
    """
    Unified query interface for the codebase knowledge graph.
    
    Args:
        query: The query string (can be natural language or template name).
        use_natural_language: Whether to fallback to LLM-generated Cypher.
        compact: Whether to return compact node representations.
        
    Returns:
        QueryResult with data and metadata.
    """
    start_time = time.time()
    result = QueryResult()
    semantic_cache = get_semantic_cache()
    query_embedding = generate_embedding(query)

    def _finalize() -> QueryResult:
        result.duration_ms = (time.time() - start_time) * 1000
        if _is_architectural_query(query):
            conventions = load_default_conventions(limit=10)
            check_against_conventions(query, conventions=conventions, threshold=0.7)
            result.conventions_checked = [item["rule"] for item in conventions if item.get("rule")]
        
        # If compact mode, results are already serialized in query_with_bridge
        # For templates, we might need to serialize them here
        if compact and result.template_used:
            from src.graph.search_expand_bridge import serialize_node
            result.data = [serialize_node(n, compact=True) for n in result.data]

        if result.success and result.source != "semantic_cache":
            referenced_paths = [item.get("path") for item in result.data if isinstance(item, dict) and item.get("path")]
            semantic_cache.store(
                query_embedding=query_embedding,
                query_text=query,
                result=result.data,
                duration_ms=result.duration_ms,
                referenced_paths=referenced_paths,
            )
        _emit_reasoning_trace(result, query)
        return result

    # 0. Semantic cache lookup before any graph traversal/querying.
    cached = semantic_cache.lookup(query_embedding)
    if cached is not None:
        result.success = True
        result.data = cached.result if isinstance(cached.result, list) else [cached.result]
        result.source = "semantic_cache"
        result.query_type = "template"
        return _finalize()

    # 1. Try direct template match by name
    if query in QUERY_TEMPLATES:
        result.template_used = query
        result.data = execute_template(query, {})
        result.success = True
        if not result.data:
            fallback_paths = _filesystem_fallback_paths(query, {}, query)
            if fallback_paths:
                result.data = [{"path": p} for p in fallback_paths]
                result.source = "filesystem_fallback"
                result.discrepancy_flagged = True
                _emit_episode(
                    EpisodeType.GRAPH_DISCREPANCY,
                    {
                        "query_text": query,
                        "template_used": query,
                        "paths": fallback_paths,
                    },
                )
        return _finalize()
        
    # 2. Try matching natural language to a template
    template_match = match_query_to_template(query)
    if template_match:
        template_name, params = template_match
        result.template_used = template_name
        result.data = execute_template(template_name, params)
        result.success = True
        if not result.data:
            fallback_paths = _filesystem_fallback_paths(template_name, params, query)
            if fallback_paths:
                result.data = [{"path": p} for p in fallback_paths]
                result.source = "filesystem_fallback"
                result.discrepancy_flagged = True
                _emit_episode(
                    EpisodeType.GRAPH_DISCREPANCY,
                    {
                        "query_text": query,
                        "template_used": template_name,
                        "paths": fallback_paths,
                    },
                )
        return _finalize()
        
    # 3. Fallback to bridge retrieval for unmatched natural language queries
    bridge_result = query_with_bridge(query, compact=compact)
    result.success = bridge_result.success
    result.data = bridge_result.data
    result.query_type = bridge_result.query_type
    result.source = bridge_result.source
    result.error = bridge_result.error

    return _finalize()
