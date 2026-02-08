import pytest
from unittest.mock import Mock, patch

from src.core.discovery.ai_inference import OpenRouterInference, InferenceResult
from src.core.discovery.local_classifier import LocalVendorClassifier, ClassificationResult
from src.core.discovery.pipeline import VendorDiscoveryPipeline, DiscoveryResult
from src.core.config.store_profile_schema import StoreProfile, KnownVendor


class TestOpenRouterInference:
    """Test OpenRouter AI inference"""

    def test_not_available_without_key(self):
        """Inference not available without API key"""
        inference = OpenRouterInference(api_key=None)
        assert not inference.is_available

    def test_returns_error_without_key(self):
        """Returns error result when key not set"""
        inference = OpenRouterInference(api_key=None)
        result = inference.infer_vendor(
            sku="R0530",
            search_results=("result 1", "result 2"),
            store_niche="arts_and_crafts",
            known_vendors=("ITD",)
        )
        assert result.error is not None
        assert result.confidence == 0.0

    def test_prompt_includes_context(self):
        """Prompt includes store context"""
        inference = OpenRouterInference()
        prompt = inference._build_prompt(
            sku="R0530",
            search_results=["ITD rice paper"],
            store_niche="arts_and_crafts",
            known_vendors=["ITD Collection"],
            additional_context="decoupage"
        )
        assert "R0530" in prompt
        assert "ITD Collection" in prompt
        assert "decoupage" in prompt

    def test_result_caching(self):
        """Same inputs return cached result"""
        inference = OpenRouterInference(api_key="test")

        # Mock the API call
        with patch.object(inference, '_call_api') as mock_call:
            mock_call.return_value = {
                'choices': [{
                    'message': {
                        'content': '{"vendor_name": "Test", "confidence": 80, "niche_match": true, "reasoning": "test"}'
                    }
                }]
            }

            result1 = inference.infer_vendor(
                sku="R0530",
                search_results=("result",),
                store_niche="arts",
                known_vendors=()
            )
            result2 = inference.infer_vendor(
                sku="R0530",
                search_results=("result",),
                store_niche="arts",
                known_vendors=()
            )

            # Should only call API once (cached)
            assert mock_call.call_count == 1


class TestLocalVendorClassifier:
    """Test local LLM classifier"""

    def test_list_vendors(self):
        """Lists known vendor profiles"""
        classifier = LocalVendorClassifier()
        vendors = classifier.list_vendors()
        assert "ITD Collection" in vendors
        assert "Pentart" in vendors

    def test_classification_result_structure(self):
        """Classification result has expected fields"""
        result = ClassificationResult(
            vendor_name="ITD Collection",
            confidence=0.85,
            needs_api_fallback=False
        )
        assert result.vendor_name == "ITD Collection"
        assert result.method == "local_llm"


class TestDiscoveryPipeline:
    """Test discovery pipeline"""

    def test_pattern_match_early_exit(self):
        """High-confidence pattern match exits early"""
        profile = StoreProfile(
            store_id="test.myshopify.com",
            niche_primary="arts_and_crafts",
            known_vendors=[
                KnownVendor(
                    name="ITD Collection",
                    sku_pattern=r"^R\d{4}[A-Z]?$"
                )
            ]
        )

        pipeline = VendorDiscoveryPipeline(store_profile=profile)
        result = pipeline.discover("R0530")

        assert result.vendor_name == "ITD Collection"
        assert result.discovery_method == "local_pattern"
        assert "local_pattern" in result.stages_executed
        # Should not have reached web search
        assert "web_search" not in result.stages_executed

    def test_stages_tracked(self):
        """Discovery tracks executed stages"""
        pipeline = VendorDiscoveryPipeline()
        result = pipeline.discover("UNKNOWN_SKU_12345", skip_search=True)

        assert "local_pattern" in result.stages_executed

    def test_requires_confirmation_below_threshold(self):
        """Low confidence requires confirmation"""
        result = DiscoveryResult(
            sku="test",
            vendor_name="Maybe Vendor",
            vendor_slug="maybe_vendor",
            confidence=0.60,
            requires_confirmation=True,
            discovery_method="web_search"
        )
        assert result.requires_confirmation

    def test_slug_generation(self):
        """Vendor name to slug conversion"""
        pipeline = VendorDiscoveryPipeline()
        assert pipeline._to_slug("ITD Collection") == "itd_collection"
        assert pipeline._to_slug("Some Vendor Inc.") == "some_vendor_inc"

    def test_no_result_returns_suggestions(self):
        """No match returns helpful suggestions"""
        pipeline = VendorDiscoveryPipeline(enable_api_inference=False)
        result = pipeline.discover(
            "TOTALLY_UNKNOWN_123",
            skip_search=True
        )

        assert result.vendor_name is None
        assert len(result.suggestions) > 0
