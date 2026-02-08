from .engine import UniversalScraper, ScrapeResult, BatchResult
from .strategies.base import BaseStrategy, StrategyResult
from .strategies.playwright_strategy import PlaywrightStrategy
from .strategies.requests_strategy import RequestsStrategy
from .metrics import ScrapeMetrics, FailureReason
from .adaptive import AdaptiveRetryEngine, RetryParams

__all__ = [
    "UniversalScraper",
    "ScrapeResult",
    "BatchResult",
    "BaseStrategy",
    "StrategyResult",
    "PlaywrightStrategy",
    "RequestsStrategy",
    "ScrapeMetrics",
    "FailureReason",
    "AdaptiveRetryEngine",
    "RetryParams"
]
