"""Phase 13.1-02 Oracle arbitration contracts."""
from __future__ import annotations

from src.core.enrichment.oracle_contract import merchant_first_arbitration, normalize_legacy_decision
from src.core.enrichment.oracles.content_oracle import evaluate_content_oracle
from src.core.enrichment.oracles.policy_oracle import evaluate_policy_oracle
from src.core.enrichment.oracles.visual_oracle import evaluate_visual_oracle


def test_merchant_first_conflict_returns_review_not_overwrite():
    decision = merchant_first_arbitration(
        merchant_value="Handmade Cotton",
        candidate_value="Polyester Blend",
        confidence=0.95,
        structural_conflict=False,
    )
    assert decision.decision == "review"
    assert decision.requires_user_action is True


def test_content_oracle_holds_on_low_confidence_conflict():
    decision = evaluate_content_oracle(
        merchant_value="Premium Cotton",
        candidate_value="Standard Cotton",
        confidence=0.5,
        structural_conflict=True,
        evidence_refs=["description_line_1"],
    )
    assert decision.decision == "hold"
    assert "content_low_confidence" in decision.reason_codes
    assert "content_structural_conflict" in decision.reason_codes


def test_visual_oracle_detects_text_image_mismatch():
    decision = evaluate_visual_oracle(
        text_color="blue",
        visual_hex="#ff0000",
        confidence=0.9,
        evidence_refs=["image:primary"],
    )
    assert decision.decision == "hold"
    assert "visual_text_conflict" in decision.reason_codes
    assert decision.requires_user_action is True


def test_policy_oracle_fails_immutable_and_holds_threshold():
    immutable = evaluate_policy_oracle(
        field_name="admin_email",
        before_value="a@example.com",
        after_value="b@example.com",
        immutable_fields=["admin_email"],
        hitl_thresholds={},
    )
    assert immutable.decision == "fail"
    assert "policy_immutable_field" in immutable.reason_codes

    threshold = evaluate_policy_oracle(
        field_name="price",
        before_value=10,
        after_value=20,
        immutable_fields=[],
        hitl_thresholds={"price_change_percent": 15.0},
    )
    assert threshold.decision == "hold"
    assert "policy_threshold_hit" in threshold.reason_codes


def test_normalize_legacy_decision_maps_old_vocabulary():
    assert normalize_legacy_decision("accept") == "pass"
    assert normalize_legacy_decision("suggest") == "review"
    assert normalize_legacy_decision("reject") == "fail"
    assert normalize_legacy_decision("hold") == "hold"
    # New vocabulary unchanged
    assert normalize_legacy_decision("pass") == "pass"
    assert normalize_legacy_decision("review") == "review"
    assert normalize_legacy_decision("fail") == "fail"
