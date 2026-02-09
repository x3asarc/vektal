"""Pydantic schemas for Products API."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from src.api.core.pagination import CursorPaginationParams

class ProductQuery(CursorPaginationParams):
    """Query parameters for product list."""
    vendor: Optional[str] = Field(default=None, description="Filter by vendor code")
    status: Optional[str] = Field(default=None, description="Filter by status")

class ProductResponse(BaseModel):
    """Single product response."""
    id: int
    sku: str
    barcode: Optional[str] = None
    title: Optional[str] = None
    vendor_id: Optional[int] = None
    vendor_code: Optional[str] = None
    shopify_product_id: Optional[str] = None
    price: Optional[float] = None
    compare_at_price: Optional[float] = None
    weight_grams: Optional[float] = None
    status: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True

class ProductListResponse(BaseModel):
    """Paginated product list response."""
    products: List[ProductResponse]
    pagination: dict  # Contains next_cursor, has_next, limit

class ProductCreateRequest(BaseModel):
    """Request to create a new product."""
    sku: str = Field(min_length=1, max_length=100)
    barcode: Optional[str] = Field(default=None, max_length=50)
    title: Optional[str] = Field(default=None, max_length=255)
    vendor_id: Optional[int] = None
    price: Optional[float] = Field(default=None, ge=0)
