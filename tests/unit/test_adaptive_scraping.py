"""
Unit tests for adaptive scraping system.

Tests metrics tracking, adaptive learning, and integrated behavior.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.core.scraping.metrics import ScrapeMetrics, FailureReason
from src.core.scraping.adaptive import AdaptiveRetryEngine, LearnedParams
from src.core.scraping import UniversalScraper, BatchResult


class TestScrapeMetrics:
    """Test ScrapeMetrics tracking."""

    def test_track_success(self):
        """Test tracking successful scrapes."""
        metrics = ScrapeMetrics()

        metrics.track_result('vendor1', 'SKU1', True)
        metrics.track_result('vendor1', 'SKU2', True)

        assert metrics.get_success_rate('vendor1') == 1.0

    def test_track_failure(self):
        """Test tracking failed scrapes."""
        metrics = ScrapeMetrics()

        metrics.track_result('vendor1', 'SKU1', False, FailureReason.TIMEOUT.value)
        metrics.track_result('vendor1', 'SKU2', True)

        assert metrics.get_success_rate('vendor1') == 0.5

    def test_failure_categorization(self):
        """Test failure reason categorization."""
        metrics = ScrapeMetrics()

        metrics.track_result('vendor1', 'SKU1', False, FailureReason.RATE_LIMIT.value)
        metrics.track_result('vendor1', 'SKU2', False, FailureReason.TIMEOUT.value)
        metrics.track_result('vendor1', 'SKU3', False, FailureReason.TIMEOUT.value)

        breakdown = metrics.get_failure_breakdown('vendor1')

        assert breakdown[FailureReason.RATE_LIMIT.value] == 1
        assert breakdown[FailureReason.TIMEOUT.value] == 2

    def test_vendor_stats(self):
        """Test per-vendor statistics."""
        metrics = ScrapeMetrics()

        metrics.track_result('vendor1', 'SKU1', True, retry_count=1, duration_ms=1000)
        metrics.track_result('vendor1', 'SKU2', False, FailureReason.TIMEOUT.value, retry_count=2, duration_ms=2000)
        metrics.track_result('vendor2', 'SKU3', True, retry_count=0, duration_ms=500)

        stats = metrics.get_vendor_stats()

        assert 'vendor1' in stats
        assert 'vendor2' in stats

        v1_stats = stats['vendor1']
        assert v1_stats['total_attempts'] == 2
        assert v1_stats['successful'] == 1
        assert v1_stats['failed'] == 1
        assert v1_stats['success_rate'] == 0.5
        assert v1_stats['most_common_failure'] == FailureReason.TIMEOUT.value

    def test_no_attempts_default(self):
        """Test optimistic default when no attempts."""
        metrics = ScrapeMetrics()

        # Should return 1.0 for unknown vendor
        assert metrics.get_success_rate('unknown_vendor') == 1.0

    def test_session_report(self):
        """Test markdown report generation."""
        metrics = ScrapeMetrics()

        metrics.track_result('vendor1', 'SKU1', True)
        metrics.track_result('vendor1', 'SKU2', False, FailureReason.TIMEOUT.value)

        report = metrics.export_session_report()

        assert '# Scraping Session Report' in report
        assert 'Overall Statistics' in report
        assert 'Per-Vendor Statistics' in report
        assert 'vendor1' in report


class TestAdaptiveRetryEngine:
    """Test AdaptiveRetryEngine learning."""

    def test_rate_limit_increases_delay(self):
        """Test that rate limits increase delay."""
        metrics = ScrapeMetrics()
        adaptive = AdaptiveRetryEngine(metrics)

        # Initial delay
        params = adaptive.get_retry_params('vendor1', attempt_number=1)
        initial_delay = params.delay_ms

        # Learn from rate limit
        adaptive.learn_from_failure(
            'vendor1',
            FailureReason.RATE_LIMIT.value,
            {'delay_ms': initial_delay}
        )

        # Delay should increase
        new_params = adaptive.get_retry_params('vendor1', attempt_number=1)
        assert new_params.delay_ms > initial_delay

    def test_timeout_increases_timeout(self):
        """Test that timeouts increase timeout duration."""
        metrics = ScrapeMetrics()
        adaptive = AdaptiveRetryEngine(metrics)

        # Initial timeout
        params = adaptive.get_retry_params('vendor1', attempt_number=1)
        initial_timeout = params.timeout_ms

        # Learn from timeout
        adaptive.learn_from_failure(
            'vendor1',
            FailureReason.TIMEOUT.value,
            {'timeout_ms': initial_timeout}
        )

        # Timeout should increase
        new_params = adaptive.get_retry_params('vendor1', attempt_number=1)
        assert new_params.timeout_ms > initial_timeout

    def test_selector_failure_triggers_fallback(self):
        """Test that selector failures trigger fallback usage."""
        metrics = ScrapeMetrics()
        adaptive = AdaptiveRetryEngine(metrics)

        # Initially no fallback
        params = adaptive.get_retry_params('vendor1', attempt_number=1)
        assert not params.use_fallback_selectors

        # Multiple selector failures
        for _ in range(3):
            adaptive.learn_from_failure(
                'vendor1',
                FailureReason.SELECTOR_FAILED.value
            )

        # Fallback should be enabled
        new_params = adaptive.get_retry_params('vendor1', attempt_number=1)
        assert new_params.use_fallback_selectors

    def test_rediscovery_trigger_selector_failures(self):
        """Test rediscovery triggered by selector failures."""
        metrics = ScrapeMetrics()
        adaptive = AdaptiveRetryEngine(metrics)

        # Track multiple selector failures
        for i in range(6):
            metrics.track_result(
                'vendor1',
                f'SKU{i}',
                False,
                FailureReason.SELECTOR_FAILED.value
            )
            adaptive.learn_from_failure(
                'vendor1',
                FailureReason.SELECTOR_FAILED.value
            )

        # Should trigger rediscovery
        assert adaptive.should_trigger_rediscovery('vendor1')

    def test_rediscovery_trigger_low_success_rate(self):
        """Test rediscovery triggered by low success rate."""
        metrics = ScrapeMetrics()
        adaptive = AdaptiveRetryEngine(metrics)

        # Simulate 40% success rate
        for i in range(10):
            success = i < 4  # 4 successes out of 10
            failure_reason = None if success else FailureReason.UNKNOWN.value
            metrics.track_result('vendor1', f'SKU{i}', success, failure_reason)
            # Also record in adaptive engine's recent failures
            if not success:
                adaptive.learn_from_failure('vendor1', failure_reason)

        # Should trigger rediscovery (< 50%)
        assert adaptive.should_trigger_rediscovery('vendor1')

    def test_fallback_selector_chain(self):
        """Test fallback selector chain generation."""
        metrics = ScrapeMetrics()
        adaptive = AdaptiveRetryEngine(metrics)

        chain = adaptive.get_fallback_selector_chain(
            'vendor1',
            'title',
            primary_selector='h1.product-name'
        )

        # Primary should be first
        assert chain[0] == 'h1.product-name'

        # Should include common fallbacks
        assert len(chain) > 1
        assert 'h1' in chain

    def test_exponential_backoff(self):
        """Test exponential backoff calculation."""
        metrics = ScrapeMetrics()
        adaptive = AdaptiveRetryEngine(metrics)

        # Get delays for increasing attempts
        params1 = adaptive.get_retry_params('vendor1', attempt_number=1)
        params2 = adaptive.get_retry_params('vendor1', attempt_number=2)
        params3 = adaptive.get_retry_params('vendor1', attempt_number=3)

        # Should increase exponentially (roughly)
        # Account for jitter by checking general trend
        assert params2.delay_ms > params1.delay_ms
        assert params3.delay_ms > params2.delay_ms

    def test_reset_vendor_learning(self):
        """Test resetting learned parameters."""
        metrics = ScrapeMetrics()
        adaptive = AdaptiveRetryEngine(metrics)

        # Learn from failure
        adaptive.learn_from_failure('vendor1', FailureReason.RATE_LIMIT.value)

        # Get params (should be modified)
        params_before = adaptive.get_retry_params('vendor1', attempt_number=1)

        # Reset
        adaptive.reset_vendor_learning('vendor1')

        # Should return to defaults
        params_after = adaptive.get_retry_params('vendor1', attempt_number=1)

        # After reset, delay should be back to default
        assert params_after.delay_ms < params_before.delay_ms

    def test_learning_summary(self):
        """Test learning summary export."""
        metrics = ScrapeMetrics()
        adaptive = AdaptiveRetryEngine(metrics)

        # Learn from various failures
        adaptive.learn_from_failure('vendor1', FailureReason.RATE_LIMIT.value)
        adaptive.learn_from_failure('vendor1', FailureReason.TIMEOUT.value)
        adaptive.learn_from_failure('vendor2', FailureReason.SELECTOR_FAILED.value)

        summary = adaptive.get_learning_summary()

        assert 'vendor1' in summary
        assert 'vendor2' in summary
        assert summary['vendor1']['delay_ms'] > 2000  # Should be increased


class TestIntegratedAdaptiveScraping:
    """Test integrated adaptive behavior in UniversalScraper."""

    @pytest.mark.asyncio
    async def test_metrics_tracked_on_success(self):
        """Test metrics are tracked on successful scrape."""
        scraper = UniversalScraper()

        # Mock vendor config
        mock_config = Mock()
        mock_config.vendor.name = 'test_vendor'
        mock_config.vendor.domain = 'test.com'
        mock_config.urls = {'product': {'template': 'https://{domain}/p/{sku}'}}
        mock_config.gsd_mappings = None  # No direct mappings
        mock_config.scraping = {
            'strategy': {'primary': 'requests', 'fallback': []},
            'timing': {}
        }
        mock_config.selectors = {}
        mock_config.validation = {}
        mock_config.variants = None

        # Mock strategy to return success
        mock_strategy = AsyncMock()
        mock_strategy.scrape.return_value = Mock(
            success=True,
            title='Test Product',
            description='Test description',
            price='$10',
            images=['http://test.com/img.jpg'],
            sku_on_page='SKU1',
            availability='In stock',
            error=None
        )

        scraper._strategies['requests'] = mock_strategy

        # Scrape
        result = await scraper.scrape('SKU1', mock_config)

        # Check metrics tracked
        assert scraper.metrics.get_success_rate('test_vendor') == 1.0

    @pytest.mark.asyncio
    async def test_metrics_tracked_on_failure(self):
        """Test metrics are tracked on failed scrape."""
        scraper = UniversalScraper()

        # Mock vendor config
        mock_config = Mock()
        mock_config.vendor.name = 'test_vendor'
        mock_config.vendor.domain = 'test.com'
        mock_config.urls = {'product': {'template': 'https://{domain}/p/{sku}'}}
        mock_config.gsd_mappings = None
        mock_config.scraping = {
            'strategy': {'primary': 'requests', 'fallback': []},
            'timing': {}
        }
        mock_config.selectors = {}
        mock_config.variants = None

        # Mock strategy to return failure
        mock_strategy = AsyncMock()
        mock_strategy.scrape.return_value = Mock(
            success=False,
            error='Timeout error'
        )

        scraper._strategies['requests'] = mock_strategy

        # Scrape
        result = await scraper.scrape('SKU1', mock_config)

        # Check metrics tracked
        assert scraper.metrics.get_success_rate('test_vendor') < 1.0

        # Check failure categorized
        breakdown = scraper.metrics.get_failure_breakdown('test_vendor')
        assert FailureReason.TIMEOUT.value in breakdown

    @pytest.mark.asyncio
    async def test_batch_result_includes_metrics(self):
        """Test batch scrape returns BatchResult with metrics."""
        scraper = UniversalScraper()

        # Mock vendor config
        mock_config = Mock()
        mock_config.vendor.name = 'test_vendor'
        mock_config.vendor.domain = 'test.com'
        mock_config.urls = {'product': {'template': 'https://{domain}/p/{sku}'}}
        mock_config.gsd_mappings = None
        mock_config.scraping = {
            'strategy': {'primary': 'requests', 'fallback': []},
            'timing': {}
        }
        mock_config.selectors = {}
        mock_config.validation = {}
        mock_config.variants = None

        # Mock strategy - 2 successes, 1 failure
        mock_strategy = AsyncMock()
        call_count = [0]

        def mock_scrape_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                # Second call fails
                return Mock(success=False, error='Timeout error')
            else:
                return Mock(
                    success=True,
                    title='Test Product',
                    description='Test',
                    price='$10',
                    images=['http://test.com/img.jpg'],
                    sku_on_page=f'SKU{call_count[0]}',
                    availability='In stock',
                    error=None
                )

        mock_strategy.scrape.side_effect = mock_scrape_side_effect
        scraper._strategies['requests'] = mock_strategy

        # Batch scrape
        batch_result = await scraper.scrape_batch(
            ['SKU1', 'SKU2', 'SKU3'],
            mock_config,
            batch_size=3
        )

        # Check BatchResult structure
        assert isinstance(batch_result, BatchResult)
        assert len(batch_result.results) == 3
        assert 0.0 <= batch_result.success_rate <= 1.0
        assert isinstance(batch_result.failure_breakdown, dict)
        assert isinstance(batch_result.recommendations, list)

    @pytest.mark.asyncio
    async def test_rediscovery_recommendation_in_batch(self):
        """Test batch result includes rediscovery recommendation."""
        scraper = UniversalScraper()

        # Mock vendor config
        mock_config = Mock()
        mock_config.vendor.name = 'test_vendor'
        mock_config.vendor.domain = 'test.com'
        mock_config.urls = {'product': {'template': 'https://{domain}/p/{sku}'}}
        mock_config.gsd_mappings = None
        mock_config.scraping = {
            'strategy': {'primary': 'requests', 'fallback': []},
            'timing': {}
        }
        mock_config.selectors = {}
        mock_config.variants = None

        # Mock strategy - all selector failures
        mock_strategy = AsyncMock()
        mock_strategy.scrape.return_value = Mock(
            success=False,
            error='Element not found'
        )

        scraper._strategies['requests'] = mock_strategy

        # Batch scrape with many failures
        batch_result = await scraper.scrape_batch(
            [f'SKU{i}' for i in range(10)],
            mock_config,
            batch_size=10
        )

        # Should recommend rediscovery
        assert any('rediscovery' in rec.lower() for rec in batch_result.recommendations)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
