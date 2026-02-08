"""
Product and enrichment models.

Product: Core Shopify product data
ProductEnrichment: AI-generated SEO and attributes (separate table, can be regenerated)
ProductImage: Product images with vision analysis metadata
"""
from sqlalchemy import (
    String, Integer, Text, ForeignKey, Numeric, Boolean,
    BigInteger, JSON, ARRAY
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from src.models import db, TimestampMixin


class Product(db.Model, TimestampMixin):
    """
    Core Shopify product data.

    Stores product information synced with Shopify store.
    One-to-one with ProductEnrichment for AI-generated data.
    """
    __tablename__ = 'products'

    id = db.Column(Integer, primary_key=True)
    store_id = db.Column(
        Integer,
        ForeignKey('shopify_stores.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # Shopify identifiers
    shopify_product_id = db.Column(BigInteger, index=True)  # From Shopify API
    shopify_variant_id = db.Column(BigInteger, index=True)

    # Product identification
    title = db.Column(String(512), nullable=False)
    sku = db.Column(String(255), index=True)
    barcode = db.Column(String(255), index=True)
    vendor_code = db.Column(String(50))  # Reference to vendor.code

    # Core data
    description = db.Column(Text)
    product_type = db.Column(String(255))
    tags = db.Column(PG_ARRAY(String(100)))  # PostgreSQL array

    # Pricing
    price = db.Column(Numeric(10, 2))
    compare_at_price = db.Column(Numeric(10, 2))
    cost = db.Column(Numeric(10, 2))
    currency = db.Column(String(3), default='USD')

    # Physical properties
    weight_kg = db.Column(Numeric(10, 3))
    weight_unit = db.Column(String(10), default='kg')

    # Customs / HS code
    hs_code = db.Column(String(20))
    country_of_origin = db.Column(String(2))  # ISO 3166-1 alpha-2

    # Sync tracking
    last_synced_at = db.Column(db.DateTime(timezone=True))
    sync_status = db.Column(String(50), default='pending')  # pending, synced, error
    sync_error = db.Column(Text)

    # Status
    is_active = db.Column(Boolean, default=True, nullable=False)
    is_published = db.Column(Boolean, default=False, nullable=False)

    # Relationships
    store = relationship('ShopifyStore', back_populates='products')

    enrichment = relationship(
        'ProductEnrichment',
        back_populates='product',
        uselist=False,  # One-to-one
        cascade='all, delete-orphan'
    )

    images = relationship(
        'ProductImage',
        back_populates='product',
        cascade='all, delete-orphan',
        order_by='ProductImage.position'
    )

    def __repr__(self):
        return f'<Product {self.sku} store_id={self.store_id}>'


class ProductEnrichment(db.Model, TimestampMixin):
    """
    AI-generated product enrichment data.

    Separate table from Product - can be regenerated independently.
    Stores SEO optimizations, AI-extracted attributes, quality scores.
    """
    __tablename__ = 'product_enrichments'

    id = db.Column(Integer, primary_key=True)
    product_id = db.Column(
        Integer,
        ForeignKey('products.id', ondelete='CASCADE'),
        unique=True,  # One-to-one
        nullable=False,
        index=True
    )

    # SEO optimization
    seo_title = db.Column(String(512))
    seo_description = db.Column(Text)
    seo_keywords = db.Column(PG_ARRAY(String(100)))

    # AI-extracted attributes
    colors = db.Column(PG_ARRAY(String(50)))
    materials = db.Column(PG_ARRAY(String(100)))
    dimensions = db.Column(String(255))
    features = db.Column(PG_ARRAY(String(255)))

    # Quality assessment
    quality_score = db.Column(Numeric(3, 2))  # 0.00 to 1.00
    quality_issues = db.Column(JSON)  # List of identified issues

    # Vision analysis summary
    vision_summary = db.Column(Text)

    # Embeddings for semantic search (optional)
    title_embedding = db.Column(PG_ARRAY(Numeric))  # Vector for semantic search
    description_embedding = db.Column(PG_ARRAY(Numeric))

    # Generation metadata
    generated_by = db.Column(String(50))  # e.g., 'claude-3-opus', 'gpt-4-vision'
    generation_version = db.Column(String(20))  # Version tag for regeneration tracking

    # Relationships
    product = relationship('Product', back_populates='enrichment')

    def __repr__(self):
        return f'<ProductEnrichment product_id={self.product_id} quality={self.quality_score}>'


class ProductImage(db.Model, TimestampMixin):
    """
    Product image with vision analysis metadata.

    Stores image URLs and vision API analysis results.
    """
    __tablename__ = 'product_images'

    id = db.Column(Integer, primary_key=True)
    product_id = db.Column(
        Integer,
        ForeignKey('products.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # Image data
    src_url = db.Column(String(1024), nullable=False)
    alt_text = db.Column(String(512))
    position = db.Column(Integer, default=0)  # Display order

    # Vision analysis
    vision_analyzed = db.Column(Boolean, default=False)
    vision_labels = db.Column(PG_ARRAY(String(100)))  # Detected labels
    vision_colors = db.Column(PG_ARRAY(String(50)))  # Dominant colors
    vision_text = db.Column(Text)  # OCR extracted text
    vision_quality = db.Column(Numeric(3, 2))  # Image quality score

    # Status
    is_active = db.Column(Boolean, default=True, nullable=False)

    # Relationships
    product = relationship('Product', back_populates='images')

    def __repr__(self):
        return f'<ProductImage product_id={self.product_id} position={self.position}>'
