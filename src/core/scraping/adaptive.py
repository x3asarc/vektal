"""
Adaptive Retry Engine

Learns from scraping failures and dynamically adjusts retry strategies,
delays, timeouts, and selector fallbacks to improve success rates.
"""

import logging
import random
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Optional

from .metrics import ScrapeMetrics, FailureReason

logger = logging.getLogger(__name__)


@dataclass
class RetryParams:
    """Retry parameters for a scrape attempt."""
    delay_ms: int
    timeout_ms: int
    max_attempts: int
    use_fallback_selectors: bool


@dataclass
class LearnedParams:
    """Learned parameters for a vendor."""
    delay_ms: int = 2000  # Default 2s
    timeout_ms: int = 30000  # Default 30s
    max_attempts: int = 3
    selector_failures: int = 0
    recent_failures: deque = None  # Track last 10 failure reasons

    def __post_init__(self):
        if self.recent_failures is None:
            self.recent_failures = deque(maxlen=10)


# Common fallback selectors for various product fields
FALLBACK_SELECTORS = {
    'title': [
        'h1',
        'h1.product-title',
        'h1.product__title',
        '.product-title',
        '.product__title',
        '[itemprop="name"]',
        'meta[property="og:title"]',  # OpenGraph
        'title'  # Last resort
    ],
    'images': [
        'img.product-image',
        'img.product__image',
        '.product-images img',
        '.product__images img',
        '[data-product-image]',
        'img[itemprop="image"]',
        'meta[property="og:image"]'
    ],
    'price': [
        '.price',
        '.product-price',
        '.product__price',
        '[itemprop="price"]',
        'meta[property="product:price:amount"]'
    ],
    'description': [
        '.product-description',
        '.product__description',
        '[itemprop="description"]',
        'meta[property="og:description"]'
    ],
    'sku': [
        '.sku',
        '.product-sku',
        '[data-sku]',
        '[itemprop="sku"]',
        'meta[property="product:retailer_item_id"]'
    ]
}


