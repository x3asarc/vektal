"""
Entity and edge type contracts for temporal knowledge graph.

Defines Pydantic v2 models for Graphiti episode ingestion and graph-backed
Oracle evidence retrieval. All entities and edges inherit base fields for
consistent temporal tracking.

Phase 13.2 - Oracle Framework Reuse
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field, field_validator


# ===========================================
# Episode Type Taxonomy
# ===========================================

class EpisodeType(str, Enum):
    """
    Episode type taxonomy for temporal knowledge graph.

    Episodes are immutable events that capture decision outcomes,
    failure patterns, and user interventions.
    """
    ORACLE_DECISION = "oracle_decision"
    FAILURE_PATTERN = "failure_pattern"
    ENRICHMENT_OUTCOME = "enrichment_outcome"
    USER_APPROVAL = "user_approval"
    VENDOR_CATALOG_CHANGE = "vendor_catalog_change"


# ===========================================
# Base Entity Fields
# ===========================================

class BaseEntity(BaseModel):
    """
    Base entity fields inherited by all entity types.

    All entities must include:
    - entity_type: Discriminator for entity family
    - store_id: Multi-tenant isolation
    - created_at: Temporal validity anchor
    - correlation_id: Lineage tracking (when available)
    """
    entity_type: str = Field(..., description="Entity type discriminator")
    store_id: str = Field(..., description="Store ID for multi-tenant isolation")
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow(), description="Entity creation timestamp (UTC)")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for lineage tracking")


# ===========================================
# Entity Families
# ===========================================

class OracleDecisionEntity(BaseEntity):
    """
    Oracle decision outcome for governance verification.

    Captures binary pass/fail decisions with confidence scoring,
    explicit reason codes, and evidence references.
    """
    entity_type: str = Field(default="oracle_decision", frozen=True)
    decision: str = Field(..., description="Decision outcome: pass, fail, defer")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Decision confidence [0.0, 1.0]")
    reason_codes: List[str] = Field(default_factory=list, description="Machine-readable reason codes")
    evidence_refs: List[str] = Field(default_factory=list, description="References to supporting evidence")
    requires_user_action: bool = Field(default=False, description="Whether decision requires user intervention")
    source_adapter: str = Field(..., description="Adapter that produced decision (e.g., 'enrichment_oracle', 'field_policy')")


class FailurePatternEntity(BaseEntity):
    """
    Failure pattern from FAILURE_JOURNEY.md or runtime errors.

    Captures module-specific failure modes with error signatures
    and occurrence tracking for trend analysis.
    """
    entity_type: str = Field(default="failure_pattern", frozen=True)
    failure_type: str = Field(..., description="Failure category (e.g., 'timeout', 'validation', 'null_pointer')")
    module_path: str = Field(..., description="Python module path where failure occurred")
    error_signature: str = Field(..., description="Normalized error message or stack trace hash")
    occurrence_count: int = Field(default=1, ge=1, description="Number of times pattern occurred")
    last_seen_at: datetime = Field(default_factory=lambda: datetime.utcnow(), description="Most recent occurrence timestamp")


class ModuleEntity(BaseEntity):
    """
    Module health snapshot for system observability.

    Tracks health status of individual modules/services for
    graph-aware remediation planning.
    """
    entity_type: str = Field(default="module", frozen=True)
    module_name: str = Field(..., description="Human-readable module name")
    module_path: str = Field(..., description="Python module path")
    health_status: str = Field(..., description="Health status: healthy, degraded, failed")
    last_check_at: datetime = Field(default_factory=lambda: datetime.utcnow(), description="Most recent health check timestamp")


class EnrichmentOutcomeEntity(BaseEntity):
    """
    Enrichment batch outcome for quality tracking.

    Captures product-level enrichment results with profile gear,
    field modifications, and quality delta for trend analysis.
    """
    entity_type: str = Field(default="enrichment_outcome", frozen=True)
    product_id: str = Field(..., description="Product ID enriched")
    profile_gear: str = Field(..., description="Profile gear used (e.g., 'conservative', 'balanced', 'aggressive')")
    fields_modified: List[str] = Field(default_factory=list, description="List of fields modified by enrichment")
    quality_delta: float = Field(..., description="Quality score change from baseline")
    oracle_arbitration_used: bool = Field(default=False, description="Whether Oracle arbitration was invoked")


class UserApprovalEntity(BaseEntity):
    """
    User approval/rejection event for preference learning.

    Captures user decisions on proposed actions for graph-backed
    approval pattern analysis.
    """
    entity_type: str = Field(default="user_approval", frozen=True)
    action_id: str = Field(..., description="Action ID from chat or enrichment flow")
    action_type: str = Field(..., description="Action type (e.g., 'create', 'update', 'bulk_update')")
    approval_decision: str = Field(..., description="Decision: approved, rejected, modified")
    user_id: str = Field(..., description="User who made decision")
    approved_at: datetime = Field(default_factory=lambda: datetime.utcnow(), description="Approval timestamp")


# ===========================================
# Edge Families
# ===========================================

class BaseEdge(BaseModel):
    """
    Base edge fields inherited by all edge types.

    All edges must include:
    - from_entity_id: Source entity
    - to_entity_id: Target entity
    - edge_type: Edge type discriminator
    """
    from_entity_id: str = Field(..., description="Source entity ID")
    to_entity_id: str = Field(..., description="Target entity ID")
    edge_type: str = Field(..., description="Edge type discriminator")


class WasVerifiedByEdge(BaseEdge):
    """
    Verification outcome edge linking actions to Oracle decisions.

    Connects enrichment outcomes or chat actions to verification
    events for lineage tracking.
    """
    edge_type: str = Field(default="was_verified_by", frozen=True)
    verified_at: datetime = Field(default_factory=lambda: datetime.utcnow(), description="Verification timestamp")
    verification_outcome: str = Field(..., description="Outcome: verified, deferred, failed")


class HasFailureWarningEdge(BaseEdge):
    """
    Failure warning edge linking modules to failure patterns.

    Connects module health snapshots to observed failure patterns
    for graph-aware remediation.
    """
    edge_type: str = Field(default="has_failure_warning", frozen=True)
    warning_level: str = Field(..., description="Warning severity: critical, high, medium, low")
    warning_message: str = Field(..., description="Human-readable warning message")


class YieldedOutcomeEdge(BaseEdge):
    """
    Outcome edge linking actions to enrichment results.

    Connects chat actions or enrichment runs to outcome entities
    for quality trend analysis.
    """
    edge_type: str = Field(default="yielded_outcome", frozen=True)
    outcome_type: str = Field(..., description="Outcome type (e.g., 'enrichment', 'resolution', 'apply')")
    outcome_data: Dict[str, Any] = Field(default_factory=dict, description="Additional outcome metadata")


class ApprovedByUserEdge(BaseEdge):
    """
    User approval edge linking actions to approval decisions.

    Connects proposed actions to user approval events for
    preference pattern learning.
    """
    edge_type: str = Field(default="approved_by_user", frozen=True)
    user_id: str = Field(..., description="User who approved")
    approved_at: datetime = Field(default_factory=lambda: datetime.utcnow(), description="Approval timestamp")


# ===========================================
# Episode Payload Helper
# ===========================================

def create_episode_payload(
    episode_type: EpisodeType,
    store_id: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Create compliant episode payload for Graphiti ingestion.

    Ensures required base fields are present and adds created_at
    if not provided.

    Args:
        episode_type: Episode type from EpisodeType enum
        store_id: Store ID for multi-tenant isolation
        **kwargs: Additional episode-specific fields

    Returns:
        Dict with episode_type, store_id, created_at, and kwargs

    Example:
        >>> payload = create_episode_payload(
        ...     EpisodeType.ORACLE_DECISION,
        ...     store_id="store_123",
        ...     decision="pass",
        ...     confidence=0.95,
        ...     reason_codes=["no_conflicts"]
        ... )
    """
    payload = {
        'episode_type': episode_type.value,
        'store_id': store_id,
        **kwargs
    }

    # Add created_at if not provided
    if 'created_at' not in payload:
        payload['created_at'] = datetime.utcnow()

    return payload
