"""
Contract tests for Synthex entity and edge definitions.

Tests use Pydantic validation - no external dependencies required.

Phase 13.2 - Oracle Framework Reuse
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from src.core.synthex_entities import (
    EpisodeType,
    OracleDecisionEntity,
    FailurePatternEntity,
    ModuleEntity,
    EnrichmentOutcomeEntity,
    UserApprovalEntity,
    WasVerifiedByEdge,
    HasFailureWarningEdge,
    YieldedOutcomeEdge,
    ApprovedByUserEdge,
    create_episode_payload,
)


# ===========================================
# Test Entity Contracts
# ===========================================

def test_oracle_decision_entity_has_required_fields():
    """
    OracleDecisionEntity has all required contract fields.
    """
    entity = OracleDecisionEntity(
        store_id="store_123",
        decision="pass",
        confidence=0.95,
        source_adapter="enrichment_oracle"
    )

    # Verify required fields
    assert entity.entity_type == "oracle_decision"
    assert entity.store_id == "store_123"
    assert entity.decision == "pass"
    assert entity.confidence == 0.95
    assert entity.source_adapter == "enrichment_oracle"
    assert entity.reason_codes == []  # Default
    assert entity.evidence_refs == []  # Default
    assert entity.requires_user_action is False  # Default
    assert isinstance(entity.created_at, datetime)


def test_oracle_decision_entity_validates_confidence_range():
    """
    OracleDecisionEntity validates confidence is between 0.0 and 1.0.
    """
    # Valid confidence
    entity = OracleDecisionEntity(
        store_id="store_123",
        decision="pass",
        confidence=0.5,
        source_adapter="test"
    )
    assert entity.confidence == 0.5

    # Invalid confidence (too high)
    with pytest.raises(ValidationError):
        OracleDecisionEntity(
            store_id="store_123",
            decision="pass",
            confidence=1.5,
            source_adapter="test"
        )

    # Invalid confidence (negative)
    with pytest.raises(ValidationError):
        OracleDecisionEntity(
            store_id="store_123",
            decision="pass",
            confidence=-0.1,
            source_adapter="test"
        )


def test_failure_pattern_entity_has_required_fields():
    """
    FailurePatternEntity has all required contract fields.
    """
    entity = FailurePatternEntity(
        store_id="store_123",
        failure_type="timeout",
        module_path="src.tasks.enrichment",
        error_signature="abc123def456"
    )

    # Verify required fields
    assert entity.entity_type == "failure_pattern"
    assert entity.store_id == "store_123"
    assert entity.failure_type == "timeout"
    assert entity.module_path == "src.tasks.enrichment"
    assert entity.error_signature == "abc123def456"
    assert entity.occurrence_count == 1  # Default
    assert isinstance(entity.last_seen_at, datetime)


def test_failure_pattern_entity_validates_occurrence_count():
    """
    FailurePatternEntity validates occurrence_count is >= 1.
    """
    # Valid occurrence count
    entity = FailurePatternEntity(
        store_id="store_123",
        failure_type="timeout",
        module_path="src.tasks.enrichment",
        error_signature="abc123",
        occurrence_count=5
    )
    assert entity.occurrence_count == 5

    # Invalid occurrence count (zero)
    with pytest.raises(ValidationError):
        FailurePatternEntity(
            store_id="store_123",
            failure_type="timeout",
            module_path="src.tasks.enrichment",
            error_signature="abc123",
            occurrence_count=0
        )


def test_enrichment_outcome_entity_has_required_fields():
    """
    EnrichmentOutcomeEntity has all required contract fields.
    """
    entity = EnrichmentOutcomeEntity(
        store_id="store_123",
        product_id="prod_456",
        profile_gear="balanced",
        quality_delta=0.15
    )

    # Verify required fields
    assert entity.entity_type == "enrichment_outcome"
    assert entity.store_id == "store_123"
    assert entity.product_id == "prod_456"
    assert entity.profile_gear == "balanced"
    assert entity.quality_delta == 0.15
    assert entity.fields_modified == []  # Default
    assert entity.oracle_arbitration_used is False  # Default


def test_module_entity_has_required_fields():
    """
    ModuleEntity has all required contract fields.
    """
    entity = ModuleEntity(
        store_id="store_123",
        module_name="Enrichment Task",
        module_path="src.tasks.enrichment",
        health_status="healthy"
    )

    # Verify required fields
    assert entity.entity_type == "module"
    assert entity.store_id == "store_123"
    assert entity.module_name == "Enrichment Task"
    assert entity.module_path == "src.tasks.enrichment"
    assert entity.health_status == "healthy"
    assert isinstance(entity.last_check_at, datetime)


def test_user_approval_entity_has_required_fields():
    """
    UserApprovalEntity has all required contract fields.
    """
    entity = UserApprovalEntity(
        store_id="store_123",
        action_id="action_789",
        action_type="bulk_update",
        approval_decision="approved",
        user_id="user_001"
    )

    # Verify required fields
    assert entity.entity_type == "user_approval"
    assert entity.store_id == "store_123"
    assert entity.action_id == "action_789"
    assert entity.action_type == "bulk_update"
    assert entity.approval_decision == "approved"
    assert entity.user_id == "user_001"
    assert isinstance(entity.approved_at, datetime)


# ===========================================
# Test Edge Contracts
# ===========================================

def test_was_verified_by_edge_has_required_fields():
    """
    WasVerifiedByEdge has all required contract fields.
    """
    edge = WasVerifiedByEdge(
        from_entity_id="entity_1",
        to_entity_id="entity_2",
        verification_outcome="verified"
    )

    # Verify required fields
    assert edge.edge_type == "was_verified_by"
    assert edge.from_entity_id == "entity_1"
    assert edge.to_entity_id == "entity_2"
    assert edge.verification_outcome == "verified"
    assert isinstance(edge.verified_at, datetime)


def test_has_failure_warning_edge_has_required_fields():
    """
    HasFailureWarningEdge has all required contract fields.
    """
    edge = HasFailureWarningEdge(
        from_entity_id="module_1",
        to_entity_id="failure_1",
        warning_level="high",
        warning_message="Repeated timeout errors detected"
    )

    # Verify required fields
    assert edge.edge_type == "has_failure_warning"
    assert edge.from_entity_id == "module_1"
    assert edge.to_entity_id == "failure_1"
    assert edge.warning_level == "high"
    assert edge.warning_message == "Repeated timeout errors detected"


def test_yielded_outcome_edge_has_required_fields():
    """
    YieldedOutcomeEdge has all required contract fields.
    """
    edge = YieldedOutcomeEdge(
        from_entity_id="action_1",
        to_entity_id="outcome_1",
        outcome_type="enrichment"
    )

    # Verify required fields
    assert edge.edge_type == "yielded_outcome"
    assert edge.from_entity_id == "action_1"
    assert edge.to_entity_id == "outcome_1"
    assert edge.outcome_type == "enrichment"
    assert edge.outcome_data == {}  # Default


def test_approved_by_user_edge_has_required_fields():
    """
    ApprovedByUserEdge has all required contract fields.
    """
    edge = ApprovedByUserEdge(
        from_entity_id="action_1",
        to_entity_id="approval_1",
        user_id="user_001"
    )

    # Verify required fields
    assert edge.edge_type == "approved_by_user"
    assert edge.from_entity_id == "action_1"
    assert edge.to_entity_id == "approval_1"
    assert edge.user_id == "user_001"
    assert isinstance(edge.approved_at, datetime)


# ===========================================
# Test Episode Payload Helper
# ===========================================

def test_create_episode_payload_adds_required_fields():
    """
    create_episode_payload adds episode_type and store_id.
    """
    payload = create_episode_payload(
        EpisodeType.ORACLE_DECISION,
        store_id="store_123",
        decision="pass",
        confidence=0.95
    )

    # Verify required fields
    assert payload['episode_type'] == "oracle_decision"
    assert payload['store_id'] == "store_123"
    assert payload['decision'] == "pass"
    assert payload['confidence'] == 0.95
    assert 'created_at' in payload


def test_create_episode_payload_uses_provided_created_at():
    """
    create_episode_payload uses provided created_at if given.
    """
    custom_time = datetime(2026, 2, 19, 12, 0, 0)

    payload = create_episode_payload(
        EpisodeType.ORACLE_DECISION,
        store_id="store_123",
        created_at=custom_time,
        decision="pass",
        confidence=0.95
    )

    # Verify custom timestamp is preserved
    assert payload['created_at'] == custom_time


def test_create_episode_payload_generates_created_at_if_missing():
    """
    create_episode_payload generates created_at if not provided.
    """
    payload = create_episode_payload(
        EpisodeType.ORACLE_DECISION,
        store_id="store_123",
        decision="pass",
        confidence=0.95
    )

    # Verify timestamp was generated
    assert 'created_at' in payload
    assert isinstance(payload['created_at'], datetime)


# ===========================================
# Test Episode Type Enum
# ===========================================

def test_episode_type_enum_has_expected_values():
    """
    EpisodeType enum has all expected values.
    """
    # Verify enum values
    assert EpisodeType.ORACLE_DECISION.value == "oracle_decision"
    assert EpisodeType.FAILURE_PATTERN.value == "failure_pattern"
    assert EpisodeType.ENRICHMENT_OUTCOME.value == "enrichment_outcome"
    assert EpisodeType.USER_APPROVAL.value == "user_approval"
    assert EpisodeType.VENDOR_CATALOG_CHANGE.value == "vendor_catalog_change"

    # Verify all values are present
    all_values = [e.value for e in EpisodeType]
    assert len(all_values) == 5
    assert "oracle_decision" in all_values
    assert "failure_pattern" in all_values
    assert "enrichment_outcome" in all_values
    assert "user_approval" in all_values
    assert "vendor_catalog_change" in all_values


def test_episode_type_can_be_constructed_from_string():
    """
    EpisodeType can be constructed from string value.
    """
    # From string
    episode_type = EpisodeType("oracle_decision")
    assert episode_type == EpisodeType.ORACLE_DECISION

    # Invalid string raises error
    with pytest.raises(ValueError):
        EpisodeType("invalid_type")
