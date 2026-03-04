"""
Unit tests for chat routing infrastructure.

Tests pattern matching, intent classification, handler routing, and response generation.
"""

import pytest
import requests
from unittest.mock import Mock, patch
from src.core.chat.router import (
    ChatRouter,
    PatternMatcher,
    APILLMClassifier,
    IntentType,
    Intent,
    RouteResult
)
from src.core.chat.handlers.product import ProductHandler
from src.core.chat.handlers.vendor import VendorHandler
from src.core.chat.handlers.generic import GenericHandler


class TestPatternMatcher:
    """Test pattern matching for common intents."""

    def setup_method(self):
        self.matcher = PatternMatcher()

    def test_bare_sku_pattern(self):
        """Test bare SKU recognition."""
        intent = self.matcher.match('R0530')
        assert intent is not None
        assert intent.type == IntentType.ADD_PRODUCT
        assert intent.entities.get('sku') == 'R0530'
        assert intent.confidence == 0.95
        assert intent.method == 'pattern'

    def test_sku_with_dashes(self):
        """Test SKU with dashes."""
        intent = self.matcher.match('P-12345')
        assert intent is not None
        assert intent.type == IntentType.ADD_PRODUCT
        assert intent.entities.get('sku') == 'P-12345'

    def test_add_product_explicit(self):
        """Test explicit add product command."""
        test_cases = [
            'add sku: R0530',
            'add product R0530',
            'add R0531',
            'sku: R0532',
            'product: R0533'
        ]

        for test_case in test_cases:
            intent = self.matcher.match(test_case)
            assert intent is not None, f"Failed to match: {test_case}"
            assert intent.type == IntentType.ADD_PRODUCT
            assert 'sku' in intent.entities

    def test_update_product(self):
        """Test update product patterns."""
        test_cases = [
            'update R0530',
            'update product R0530',
            'refresh R0530',
            'refresh product R0530'
        ]

        for test_case in test_cases:
            intent = self.matcher.match(test_case)
            assert intent is not None, f"Failed to match: {test_case}"
            assert intent.type == IntentType.UPDATE_PRODUCT
            assert intent.entities.get('sku') in ['R0530']

    def test_search_vendor(self):
        """Test vendor search patterns."""
        test_cases = [
            'find vendor for R0530',
            'search vendor for R0530',
            'who makes R0530',
            'who sells R0530',
            'vendor for R0530'
        ]

        for test_case in test_cases:
            intent = self.matcher.match(test_case)
            assert intent is not None, f"Failed to match: {test_case}"
            assert intent.type == IntentType.SEARCH_VENDOR
            assert intent.entities.get('sku') == 'R0530'

    def test_list_vendors(self):
        """Test list vendors patterns."""
        test_cases = [
            'list vendors',
            'show vendors',
            'show all vendors',
            'vendors',
            'what vendors',
            'which vendors'
        ]

        for test_case in test_cases:
            intent = self.matcher.match(test_case)
            assert intent is not None, f"Failed to match: {test_case}"
            assert intent.type == IntentType.LIST_VENDORS

    def test_help_patterns(self):
        """Test help patterns."""
        test_cases = [
            'help',
            '?',
            '???',
            'what can you do',
            'what can i do',
            'how can you help'
        ]

        for test_case in test_cases:
            intent = self.matcher.match(test_case)
            assert intent is not None, f"Failed to match: {test_case}"
            assert intent.type == IntentType.HELP

    def test_small_talk_patterns_route_to_unknown(self):
        """Small talk should short-circuit to UNKNOWN via pattern matching."""
        test_cases = [
            'hi',
            'hello',
            "what's up",
            'how are you?',
            'thanks!',
            "i'm not sure where to start",
        ]

        for test_case in test_cases:
            intent = self.matcher.match(test_case)
            assert intent is not None, f"Failed to match: {test_case}"
            assert intent.type == IntentType.UNKNOWN
            assert intent.method == 'pattern'

    def test_status_patterns(self):
        """Test status patterns."""
        test_cases = [
            'status',
            'what is the status',
            'how is it going'
        ]

        for test_case in test_cases:
            intent = self.matcher.match(test_case)
            assert intent is not None, f"Failed to match: {test_case}"
            assert intent.type == IntentType.GET_STATUS

    def test_priority_order(self):
        """Test that help is matched before bare SKU pattern."""
        intent = self.matcher.match('help')
        assert intent.type == IntentType.HELP

        intent = self.matcher.match('status')
        assert intent.type == IntentType.GET_STATUS

        intent = self.matcher.match('vendors')
        assert intent.type == IntentType.LIST_VENDORS

    def test_no_match(self):
        """Test messages that don't match patterns."""
        intent = self.matcher.match('this is some random text')
        assert intent is None
        intent = self.matcher.match('hiii')
        assert intent is None

    def test_case_insensitive(self):
        """Test case insensitive matching."""
        intent = self.matcher.match('HELP')
        assert intent.type == IntentType.HELP

        intent = self.matcher.match('Add SKU: r0530')
        assert intent.type == IntentType.ADD_PRODUCT
        assert intent.entities.get('sku') == 'R0530'  # Should be uppercase


