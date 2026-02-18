"""Pydantic schemas for Vendors API."""
from pydantic import BaseModel, Field
from typing import Optional, List

class VendorResponse(BaseModel):
    """Single vendor response."""
    id: int
    code: str
    name: str
    website_url: Optional[str] = None
    country: Optional[str] = None
    is_active: bool = True
    product_count: int = 0
    catalog_item_count: int = 0
    created_at: Optional[str] = None

    class Config:
        from_attributes = True

class VendorListResponse(BaseModel):
    """Vendor list response."""
    vendors: List[VendorResponse]
    total: int

class VendorDetailResponse(BaseModel):
    """Detailed vendor response with config."""
    id: int
    code: str
    name: str
    website_url: Optional[str] = None
    country: Optional[str] = None
    is_active: bool
    scraping_config: Optional[dict] = None
    product_count: int = 0
    catalog_item_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class VendorFieldMappingResponse(BaseModel):
    id: int
    store_id: int
    vendor_code: str
    field_group: str
    mapping_version: int
    coverage_status: str
    required_fields: list[str] = Field(default_factory=list)
    canonical_mapping: dict = Field(default_factory=dict)
    is_active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class VendorFieldMappingListResponse(BaseModel):
    mappings: List[VendorFieldMappingResponse]
    total: int
