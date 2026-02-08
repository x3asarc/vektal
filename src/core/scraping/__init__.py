from .strategies.base import BaseStrategy, StrategyResult
from .strategies.playwright_strategy import PlaywrightStrategy
from .strategies.requests_strategy import RequestsStrategy

# UniversalScraper and ScrapeResult will be added in Task 3
# from .engine import UniversalScraper, ScrapeResult

__all__ = [
    "BaseStrategy",
    "StrategyResult",
    "PlaywrightStrategy",
    "RequestsStrategy"
]
