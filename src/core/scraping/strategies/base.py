"""
Base Strategy Interface

All scraping strategies implement this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StrategyResult:
    """Result from a scraping strategy."""
    success: bool
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[str] = None
    images: list[str] = field(default_factory=list)
    sku_on_page: Optional[str] = None
    availability: Optional[str] = None

    # Metadata
    source_url: str = ""
    strategy_name: str = ""
    error: Optional[str] = None
    raw_html: Optional[str] = None  # For debugging


class BaseStrategy(ABC):
    """Abstract base class for scraping strategies."""

    name: str = "base"

    @abstractmethod
    async def scrape(
        self,
        url: str,
        selectors: dict,
        config: dict = None
    ) -> StrategyResult:
        """
        Scrape product data from URL.

        Args:
            url: Product page URL
            selectors: CSS selectors from vendor config
            config: Additional configuration (timing, etc.)

        Returns:
            StrategyResult with extracted data
        """
        pass

    @abstractmethod
    async def close(self):
        """Clean up resources."""
        pass
