"""Phase 13.1-02 profile gear behavior contracts."""
from __future__ import annotations

from src.core.enrichment.pipeline import GovernedEnrichmentPipeline
from src.core.enrichment.profiles import get_profile


def test_profile_contracts_are_deterministic():
    quick = get_profile("quick")
    standard = get_profile("standard")
    deep = get_profile("deep")

    assert quick.tier == "tier_2"
    assert quick.include_visual_oracle is False
    assert quick.include_second_opinion is False

    assert standard.tier == "tier_2"
    assert standard.include_second_opinion is True
    assert standard.include_multilingual_norm is True

    assert deep.tier == "tier_3"
    assert deep.include_visual_oracle is True
    assert deep.max_retry_attempts == 3


def test_profile_fallback_defaults_to_standard():
    fallback = get_profile("not-a-real-profile")
    assert fallback.name == "standard"
    assert fallback.include_second_opinion is True


def test_pipeline_respects_profile_depth_and_cache_reuse():
    pipeline = GovernedEnrichmentPipeline(cache_ttl_seconds=60)
    product = {
        "title": "Acrylfarbe Rot 20ml",
        "merchant_title": "Acrylfarbe Rot 20ml",
        "product_type": "Farbe",
        "tags": ["farbe", "basteln"],
        "extracted_color": "red",
        "visual_hex": "#ff0000",
        "vendor_code": "PENTART",
        "sku": "P-001",
        "barcode": "123",
    }

    quick_result = pipeline.enrich_products(
        products=[product],
        profile_name="quick",
        target_language="de",
        policy_version=1,
    )[0]
    assert quick_result["profile"] == "quick"
    assert quick_result["profile_contract"]["include_visual_oracle"] is False
    assert len(quick_result["oracle_resolution"]) == 1
    assert quick_result["cache_reused"] is False

    quick_reused = pipeline.enrich_products(
        products=[product],
        profile_name="quick",
        target_language="de",
        policy_version=1,
    )[0]
    assert quick_reused["cache_reused"] is True

    deep_result = pipeline.enrich_products(
        products=[product],
        profile_name="deep",
        target_language="de",
        policy_version=1,
    )[0]
    assert deep_result["profile"] == "deep"
    assert deep_result["profile_contract"]["include_visual_oracle"] is True
    assert len(deep_result["oracle_resolution"]) >= 2
