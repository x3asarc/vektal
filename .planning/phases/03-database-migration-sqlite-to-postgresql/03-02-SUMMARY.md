---
phase: 03-database-migration-sqlite-to-postgresql
plan: 02
subsystem: database-models
tags: [sqlalchemy, orm, models, postgresql, encryption, multi-tenant]
requires:
  - phase: 03-database-migration-sqlite-to-postgresql
    plan: 01
    feature: Flask-SQLAlchemy instance and TimestampMixin
  - phase: 02-docker-infrastructure-foundation
    feature: Encryption module for token security
provides:
  - User model with authentication and tier management
  - ShopifyStore model with encrypted OAuth token storage
  - Vendor and VendorCatalogItem models for supplier catalogs
  - Product, ProductEnrichment, ProductImage models for product data
  - Job and JobResult models for background task tracking
  - Complete ORM layer for multi-tenant platform
affects:
  - phase: 03-database-migration-sqlite-to-postgresql
    plan: 03
    why: Migration files will be generated from these model definitions
  - phase: 03-database-migration-sqlite-to-postgresql
    plan: 04+
    why: All database operations will use these models
tech-stack:
  added: []
  patterns:
    - Tenant isolation via user_id foreign keys on all user-owned resources
    - One-to-one User-ShopifyStore relationship (v1.0)
    - Separate ProductEnrichment table for regenerable AI data
    - Deferred imports to avoid circular dependencies
    - PostgreSQL ARRAY types for tags, embeddings, and multi-value fields
    - Composite indexes for fast catalog lookups
key-files:
  created:
    - src/models/user.py
    - src/models/shopify.py
    - src/models/vendor.py
    - src/models/product.py
    - src/models/job.py
  modified:
    - src/models/__init__.py
decisions:
  - title: "Separate ProductEnrichment table"
    rationale: "AI-generated SEO and attributes can be regenerated independently without affecting core product data. Enables batch re-enrichment without touching synced Shopify data."
    phase: "03-02"
    date: "2026-02-08"
  - title: "Deferred imports for encryption"
    rationale: "ShopifyStore methods use 'from src.core.encryption import' inside methods to avoid circular dependency between models and core modules."
    phase: "03-02"
    date: "2026-02-08"
  - title: "PostgreSQL ARRAY types"
    rationale: "Native array support for tags, colors, materials, embeddings eliminates need for junction tables. Simpler queries, better performance for multi-value fields."
    phase: "03-02"
    date: "2026-02-08"
  - title: "Composite index on VendorCatalogItem"
    rationale: "Index on (vendor_id, sku, barcode) enables fast catalog lookups during product matching. Critical for performance when searching vendor catalogs."
    phase: "03-02"
    date: "2026-02-08"
  - title: "One-to-one User-ShopifyStore"
    rationale: "v1.0 requirement per 03-CONTEXT.md. unique=True on ShopifyStore.user_id enforces at database level. Multi-store support deferred to v2.0."
    phase: "03-02"
    date: "2026-02-08"
metrics:
  duration: 5 minutes
  tasks: 3
  commits: 3
  files_created: 5
  files_modified: 1
completed: 2026-02-08
---

# Phase 3 Plan 02: SQLAlchemy ORM Models Summary

**One-liner:** Multi-tenant ORM models with encrypted Shopify tokens, separate enrichment table, PostgreSQL arrays, and composite vendor catalog indexes

## What Was Built

Created complete SQLAlchemy ORM models for the production database schema. Defines User, ShopifyStore, Vendor, Product, and Job models with proper relationships, indexes, and tenant isolation. Replaces temporary SQLite schema with production-ready relational design supporting multi-user platform.

### Task Breakdown

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create User and ShopifyStore models | 8fe771e | src/models/user.py, src/models/shopify.py |
| 2 | Create Vendor and VendorCatalogItem models | be345de | src/models/vendor.py |
| 3 | Create Product, ProductEnrichment, ProductImage, and Job models | a5151c1 | src/models/product.py, src/models/job.py, src/models/__init__.py |

### Key Components

**1. User Model (src/models/user.py)**
- Authentication: email (unique, indexed), password_hash
- Subscription tier: FREE, PRO, ENTERPRISE (enum, indexed)
- One-to-one relationship with ShopifyStore (v1.0 requirement)
- One-to-many relationships with Vendors and Jobs
- TimestampMixin for created_at/updated_at

**2. ShopifyStore Model (src/models/shopify.py)**
- One-to-one with User (unique user_id foreign key)
- Encrypted OAuth token storage (LargeBinary field)
- set_access_token() and get_access_token() methods with deferred imports
- shop_domain (unique, indexed) and shop_name
- is_active flag for store status
- One-to-many relationship with Products

**3. ShopifyCredential Model (src/models/shopify.py)**
- Additional API keys and secrets per store
- credential_type (e.g., 'api_key', 'webhook_secret', 'storefront_token')
- Encrypted credential_value_encrypted field
- set_credential() and get_credential() methods
- Many-to-one relationship with ShopifyStore

