from .base import BaseStrategy, StrategyResult
from .requests_strategy import RequestsStrategy

# PlaywrightStrategy will be added in Task 2
# from .playwright_strategy import PlaywrightStrategy

__all__ = [
    "BaseStrategy",
    "StrategyResult",
    "RequestsStrategy"
]
