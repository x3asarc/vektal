"""
Core utilities and infrastructure for Shopify Multi-Supplier Platform.

Exports:
- Graphiti client singleton and graph utilities (Phase 13.2)
- Entity and edge type contracts for temporal knowledge graph (Phase 13.2)
"""

from src.core.graphiti_client import (
    get_graphiti_client,
    check_graph_availability,
    query_with_fallback
)

from src.core.synthex_entities import (
    EpisodeType,
    BaseEntity,
    OracleDecisionEntity,
    FailurePatternEntity,
    ModuleEntity,
    EnrichmentOutcomeEntity,
    UserApprovalEntity,
    BaseEdge,
    WasVerifiedByEdge,
    HasFailureWarningEdge,
    YieldedOutcomeEdge,
    ApprovedByUserEdge,
    create_episode_payload
)

__all__ = [
    # Graphiti client
    'get_graphiti_client',
    'check_graph_availability',
    'query_with_fallback',
    # Episode taxonomy
    'EpisodeType',
    'create_episode_payload',
    # Entity families
    'BaseEntity',
    'OracleDecisionEntity',
    'FailurePatternEntity',
    'ModuleEntity',
    'EnrichmentOutcomeEntity',
    'UserApprovalEntity',
    # Edge families
    'BaseEdge',
    'WasVerifiedByEdge',
    'HasFailureWarningEdge',
    'YieldedOutcomeEdge',
    'ApprovedByUserEdge'
]
