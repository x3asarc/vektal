"""
Store Profile Schema

Pydantic models for store profile validation and serialization.
Represents the intelligence extracted from Shopify catalogs.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class KnownVendor(BaseModel):
    """Known vendor in the store catalog."""
    name: str = Field(description="Vendor name from Shopify products")
    sku_pattern: Optional[str] = Field(
        default=None,
        description="Regex pattern for vendor's SKU format"
    )
    product_count: int = Field(default=0, description="Number of products from this vendor")
    last_scrape: Optional[datetime] = Field(default=None, description="Last scrape timestamp")


class CatalogStats(BaseModel):
    """Statistics about the existing catalog."""
    total_products: int = Field(default=0, description="Total products in catalog")
    total_vendors: int = Field(default=0, description="Total unique vendors")
    avg_products_per_vendor: float = Field(default=0, description="Average products per vendor")
    most_common_categories: dict[str, int] = Field(
        default_factory=dict,
        description="Product type distribution"
    )


class DiscoverySettings(BaseModel):
    """Settings for vendor discovery behavior."""
    require_confirmation_if_confidence_below: float = Field(
        default=0.70,
        description="Require user confirmation if vendor confidence below this threshold"
    )
    reject_vendor_if_niche_mismatch: bool = Field(
        default=True,
        description="Automatically reject vendors that don't match store niche"
    )
    allow_cross_niche_products: bool = Field(
        default=False,
        description="Allow products from adjacent niches"
    )


class StoreProfile(BaseModel):
    """
    Store intelligence profile extracted from Shopify catalog.

    Follows catalog-first approach:
    - 50+ products: High confidence, catalog is source of truth
    - 10-49 products: Medium confidence, hybrid approach
    - <10 products: Low confidence, questionnaire needed
    """

    # Identity
    store_id: str = Field(description="Shopify store identifier (e.g., shop.myshopify.com)")
    created: datetime = Field(default_factory=datetime.utcnow, description="Profile creation timestamp")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

    # Niche intelligence
    niche_primary: str = Field(description="Primary niche (e.g., arts_and_crafts)")
    niche_sub_niches: list[str] = Field(
        default_factory=list,
        description="Sub-niches detected (e.g., decoupage, scrapbooking)"
    )
    niche_confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence in niche detection (0.0-1.0)"
    )

    # Store characteristics
    language: str = Field(default="de", description="Primary language code")
    country: str = Field(default="AT", description="Primary country code")
    vendor_scope: str = Field(
        default="focused",
        description="Vendor strategy: focused | flexible | multi_category"
    )
    keywords: list[str] = Field(
        default_factory=list,
        description="Top keywords extracted from catalog"
    )

    # Vendor intelligence
    known_vendors: list[KnownVendor] = Field(
        default_factory=list,
        description="Vendors identified in catalog"
    )

    # Catalog analysis
    catalog_stats: CatalogStats = Field(
        default_factory=CatalogStats,
        description="Catalog statistics"
    )
    discovery_settings: DiscoverySettings = Field(
        default_factory=DiscoverySettings,
        description="Discovery behavior settings"
    )

    # Content framework (learned from catalog for high-confidence stores)
    content_framework: Optional[dict] = Field(
        default=None,
        description="Content patterns learned from catalog (title/description templates)"
    )

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )
