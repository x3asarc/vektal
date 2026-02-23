"""
Search-then-expand retrieval bridge for hybrid graph/vector context.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import re

from src.core.embeddings import generate_embedding, similarity_search
from src.core.graphiti_client import get_graphiti_client
from src.graph.query_templates import execute_template


@dataclass
class BridgeConfig:
    max_initial_nodes: int = 5
    max_traversal_depth: int = 2
    max_context_tokens: int = 8192
    expand_relationships: List[str] = field(
        default_factory=lambda: ["IMPORTS", "CALLS", "IMPLEMENTS", "EXPLAINS"]
    )


@dataclass
class BridgeResult:
    initial_nodes: List[Dict[str, Any]] = field(default_factory=list)
    expanded_nodes: List[Dict[str, Any]] = field(default_factory=list)
    total_tokens_estimated: int = 0
    truncated: bool = False
    relationships_followed: List[str] = field(default_factory=list)


def _extract_path_candidates(query_text: str) -> List[str]:
    candidates: List[str] = []
    for match in re.finditer(r"([\w./-]+\.(py|md|json|yaml|yml|ts|tsx|js|jsx))", query_text):
        candidate = match.group(1)
        if Path(candidate).exists():
            candidates.append(candidate)
    return candidates


def _estimate_node_tokens(node: Dict[str, Any]) -> int:
    path = str(node.get("path", ""))
    purpose = str(node.get("purpose", ""))
    return max(20, len(path) // 2 + len(purpose) // 4 + 20)


def _seed_initial_nodes(query_text: str, query_embedding: List[float], config: BridgeConfig) -> List[Dict[str, Any]]:
    client = get_graphiti_client()
    nodes = similarity_search(client, query_embedding, top_k=config.max_initial_nodes, min_score=0.0)
    nodes = nodes[: config.max_initial_nodes]

    if nodes:
        return nodes

    # Fallback when graph/vector is unavailable.
    return [{"path": p, "entity_type": "File", "score": 1.0} for p in _extract_path_candidates(query_text)][
        : config.max_initial_nodes
    ]


def _expand_from_node(node: Dict[str, Any], config: BridgeConfig) -> List[Dict[str, Any]]:
    path = node.get("path")
    if not path:
        return []

    expanded: List[Dict[str, Any]] = []
    rels_followed: List[str] = []

    if "IMPORTS" in config.expand_relationships:
        rels_followed.append("IMPORTS")
        expanded.extend(execute_template("imports", {"file_path": path}))
        expanded.extend(execute_template("imported_by", {"file_path": path}))

    if "CALLS" in config.expand_relationships:
        rels_followed.append("CALLS")
        # If query template expands function caller info, bridge can include it when available.
        expanded.extend([])

    node["_relationships_followed"] = rels_followed
    return expanded


def search_then_expand(
    query_text: str,
    query_embedding: Optional[List[float]] = None,
    config: Optional[BridgeConfig] = None,
) -> BridgeResult:
    config = config or BridgeConfig()
    query_embedding = query_embedding or generate_embedding(query_text)

    initial_nodes = _seed_initial_nodes(query_text, query_embedding, config)
    initial_nodes = initial_nodes[: config.max_initial_nodes]

    seen_paths = {n.get("path") for n in initial_nodes if n.get("path")}
    expanded_nodes: List[Dict[str, Any]] = []
    relationships_followed: List[str] = []

    total_tokens = 0
    for node in initial_nodes:
        total_tokens += _estimate_node_tokens(node)
    truncated = total_tokens > config.max_context_tokens
    if truncated:
        return BridgeResult(
            initial_nodes=initial_nodes,
            expanded_nodes=[],
            total_tokens_estimated=total_tokens,
            truncated=True,
            relationships_followed=[],
        )

    for node in initial_nodes:
        if len(relationships_followed) == 0:
            relationships_followed.extend(node.get("_relationships_followed", []))

        additions = _expand_from_node(node, config)
        for candidate in additions:
            candidate_path = candidate.get("path")
            if candidate_path and candidate_path in seen_paths:
                continue
            candidate_tokens = _estimate_node_tokens(candidate)
            if total_tokens + candidate_tokens > config.max_context_tokens:
                truncated = True
                break
            total_tokens += candidate_tokens
            expanded_nodes.append(candidate)
            if candidate_path:
                seen_paths.add(candidate_path)

        if truncated:
            break

    return BridgeResult(
        initial_nodes=initial_nodes,
        expanded_nodes=expanded_nodes,
        total_tokens_estimated=total_tokens,
        truncated=truncated,
        relationships_followed=list(dict.fromkeys(relationships_followed or config.expand_relationships)),
    )
