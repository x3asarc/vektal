"""
Search-then-expand retrieval bridge for hybrid graph/vector context.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import math
import re
from datetime import datetime, timezone

from src.core.embeddings import generate_embedding, similarity_search
from src.core.graphiti_client import get_graphiti_client
from src.graph.query_templates import execute_template

EDGE_SCORE_MULTIPLIER = {
    "IMPLEMENTS": 1.3,  # Strong: actual implementation
    "CALLS": 1.1,  # Medium: direct function call
    "IMPORTS": 0.9,  # Medium-weak: dependency
    "REFERENCES": 0.7,  # Weak: documentation mention
    "EXPLAINS": 1.0,  # Neutral: planning doc link
    "DEPENDS_ON": 0.9,  # Similar to IMPORTS
    "CONTAINS": 1.0,  # Structural: module contains class
}


def apply_temporal_decay(score: float, created_at: Any) -> float:
    """Apply temporal decay to score. Nodes >6 months score 0.6x base."""
    if not created_at:
        return score

    try:
        if isinstance(created_at, str):
            created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        elif isinstance(created_at, (int, float)):
            created = datetime.fromtimestamp(created_at, tz=timezone.utc)
        else:
            created = created_at

        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)

        age_days = (datetime.now(timezone.utc) - created).days

        # Exponential decay: exp(-0.003 * age_days)
        # 180 days (6 months) -> ~0.58 multiplier
        decay_factor = math.exp(-0.003 * age_days)

        # Floor at 0.5 (50% of base score)
        return score * max(decay_factor, 0.5)

    except (ValueError, TypeError):
        return score


def score_node(
    base_score: float,
    edge_type: Optional[str] = None,
    created_at: Any = None,
) -> float:
    """Apply edge-type multiplier + temporal decay."""
    score = base_score
    if edge_type:
        score *= EDGE_SCORE_MULTIPLIER.get(edge_type.upper(), 1.0)

    if created_at:
        score = apply_temporal_decay(score, created_at)

    return score


@dataclass
class BridgeConfig:
    max_initial_nodes: int = 5
    max_traversal_depth: int = 2
    max_context_tokens: int = 8192
    expand_relationships: List[str] = field(
        default_factory=lambda: ["IMPORTS", "CALLS", "IMPLEMENTS", "EXPLAINS"]
    )
    compact: bool = False


@dataclass
class BridgeResult:
    initial_nodes: List[Dict[str, Any]] = field(default_factory=list)
    expanded_nodes: List[Dict[str, Any]] = field(default_factory=list)
    total_tokens_estimated: int = 0
    truncated: bool = False
    relationships_followed: List[str] = field(default_factory=list)


def _generate_summary(node: Dict[str, Any]) -> str:
    """Generate compact summary for node."""
    desc = node.get("description") or node.get("purpose", "")
    if len(desc) > 100:
        return desc[:97] + "..."
    return desc


def serialize_node(node: Dict[str, Any], compact: bool = False) -> Dict[str, Any]:
    """Serialize graph node. Compact mode strips verbose fields."""
    if compact:
        return {
            "path": node.get("path") or node.get("name"),
            "type": node.get("entity_type") or node.get("type"),
            "summary": _generate_summary(node),
        }
    return node


def _extract_path_candidates(query_text: str) -> List[str]:
    candidates: List[str] = []
    for match in re.finditer(r"([\w./-]+\.(py|md|json|yaml|yml|ts|tsx|js|jsx))", query_text):
        candidate = match.group(1)
        if Path(candidate).exists():
            candidates.append(candidate)
    return candidates


def _estimate_node_tokens(node: Dict[str, Any], compact: bool = False) -> int:
    if compact:
        return 30
    path = str(node.get("path", ""))
    purpose = str(node.get("purpose", ""))
    return max(20, len(path) // 2 + len(purpose) // 4 + 20)


def _seed_initial_nodes(query_text: str, query_embedding: List[float], config: BridgeConfig) -> List[Dict[str, Any]]:
    client = get_graphiti_client()
    nodes = similarity_search(client, query_embedding, top_k=config.max_initial_nodes, min_score=0.0)
    nodes = nodes[: config.max_initial_nodes]

    if nodes:
        # Apply temporal decay to initial nodes
        for node in nodes:
            node["score"] = score_node(node.get("score", 1.0), created_at=node.get("created_at"))
        return sorted(nodes, key=lambda n: n.get("score", 0.0), reverse=True)

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
    anchor_score = node.get("score", 1.0)

    if "IMPORTS" in config.expand_relationships:
        rels_followed.append("IMPORTS")
        # Template queries might not return score/edge_type, we assign them
        for item in execute_template("imports", {"file_path": path}):
            item["score"] = score_node(anchor_score, edge_type="IMPORTS", created_at=item.get("created_at"))
            expanded.append(item)
        for item in execute_template("imported_by", {"file_path": path}):
            item["score"] = score_node(anchor_score, edge_type="IMPORTS", created_at=item.get("created_at"))
            expanded.append(item)

    if "CALLS" in config.expand_relationships:
        rels_followed.append("CALLS")
        # Placeholder for future expansion
        expanded.extend([])

    node["_relationships_followed"] = rels_followed
    return expanded


def search_then_expand(
    query_text: str,
    query_embedding: Optional[List[float]] = None,
    config: Optional[BridgeConfig] = None,
    compact: bool = False,
) -> BridgeResult:
    config = config or BridgeConfig(compact=compact)
    # Ensure config respects passed compact flag
    if compact:
        config.compact = True
        
    query_embedding = query_embedding or generate_embedding(query_text)

    initial_nodes = _seed_initial_nodes(query_text, query_embedding, config)
    initial_nodes = initial_nodes[: config.max_initial_nodes]

    seen_paths = {n.get("path") for n in initial_nodes if n.get("path")}
    
    # Serialize initial nodes if compact
    if config.compact:
        initial_nodes = [serialize_node(n, compact=True) for n in initial_nodes]

    expanded_nodes: List[Dict[str, Any]] = []
    relationships_followed: List[str] = []

    total_tokens = 0
    for node in initial_nodes:
        total_tokens += _estimate_node_tokens(node, compact=config.compact)
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
            candidate_tokens = _estimate_node_tokens(candidate, compact=config.compact)
            if total_tokens + candidate_tokens > config.max_context_tokens:
                truncated = True
                break
            total_tokens += candidate_tokens
            
            # Serialize if compact
            final_node = serialize_node(candidate, compact=config.compact)
            expanded_nodes.append(final_node)
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
