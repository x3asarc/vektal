"""
Vendor Schema

Pydantic models for vendor configuration validation.
"""

from pydantic import BaseModel, Field
from typing import Optional


class SKUPattern(BaseModel):
    """SKU pattern configuration."""
    regex: str = Field(description="Regex pattern for SKU matching")
    description: str = Field(default="", description="Human-readable description")
    examples: list[str] = Field(default_factory=list, description="Example SKUs")
    confidence_boost: float = Field(default=0.0, description="Confidence boost for this pattern")


class VendorInfo(BaseModel):
    """Basic vendor information."""
    name: str = Field(description="Vendor display name")
    slug: str = Field(description="Vendor identifier (lowercase, no spaces)")
    domain: str = Field(description="Vendor website domain")
    country_of_origin: str = Field(default="SI", description="Country code")


class VendorURLs(BaseModel):
    """URL templates for vendor site."""
    product_template: Optional[str] = Field(default=None, description="Product page URL template")
    search_template: Optional[str] = Field(default=None, description="Search URL template")
    collection_pages: list[str] = Field(default_factory=list, description="Collection page URLs")


class ScrapingConfig(BaseModel):
    """Scraping strategy configuration."""
    primary: str = Field(default="playwright", description="Primary scraping strategy")
    fallback: str = Field(default="selenium", description="Fallback strategy")
    discovery: str = Field(default="firecrawl", description="Discovery strategy")
    enabled: bool = Field(default=True, description="Whether scraping is enabled")


class VendorConfig(BaseModel):
    """Complete vendor configuration."""
    vendor: VendorInfo = Field(description="Vendor identity")
    sku_patterns: list[SKUPattern] = Field(default_factory=list, description="SKU patterns")
    urls: Optional[VendorURLs] = Field(default=None, description="URL templates")
    scraping: Optional[ScrapingConfig] = Field(default=None, description="Scraping config")
    niche: str = Field(default="general", description="Vendor niche")
    version: str = Field(default="1.0", description="Config version")
