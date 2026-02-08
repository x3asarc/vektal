from .strategies.base import BaseStrategy, StrategyResult
from .strategies.requests_strategy import RequestsStrategy

# These will be added in later tasks
# from .engine import UniversalScraper, ScrapeResult
# from .strategies.playwright_strategy import PlaywrightStrategy

__all__ = [
    "BaseStrategy",
    "StrategyResult",
    "RequestsStrategy"
]