class TestProductHandler:
    """Test product handler responses."""

    def setup_method(self):
        self.handler = ProductHandler()

    def test_add_product_no_sku(self):
        """Test add product without SKU."""
        intent = Intent(
            type=IntentType.ADD_PRODUCT,
            confidence=0.95,
            entities={},
            raw_message='add product'
        )

        result = self.handler.handle_add_product(intent)
        assert result['status'] == 'error'
        assert 'No SKU' in result['message']

    def test_add_product_with_sku(self):
        """Test add product with SKU."""
        intent = Intent(
            type=IntentType.ADD_PRODUCT,
            confidence=0.95,
            entities={'sku': 'R0530'},
            raw_message='R0530'
        )

        result = self.handler.handle_add_product(intent)
        assert result['status'] in ['pending', 'exists']
        assert result['sku'] == 'R0530'

    def test_update_product_no_sku(self):
        """Test update product without SKU."""
        intent = Intent(
            type=IntentType.UPDATE_PRODUCT,
            confidence=0.95,
            entities={},
            raw_message='update product'
        )

        result = self.handler.handle_update_product(intent)
        assert result['status'] == 'error'
        assert 'No SKU' in result['message']

    def test_update_product_with_sku(self):
        """Test update product with SKU."""
        intent = Intent(
            type=IntentType.UPDATE_PRODUCT,
            confidence=0.95,
            entities={'sku': 'R0530'},
            raw_message='update R0530'
        )

        result = self.handler.handle_update_product(intent)
        assert result['status'] in ['refreshing', 'not_found']
        assert result['sku'] == 'R0530'


class TestVendorHandler:
    """Test vendor handler responses."""

    def setup_method(self):
        self.handler = VendorHandler()

    def test_search_vendor_no_sku(self):
        """Test search vendor without SKU."""
        intent = Intent(
            type=IntentType.SEARCH_VENDOR,
            confidence=0.95,
            entities={},
            raw_message='find vendor'
        )

        result = self.handler.handle_search_vendor(intent)
        assert result['status'] == 'error'
        assert 'No SKU' in result['message']

    def test_search_vendor_with_sku(self):
        """Test search vendor with SKU."""
        intent = Intent(
            type=IntentType.SEARCH_VENDOR,
            confidence=0.95,
            entities={'sku': 'R0530'},
            raw_message='find vendor for R0530'
        )

        result = self.handler.handle_search_vendor(intent)
        assert result['status'] in ['found', 'not_found']
        assert result['sku'] == 'R0530'

    def test_list_vendors(self):
        """Test list vendors."""
        intent = Intent(
            type=IntentType.LIST_VENDORS,
            confidence=0.95,
            entities={},
            raw_message='list vendors'
        )

        result = self.handler.handle_list_vendors(intent)
        assert result['status'] in ['success', 'empty']

    def test_discover_vendor_no_target(self):
        """Test discover vendor without target."""
        intent = Intent(
            type=IntentType.DISCOVER_VENDOR,
            confidence=0.95,
            entities={},
            raw_message='discover vendor'
        )

        result = self.handler.handle_discover_vendor(intent)
        assert result['status'] == 'error'
        assert 'No vendor URL' in result['message']

    def test_discover_vendor_with_target(self):
        """Test discover vendor with target."""
        intent = Intent(
            type=IntentType.DISCOVER_VENDOR,
            confidence=0.95,
            entities={'target': 'https://example.com'},
            raw_message='discover vendor https://example.com'
        )

        result = self.handler.handle_discover_vendor(intent)
        assert result['status'] in ['discovering', 'known']