class AdaptiveRetryEngine:
    """
    Adaptive retry engine that learns from failures.

    Automatically adjusts retry parameters, delays, timeouts based on
    observed failure patterns. Triggers selector fallbacks and re-discovery
    when needed.

    Usage:
        metrics = ScrapeMetrics()
        adaptive = AdaptiveRetryEngine(metrics)

        # After a failure
        adaptive.learn_from_failure('vendor1', 'RATE_LIMIT', {'delay_ms': 2000})

        # Get retry params for next attempt
        params = adaptive.get_retry_params('vendor1', attempt=2)
    """

    def __init__(self, metrics: ScrapeMetrics):
        """
        Initialize adaptive engine.

        Args:
            metrics: ScrapeMetrics instance for failure analysis
        """
        self.metrics = metrics

        # Per-vendor learned parameters
        self._vendor_params: dict[str, LearnedParams] = defaultdict(LearnedParams)

        # Successful fallback selectors (learn which work)
        self._successful_fallbacks: dict[str, dict[str, str]] = defaultdict(dict)

    def learn_from_failure(
        self,
        vendor_name: str,
        failure_reason: str,
        current_params: Optional[dict] = None
    ) -> None:
        """
        Learn from a scraping failure and adjust parameters.

        Args:
            vendor_name: Vendor identifier
            failure_reason: Categorized failure reason
            current_params: Current retry parameters used
        """
        params = self._vendor_params[vendor_name]
        current_params = current_params or {}

        # Track recent failure
        params.recent_failures.append(failure_reason)

        # Adapt based on failure type
        if failure_reason == FailureReason.RATE_LIMIT.value:
            # Increase delay by 50%, max 30s
            new_delay = int(params.delay_ms * 1.5)
            params.delay_ms = min(new_delay, 30000)
            logger.info(f"{vendor_name}: Rate limited, increasing delay to {params.delay_ms}ms")

        elif failure_reason == FailureReason.TIMEOUT.value:
            # Increase timeout by 25%, max 120s
            new_timeout = int(params.timeout_ms * 1.25)
            params.timeout_ms = min(new_timeout, 120000)
            logger.info(f"{vendor_name}: Timeout, increasing to {params.timeout_ms}ms")

        elif failure_reason == FailureReason.SELECTOR_FAILED.value:
            # Track selector failures
            params.selector_failures += 1
            logger.warning(
                f"{vendor_name}: Selector failed "
                f"({params.selector_failures} times)"
            )

        elif failure_reason == FailureReason.NETWORK_ERROR.value:
            # Increase retry attempts for network issues
            params.max_attempts = min(params.max_attempts + 1, 5)
            logger.info(f"{vendor_name}: Network error, max attempts now {params.max_attempts}")

        # Store updated params
        self._vendor_params[vendor_name] = params

    def get_retry_params(
        self,
        vendor_name: str,
        attempt_number: int = 1
    ) -> RetryParams:
        """
        Get retry parameters for an attempt.

        Args:
            vendor_name: Vendor identifier
            attempt_number: Current attempt number

        Returns:
            RetryParams with learned or default values
        """
        params = self._vendor_params.get(vendor_name, LearnedParams())

        # Calculate backoff delay
        delay = self._calculate_backoff(params.delay_ms, attempt_number)

        # Determine if fallback selectors should be used
        use_fallback = params.selector_failures >= 3

        return RetryParams(
            delay_ms=delay,
            timeout_ms=params.timeout_ms,
            max_attempts=params.max_attempts,
            use_fallback_selectors=use_fallback
        )

    def should_trigger_rediscovery(self, vendor_name: str) -> bool:
        """
        Check if vendor config needs re-discovery.

        Re-discovery is triggered when:
        - Selector failures exceed threshold (>5 in last 10 attempts)
        - Overall success rate < 50%

        Args:
            vendor_name: Vendor identifier

        Returns:
            True if re-discovery should be triggered
        """
        params = self._vendor_params.get(vendor_name)
        if not params:
            return False

        # Check selector failure count
        recent_selector_failures = sum(
            1 for f in params.recent_failures
            if f == FailureReason.SELECTOR_FAILED.value
        )

        if recent_selector_failures > 5:
            logger.warning(
                f"{vendor_name}: {recent_selector_failures}/10 recent attempts "
                "failed with SELECTOR_FAILED - rediscovery recommended"
            )
            return True

        # Check success rate
        success_rate = self.metrics.get_success_rate(vendor_name)
        if success_rate < 0.5:
            logger.warning(
                f"{vendor_name}: Success rate {success_rate:.1%} < 50% - "
                "rediscovery recommended"
            )
            return True

        return False

    def get_fallback_selector_chain(
        self,
        vendor_name: str,
        selector_type: str,
        primary_selector: Optional[str] = None
    ) -> list[str]:
        """
        Get fallback selector chain for a field.

        Returns primary selector (if provided) followed by common fallbacks.
        Learns which fallbacks work and prioritizes them.

        Args:
            vendor_name: Vendor identifier
            selector_type: Field type (title, images, price, etc.)
            primary_selector: Primary selector from config

        Returns:
            List of selectors to try in order
        """
        chain = []

        # Add primary selector first
        if primary_selector:
            chain.append(primary_selector)

        # Check if we learned a successful fallback for this vendor/field
        if vendor_name in self._successful_fallbacks:
            successful = self._successful_fallbacks[vendor_name].get(selector_type)
            if successful and successful not in chain:
                # Prioritize learned successful fallback
                chain.append(successful)

        # Add common fallbacks
        fallbacks = FALLBACK_SELECTORS.get(selector_type, [])
        for fallback in fallbacks:
            if fallback not in chain:
                chain.append(fallback)

        return chain

    def record_successful_fallback(
        self,
        vendor_name: str,
        selector_type: str,
        selector: str
    ) -> None:
        """
        Record that a fallback selector worked.

        This allows the engine to learn which fallbacks are effective
        for specific vendors.

        Args:
            vendor_name: Vendor identifier
            selector_type: Field type
            selector: Selector that worked
        """
        self._successful_fallbacks[vendor_name][selector_type] = selector
        logger.info(f"{vendor_name}: Learned fallback for {selector_type}: {selector}")

    def reset_vendor_learning(self, vendor_name: str) -> None:
        """
        Clear learned parameters for a vendor.

        Called after vendor config is updated or re-discovered.

        Args:
            vendor_name: Vendor identifier
        """
        if vendor_name in self._vendor_params:
            del self._vendor_params[vendor_name]

        if vendor_name in self._successful_fallbacks:
            del self._successful_fallbacks[vendor_name]

        logger.info(f"{vendor_name}: Reset learned parameters")

    def _calculate_backoff(self, base_delay_ms: int, attempt: int) -> int:
        """
        Calculate exponential backoff with jitter.

        Args:
            base_delay_ms: Base delay in milliseconds
            attempt: Attempt number (1-indexed)

        Returns:
            Delay in milliseconds
        """
        # Exponential backoff: delay * (2 ^ (attempt - 1))
        backoff = base_delay_ms * (2 ** (attempt - 1))

        # Add jitter (±20%)
        jitter_range = int(backoff * 0.2)
        jitter = random.randint(-jitter_range, jitter_range)

        # Cap at 30 seconds
        return min(backoff + jitter, 30000)

    def get_learning_summary(self) -> dict[str, dict]:
        """
        Get summary of learned parameters for all vendors.

        Returns:
            Dict mapping vendor name to learned parameters
        """
        summary = {}
        for vendor, params in self._vendor_params.items():
            recent_failure_types = list(params.recent_failures)

            summary[vendor] = {
                'delay_ms': params.delay_ms,
                'timeout_ms': params.timeout_ms,
                'max_attempts': params.max_attempts,
                'selector_failures': params.selector_failures,
                'recent_failures': recent_failure_types,
                'needs_rediscovery': self.should_trigger_rediscovery(vendor),
                'learned_fallbacks': self._successful_fallbacks.get(vendor, {})
            }

        return summary
