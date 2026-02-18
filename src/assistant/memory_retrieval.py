"""Scoped memory retrieval service for chat routing/runtime context."""
from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any

from src.models import AssistantMemoryFact

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