class TestGenericHandler:
    """Test generic handler responses."""

    def setup_method(self):
        self.handler = GenericHandler()

    def test_help(self):
        """Test help response."""
        intent = Intent(
            type=IntentType.HELP,
            confidence=0.95,
            entities={},
            raw_message='help'
        )

        result = self.handler.handle_help(intent)
        assert result['status'] == 'success'
        assert 'commands' in result
        assert len(result['commands']) > 0

        # Verify categories exist
        categories = [cmd['category'] for cmd in result['commands']]
        assert 'Product Management' in categories
        assert 'Vendor Management' in categories
        assert 'System' in categories

    def test_status(self):
        """Test status response."""
        intent = Intent(
            type=IntentType.GET_STATUS,
            confidence=0.95,
            entities={},
            raw_message='status'
        )

        result = self.handler.handle_status(intent)
        assert result['status'] == 'success'
        assert 'stats' in result
        assert 'health' in result

        # Verify stats structure
        stats = result['stats']
        assert 'products_total' in stats
        assert 'vendors_configured' in stats

    def test_unknown(self):
        """Test unknown intent response."""
        intent = Intent(
            type=IntentType.UNKNOWN,
            confidence=0.0,
            entities={},
            raw_message='this is gibberish'
        )

        result = self.handler.handle_unknown(intent)
        assert result['status'] == 'unknown'
        assert 'suggestions' in result
        assert len(result['suggestions']) > 0


class TestChatRouter:
    """Test complete chat routing flow."""

    def setup_method(self):
        self.router = ChatRouter()

        # Register handlers
        product_handler = ProductHandler()
        vendor_handler = VendorHandler()
        generic_handler = GenericHandler()

        self.router.register_handler(
            IntentType.ADD_PRODUCT,
            product_handler.handle_add_product
        )
        self.router.register_handler(
            IntentType.UPDATE_PRODUCT,
            product_handler.handle_update_product
        )
        self.router.register_handler(
            IntentType.SEARCH_VENDOR,
            vendor_handler.handle_search_vendor
        )
        self.router.register_handler(
            IntentType.DISCOVER_VENDOR,
            vendor_handler.handle_discover_vendor
        )
        self.router.register_handler(
            IntentType.LIST_VENDORS,
            vendor_handler.handle_list_vendors
        )
        self.router.register_handler(
            IntentType.HELP,
            generic_handler.handle_help
        )
        self.router.register_handler(
            IntentType.GET_STATUS,
            generic_handler.handle_status
        )
        self.router.register_handler(
            IntentType.UNKNOWN,
            generic_handler.handle_unknown
        )

    def test_route_bare_sku(self):
        """Test routing bare SKU to add product."""
        result = self.router.route('R0530')

        assert result.intent.type == IntentType.ADD_PRODUCT
        assert result.intent.method == 'pattern'
        assert result.intent.confidence >= 0.90
        assert result.handler_name == 'add_product'
        assert result.response is not None
        assert result.error is None

    def test_route_help(self):
        """Test routing help command."""
        result = self.router.route('help')

        assert result.intent.type == IntentType.HELP
        assert result.handler_name == 'help'
        assert result.response is not None
        assert result.response['status'] == 'success'

    def test_route_list_vendors(self):
        """Test routing list vendors command."""
        result = self.router.route('list vendors')

        assert result.intent.type == IntentType.LIST_VENDORS
        assert result.handler_name == 'list_vendors'
        assert result.response is not None

    def test_route_status(self):
        """Test routing status command."""
        result = self.router.route('status')

        assert result.intent.type == IntentType.GET_STATUS
        assert result.handler_name == 'get_status'
        assert result.response is not None

    def test_route_unknown_message(self):
        """Test routing unknown message."""
        result = self.router.route('this is totally random gibberish')

        # Should fall through to API LLM (which will return UNKNOWN without API key)
        assert result.intent.type == IntentType.UNKNOWN
        assert result.handler_name == 'unknown'

    def test_route_small_talk_message(self):
        """Small talk should not require local/API classification."""
        result = self.router.route('hi')
        assert result.intent.type == IntentType.UNKNOWN
        assert result.intent.method == 'pattern'
        assert result.handler_name == 'unknown'

        result = self.router.route("i'm not sure where to start")
        assert result.intent.type == IntentType.UNKNOWN
        assert result.intent.method == 'pattern'
        assert result.handler_name == 'unknown'

    def test_no_handler_registered(self):
        """Test behavior when no handler registered for intent."""
        router = ChatRouter()  # Fresh router with no handlers

        result = router.route('help')

        assert result.intent.type == IntentType.HELP
        assert result.error is not None
        assert 'No handler registered' in result.error

    def test_handler_exception(self):
        """Test behavior when handler raises exception."""
        router = ChatRouter()

        # Register handler that raises exception
        def bad_handler(intent):
            raise ValueError("Test error")

        router.register_handler(IntentType.HELP, bad_handler)

        result = router.route('help')

        assert result.intent.type == IntentType.HELP
        assert result.error is not None
        assert 'Test error' in result.error

    def test_pattern_match_coverage(self):
        """Test that pattern matching handles 80%+ of common queries."""
        common_queries = [
            'R0530',
            'add R0531',
            'update R0532',
            'find vendor for R0533',
            'list vendors',
            'help',
            'status',
            'who sells R0534',
            'refresh R0535',
            'vendors'
        ]

        pattern_matches = 0
        for query in common_queries:
            result = self.router.route(query)
            if result.intent.method == 'pattern':
                pattern_matches += 1

        coverage = pattern_matches / len(common_queries)
        assert coverage >= 0.80, f"Pattern coverage {coverage:.0%} is below 80% target"

    def test_response_structure(self):
        """Test that responses have required structure for API."""
        result = self.router.route('help')

        # Verify RouteResult structure
        assert hasattr(result, 'intent')
        assert hasattr(result, 'handler_name')
        assert hasattr(result, 'response')
        assert hasattr(result, 'error')

        # Verify Intent structure
        intent = result.intent
        assert hasattr(intent, 'type')
        assert hasattr(intent, 'confidence')
        assert hasattr(intent, 'entities')
        assert hasattr(intent, 'raw_message')
        assert hasattr(intent, 'method')

        # Verify response is JSON-serializable
        import json
        if result.response:
            json_str = json.dumps(result.response)
            assert json_str is not None


