"""
Vendor and catalog models.

Vendor: User's supplier configuration
VendorCatalogItem: Parsed CSV data for fast SQL searching
"""
from sqlalchemy import String, Integer, Text, ForeignKey, Numeric, Index, JSON, Boolean
from sqlalchemy.orm import relationship
from src.models import db, TimestampMixin


class Vendor(db.Model, TimestampMixin):
    """
    Vendor (supplier) configuration for a user.

    Each vendor has:
    - Scraping configuration (config_file reference)
    - Catalog of items parsed from CSV/API
    - Metadata about catalog freshness
    """
    __tablename__ = 'vendors'

    id = db.Column(Integer, primary_key=True)
    user_id = db.Column(
        Integer,
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # Vendor identification
    name = db.Column(String(255), nullable=False)
    code = db.Column(String(50), nullable=False)  # Unique per user, e.g., 'pentart', 'galaxyflakes'
    website_url = db.Column(String(512))

    # Configuration
    config_file = db.Column(String(255))  # Path to vendor YAML in config/vendors/

    # Catalog metadata
    catalog_last_updated = db.Column(db.DateTime(timezone=True))
    catalog_item_count = db.Column(Integer, default=0)
    catalog_source = db.Column(String(255))  # File path or API endpoint

    # Status
    is_active = db.Column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship('User', back_populates='vendors')

    catalog_items = relationship(
        'VendorCatalogItem',
        back_populates='vendor',
        cascade='all, delete-orphan',
        lazy='dynamic',
        order_by='VendorCatalogItem.sku'
    )

    # Composite unique constraint: one vendor code per user
    __table_args__ = (
        db.UniqueConstraint('user_id', 'code', name='uq_vendor_user_code'),
        Index('ix_vendor_user_active', 'user_id', 'is_active'),
    )

    def __repr__(self):
        return f'<Vendor {self.code} user_id={self.user_id} items={self.catalog_item_count}>'


class VendorCatalogItem(db.Model, TimestampMixin):
    """
    Parsed vendor catalog item for fast SQL searching.

    Stores sparse product data extracted from CSV/API:
    - SKU, barcode for matching
    - Name, description, price for reference
    - raw_data JSON for original vendor data

    Per CONTEXT.md: VendorCatalogItem stores parsed CSV data for fast SQL searching.
    """
    __tablename__ = 'vendor_catalog_items'

    id = db.Column(Integer, primary_key=True)
    vendor_id = db.Column(
        Integer,
        ForeignKey('vendors.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # Product identifiers (for matching)
    sku = db.Column(String(255), index=True)
    barcode = db.Column(String(255), index=True)
    vendor_product_id = db.Column(String(255))  # Vendor's internal ID

    # Sparse product data
    name = db.Column(String(512))
    description = db.Column(Text)
    price = db.Column(Numeric(10, 2))  # Vendor's price
    currency = db.Column(String(3), default='USD')
    weight_kg = db.Column(Numeric(10, 3))

    # Image reference (if vendor provides)
    image_url = db.Column(String(1024))

    # Raw vendor data (original CSV row or API response)
    raw_data = db.Column(JSON)

    # Status
    is_active = db.Column(Boolean, default=True, nullable=False)

    # Relationships
    vendor = relationship('Vendor', back_populates='catalog_items')

    # Composite index for fast lookup by vendor + (sku OR barcode)
    __table_args__ = (
        Index('ix_vendor_catalog_lookup', 'vendor_id', 'sku', 'barcode'),
        Index('ix_vendor_catalog_sku', 'vendor_id', 'sku'),
        Index('ix_vendor_catalog_barcode', 'vendor_id', 'barcode'),
    )

    def __repr__(self):
        return f'<VendorCatalogItem vendor_id={self.vendor_id} sku={self.sku} barcode={self.barcode}>'
