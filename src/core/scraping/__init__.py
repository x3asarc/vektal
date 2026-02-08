from .engine import UniversalScraper, ScrapeResult
from .strategies.base import BaseStrategy, StrategyResult
from .strategies.playwright_strategy import PlaywrightStrategy
from .strategies.requests_strategy import RequestsStrategy
from .metrics import ScrapeMetrics, FailureReason

__all__ = [
    "UniversalScraper",
    "ScrapeResult",
    "BaseStrategy",
    "StrategyResult",
    "PlaywrightStrategy",
    "RequestsStrategy",
    "ScrapeMetrics",
    "FailureReason"
]