**4. Vendor Model (src/models/vendor.py)**
- User-owned vendor (supplier) configuration
- name, code (unique per user), website_url
- config_file reference to YAML configuration
- Catalog metadata: last_updated, item_count, source
- One-to-many relationship with VendorCatalogItem
- Composite unique constraint: (user_id, code)

**5. VendorCatalogItem Model (src/models/vendor.py)**
- Parsed vendor catalog for fast SQL searching
- Product identifiers: sku, barcode, vendor_product_id (all indexed)
- Sparse product data: name, description, price, weight_kg, image_url
- raw_data JSON column for original vendor data
- Composite index: (vendor_id, sku, barcode) for fast lookups
- Cascade delete when vendor deleted

**6. Product Model (src/models/product.py)**
- Core Shopify product data synced with store
- Shopify identifiers: shopify_product_id, shopify_variant_id (indexed)
- Product identification: title, sku, barcode (indexed), vendor_code
- Core data: description, product_type, tags (PostgreSQL ARRAY)
- Pricing: price, compare_at_price, cost, currency
- Physical: weight_kg, weight_unit
- Customs: hs_code, country_of_origin
- Sync tracking: last_synced_at, sync_status, sync_error
- One-to-one relationship with ProductEnrichment
- One-to-many relationship with ProductImage

**7. ProductEnrichment Model (src/models/product.py)**
- **Separate table from Product** - can be regenerated independently
- SEO optimization: seo_title, seo_description, seo_keywords (ARRAY)
- AI-extracted attributes: colors, materials, dimensions, features (ARRAYs)
- Quality assessment: quality_score (0.00-1.00), quality_issues (JSON)
- Vision analysis summary
- Embeddings: title_embedding, description_embedding (ARRAY of Numeric)
- Generation metadata: generated_by, generation_version

**8. ProductImage Model (src/models/product.py)**
- Product images with vision analysis
- src_url, alt_text, position (display order)
- Vision analysis: vision_analyzed flag, vision_labels, vision_colors, vision_text (OCR), vision_quality
- All vision fields use PostgreSQL ARRAY types

**9. Job Model (src/models/job.py)**
- Background job tracking for Celery tasks
- celery_task_id (unique, indexed)
- job_type enum: PRODUCT_SYNC, PRODUCT_ENRICH, IMAGE_PROCESS, CATALOG_IMPORT, VENDOR_SCRAPE
- status enum: PENDING, RUNNING, COMPLETED, FAILED, CANCELLED
- Progress tracking: total_items, processed_items, successful_items, failed_items
- Timing: started_at, completed_at
- Error tracking: error_message, error_traceback
- parameters JSON for retry/debugging
- progress_percent property (calculated)
- One-to-many relationship with JobResult

**10. JobResult Model (src/models/job.py)**
- Per-item results for bulk operations
- Item identification: item_sku, item_barcode, item_identifier
- Result: status (success/error/skipped), product_id (foreign key)
- Error tracking: error_message
- Review flags: needs_review, review_reason
- result_data JSON for flexible result storage

**11. Models Registry (src/models/__init__.py)**
- All models imported for Alembic migration detection
- Exports: User, UserTier, ShopifyStore, ShopifyCredential, Vendor, VendorCatalogItem, Product, ProductEnrichment, ProductImage, Job, JobResult, JobStatus, JobType

## Decisions Made

### 1. Separate ProductEnrichment Table
**Decision:** ProductEnrichment as separate table with one-to-one relationship to Product
**Rationale:**
- AI-generated SEO and attributes can be regenerated without affecting core product data
- Enables batch re-enrichment operations without touching synced Shopify data
- Clearer separation of concerns: Product = Shopify source of truth, ProductEnrichment = AI-generated
- Allows versioning of enrichment algorithms via generation_version field

### 2. Deferred Imports for Encryption
**Decision:** Import encryption functions inside methods, not at module level
**Rationale:**
- Avoids circular dependency: models → encryption → database → models
- ShopifyStore.set_access_token() and get_access_token() import from src.core.encryption inside methods
- Encryption module can safely import db instance without circular import
- Pattern: `from src.core.encryption import encrypt_token` inside method body

### 3. PostgreSQL ARRAY Types
**Decision:** Use native PostgreSQL ARRAY for tags, colors, materials, embeddings, etc.
**Rationale:**
- Eliminates junction tables for simple multi-value fields
- Simpler queries: `WHERE 'red' = ANY(colors)` vs JOIN through junction table
- Better performance for read-heavy operations
- Native PostgreSQL indexing support (GIN indexes)
- Embedding vectors stored as ARRAY(Numeric) for semantic search

### 4. Composite Index on VendorCatalogItem
**Decision:** Index on (vendor_id, sku, barcode) for catalog lookups
**Rationale:**
- Product matching searches vendor catalogs by SKU or barcode
- Single index covers both lookup patterns
- Critical for performance when vendor catalogs have 10k+ items
- Also added separate indexes on (vendor_id, sku) and (vendor_id, barcode) for single-field lookups