class TestIntegration:
    """Integration tests for complete chat flow."""

    def test_end_to_end_product_addition(self):
        """Test complete flow for adding a product."""
        router = ChatRouter()
        product_handler = ProductHandler()
        router.register_handler(IntentType.ADD_PRODUCT, product_handler.handle_add_product)

        # User types bare SKU
        result = router.route('R0530')

        # Should route to add_product
        assert result.intent.type == IntentType.ADD_PRODUCT
        assert result.intent.confidence >= 0.90
        assert result.handler_name == 'add_product'

        # Should return structured response
        assert result.response is not None
        assert 'sku' in result.response
        assert result.response['sku'] == 'R0530'

    def test_end_to_end_vendor_search(self):
        """Test complete flow for vendor search."""
        router = ChatRouter()
        vendor_handler = VendorHandler()
        router.register_handler(IntentType.SEARCH_VENDOR, vendor_handler.handle_search_vendor)

        # User asks who sells product
        result = router.route('who sells R0530')

        # Should route to search_vendor
        assert result.intent.type == IntentType.SEARCH_VENDOR
        assert result.handler_name == 'search_vendor'

        # Should return structured response
        assert result.response is not None
        assert 'sku' in result.response
        assert result.response['sku'] == 'R0530'

    def test_tiered_classification(self):
        """Test tiered classification approach."""
        router = ChatRouter()

        # Pattern matching (tier 1)
        result = router.route('help')
        assert result.intent.method == 'pattern'

        # Local LLM would be tier 2 (requires sentence-transformers)
        # API LLM would be tier 3 (requires API key)

        # Verify fallback to API LLM for unknown
        result = router.route('this is totally ambiguous text')
        assert result.intent.method in ['local_llm', 'api_llm']


class TestAPILLMClassifier:
    """Focused tests for API classifier error-handling paths."""

    def test_auth_failure_returns_unknown_without_error_log(self):
        """HTTP 401/403 should degrade gracefully without error-level logging."""
        classifier = APILLMClassifier(api_key="invalid-key")
        error = requests.HTTPError("Unauthorized")
        response = requests.Response()
        response.status_code = 401
        error.response = response

        with patch("requests.post", side_effect=error), patch("src.core.chat.router.logger") as mock_logger:
            intent = classifier.classify("some ambiguous request")

        assert intent.type == IntentType.UNKNOWN
        assert intent.method == "api_llm"
        mock_logger.warning.assert_called()
        mock_logger.error.assert_not_called()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