### 5. One-to-One User-ShopifyStore
**Decision:** unique=True on ShopifyStore.user_id, uselist=False in relationship
**Rationale:**
- v1.0 requirement per 03-CONTEXT.md: "Single Shopify store per user"
- Database enforces constraint (cannot create two stores for one user)
- Multi-store support deferred to v2.0
- Simplifies v1.0 implementation (no store selection logic needed)

### 6. Tenant Isolation via user_id
**Decision:** All user-owned resources have user_id foreign key
**Rationale:**
- Clear multi-tenant isolation at database level
- Easy to query all resources for a user
- Prevents accidental cross-tenant data access
- Enables efficient data deletion when user deleted (cascade)

### 7. Cascade Deletes for Child Records
**Decision:** cascade='all, delete-orphan' on all parent-child relationships
**Rationale:**
- When User deleted, all ShopifyStores, Vendors, Jobs automatically deleted
- When Vendor deleted, all VendorCatalogItems deleted
- When Product deleted, ProductEnrichment and ProductImages deleted
- Prevents orphaned records, simplifies cleanup logic
- Database integrity maintained automatically

## Verification Results

All success criteria met:

✓ User, ShopifyStore, ShopifyCredential models with one-to-one relationship
✓ ShopifyStore.set_access_token() and get_access_token() methods exist with deferred import
✓ Vendor, VendorCatalogItem with composite index for fast lookup
✓ Product, ProductEnrichment (separate table), ProductImage models
✓ Job, JobResult models for background task tracking
✓ All models registered in src/models/__init__.py
✓ `python -c "from src.models import *"` runs without error

## Deviations from Plan

None - plan executed exactly as written.

## Integration Points

**Depends on:**
- Plan 01: SQLAlchemy db instance and TimestampMixin from src/models/__init__.py
- Phase 2: Encryption module (src/core/encryption.py) for token encryption/decryption

**Provides for:**
- Plan 03: Alembic will generate migrations from these model definitions
- Plan 04+: All database operations will use these ORM models
- Future phases: Complete data model for multi-tenant platform

**Files created:**
- `src/models/user.py` - User model with authentication and tier
- `src/models/shopify.py` - ShopifyStore and ShopifyCredential models
- `src/models/vendor.py` - Vendor and VendorCatalogItem models
- `src/models/product.py` - Product, ProductEnrichment, ProductImage models
- `src/models/job.py` - Job and JobResult models

**Files modified:**
- `src/models/__init__.py` - Import and export all models

## Next Phase Readiness

**Ready for Plan 03 (Alembic Migrations):**
- All models defined and importable
- Relationships configured with proper foreign keys
- Indexes specified for performance-critical queries
- Naming convention in place for constraint generation

**Blockers:** None

**Concerns:**
- Encryption module (src/core/encryption.py) needs to exist for token encryption/decryption
- Will verify in Plan 03 or create if missing

## Technical Notes

### Model Inheritance Pattern
All models inherit from both `db.Model` and `TimestampMixin`:
```python
class Product(db.Model, TimestampMixin):
    __tablename__ = 'products'
    # created_at and updated_at added automatically
```

### Encryption Methods Pattern
Deferred imports to avoid circular dependencies:
```python
def set_access_token(self, plaintext_token: str) -> None:
    from src.core.encryption import encrypt_token  # Import inside method
    self.access_token_encrypted = encrypt_token(plaintext_token)
```

### PostgreSQL ARRAY Usage
```python
tags = db.Column(PG_ARRAY(String(100)))  # Array of strings
embedding = db.Column(PG_ARRAY(Numeric))  # Array of numbers for vectors
```

### Tenant Isolation Pattern
All user-owned resources:
```python
user_id = db.Column(
    Integer,
    ForeignKey('users.id', ondelete='CASCADE'),
    nullable=False,
    index=True  # For efficient filtering
)
```

### Composite Index for Performance
```python
__table_args__ = (
    Index('ix_vendor_catalog_lookup', 'vendor_id', 'sku', 'barcode'),
)
```

### Job Progress Calculation
```python
@property
def progress_percent(self) -> float:
    if self.total_items == 0:
        return 0.0
    return (self.processed_items / self.total_items) * 100
```

## Performance Metrics

- **Execution time:** 5 minutes
- **Tasks completed:** 3/3
- **Commits:** 3 (1 per task)
- **Files created:** 5
- **Files modified:** 1
- **Models created:** 10 (User, ShopifyStore, ShopifyCredential, Vendor, VendorCatalogItem, Product, ProductEnrichment, ProductImage, Job, JobResult)
- **Relationships configured:** 12 (one-to-one, one-to-many, many-to-one)
- **Indexes created:** 20+ (individual and composite)

---

**Phase:** 03-database-migration-sqlite-to-postgresql
**Plan:** 02
**Status:** ✅ Complete
**Date:** 2026-02-08
