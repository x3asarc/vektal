# Phase 3: Database Migration (SQLite to PostgreSQL) - Research

**Researched:** 2026-02-08
**Domain:** PostgreSQL setup, Flask-SQLAlchemy ORM, Alembic migrations, backup/recovery
**Confidence:** HIGH

## Summary

This phase establishes a production PostgreSQL database with a fresh schema designed from v1.0 requirements, not migrated from the temporary SQLite. The research confirms PostgreSQL 16 with Flask-SQLAlchemy 3.x and Flask-Migrate (Alembic) as the standard stack for Flask applications. Key decisions include using `psycopg` (v3) over `psycopg2` for better memory efficiency and async support, SQLAlchemy's built-in connection pooling with development-friendly settings (pool_size=5), and pg_dump with custom format and gzip compression for backups.

For backup and recovery, pg_dump with custom format (`-Fc`) and gzip compression provides the best balance of portability, restoration flexibility, and storage efficiency. Development backups should be stored locally with a simple shell script wrapper, deferring automated production backups to Phase 13. Schema versioning uses Flask-Migrate (Alembic wrapper) which provides `flask db migrate` commands and automatic batch mode for SQLite compatibility during local development.

**Primary recommendation:** Use PostgreSQL 16, Flask-SQLAlchemy 3.1+, Flask-Migrate 4.0+, and psycopg 3.x with development-friendly pool settings (pool_size=5, max_overflow=2). Implement pg_dump backups with custom format and gzip compression, stored locally during development.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PostgreSQL | 16 (already in docker-compose.yml) | Relational database | ACID compliance, JSONB support, mature Docker support, already configured |
| Flask-SQLAlchemy | 3.1+ | ORM integration | Official Flask extension, simplifies SQLAlchemy setup with Flask app context |
| Flask-Migrate | 4.0+ | Database migrations | Alembic wrapper with `flask db` commands, auto-enables batch mode and type comparison |
| psycopg | 3.2+ (psycopg3) | PostgreSQL driver | 4-5x more memory efficient than psycopg2, async support, better connection handling |
| SQLAlchemy | 2.0+ | ORM core | Type hints, modern Python, improved performance over 1.x |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| psycopg[binary] | 3.2+ | Pre-built psycopg3 | Development and Docker - no compilation needed |
| alembic | 1.13+ | Migration engine | Installed via Flask-Migrate, direct access for advanced operations |
| pg_dump/pg_restore | Included in postgres:16 | Backup/restore | Disaster recovery, database snapshots |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| psycopg (v3) | psycopg2-binary | psycopg2 has slightly faster per-query speed but psycopg3 is 4-5x more memory efficient and has async support |
| Flask-Migrate | Raw Alembic | More setup, but offers more control - Flask-Migrate sufficient for this project |
| Custom format backup | Plain SQL backup | Plain SQL larger, no selective restore, but more portable |

**Installation:**
```bash
pip install Flask-SQLAlchemy Flask-Migrate "psycopg[binary]"
```

**Connection String (psycopg3):**
```
postgresql+psycopg://user:password@host:5432/database
```

**Note:** The `+psycopg` dialect specifies psycopg3. For psycopg2, use `+psycopg2`.

## Architecture Patterns

### Recommended Project Structure
```
src/
├── models/              # SQLAlchemy models
│   ├── __init__.py     # Import all models, create db instance
│   ├── user.py         # User, UserPreference models
│   ├── vendor.py       # Vendor, VendorCatalogItem models
│   ├── product.py      # Product, ProductEnrichment, ProductImage models
│   ├── job.py          # Job, JobLog models
│   └── shopify.py      # ShopifyStore, ShopifyCredential models
├── migrations/          # Alembic migrations (created by flask db init)
│   ├── versions/       # Migration scripts
│   └── alembic.ini
└── app.py              # Flask app with db.init_app()
```

### Pattern 1: Application Factory with SQLAlchemy
**What:** Initialize SQLAlchemy and Migrate in application factory pattern.
**When to use:** Always - standard Flask pattern for testability and configuration.
**Example:**
```python
# Source: Flask-SQLAlchemy official docs + Flask-Migrate docs
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')

    # Development-friendly pool settings
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 5,           # Default, sufficient for dev
        'max_overflow': 2,        # Allow 2 extra connections
        'pool_pre_ping': True,    # Validate connections before use
        'pool_recycle': 1800,     # Recycle connections after 30 min
    }

    db.init_app(app)
    migrate.init_app(app, db)

    return app
```

### Pattern 2: Model Base with Naming Convention
**What:** Define base model with timestamp columns and naming convention for constraints.
**When to use:** All models - ensures consistent naming and audit timestamps.
**Example:**
```python
# Source: SQLAlchemy naming convention docs
from datetime import datetime, timezone
from sqlalchemy import MetaData

# Naming convention for auto-generated constraints
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)
db = SQLAlchemy(metadata=metadata)

class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
```

### Pattern 3: Tenant Isolation via Foreign Key
**What:** All user data references user_id foreign key for data isolation.
**When to use:** v1.0 with single database, single Shopify store per user.
**Example:**
```python
# Source: Multi-tenant design patterns (Crunchy Data, Logto)
class User(db.Model, TimestampMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)

    # Relationships
    shopify_store = db.relationship('ShopifyStore', backref='user', uselist=False)
    products = db.relationship('Product', backref='user', lazy='dynamic')
    jobs = db.relationship('Job', backref='user', lazy='dynamic')

class Product(db.Model, TimestampMixin):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    # ... product fields
```

### Pattern 4: Separate Enrichment Tables (Recommended)
**What:** Store product enrichment data (SEO, descriptions) in separate table, linked by product_id.
**When to use:** Product enrichment data that may be regenerated independently.
**Example:**
```python
# Product enrichment data in separate table
# Rationale: Enrichment may be regenerated without touching base product data
class Product(db.Model, TimestampMixin):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    shopify_product_id = db.Column(db.BigInteger, index=True)  # Shopify's ID
    sku = db.Column(db.String(100), index=True)
    barcode = db.Column(db.String(50), index=True)  # EAN/UPC
    title = db.Column(db.String(500))

    # Relationship to enrichment
    enrichment = db.relationship('ProductEnrichment', backref='product', uselist=False)

class ProductEnrichment(db.Model, TimestampMixin):
    __tablename__ = 'product_enrichments'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), unique=True, nullable=False)

    # SEO fields
    meta_title = db.Column(db.String(70))
    meta_description = db.Column(db.String(160))
    seo_keywords = db.Column(db.ARRAY(db.String))  # PostgreSQL array

    # Generated content
    description_html = db.Column(db.Text)
    tags = db.Column(db.ARRAY(db.String))

    # Source tracking
    enrichment_source = db.Column(db.String(50))  # 'vision_ai', 'web_scrape', 'manual'
    enrichment_version = db.Column(db.Integer, default=1)
```

### Anti-Patterns to Avoid
- **Using raw SQL in models:** Use SQLAlchemy ORM methods; raw SQL bypasses type safety and relationships.
- **Storing credentials unencrypted:** Shopify OAuth tokens must be encrypted at rest (use Fernet or similar).
- **Fat models:** Keep business logic in services, not models. Models should only define structure and relationships.
- **Missing indexes on foreign keys:** Always index foreign key columns for JOIN performance.
- **Using ORM for bulk inserts:** For large catalog imports (1000+ rows), use `session.bulk_insert_mappings()` or raw COPY.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Database migrations | SQL scripts checked into git | Flask-Migrate (Alembic) | Version control, rollback, team sync, auto-detection |
| Connection pooling | Custom connection manager | SQLAlchemy built-in pool | Thread-safe, battle-tested, configurable |
| Backup scripts | Complex pg_dump wrappers | Simple shell script with pg_dump -Fc | pg_dump handles consistency, compression, format |
| Data import from CSV | Custom CSV parser | pandas read_csv + SQLAlchemy bulk_insert | pandas handles encoding, types, edge cases |
| Encryption at rest | Custom AES implementation | cryptography.Fernet | Authenticated encryption, key rotation support |
| Query building | String concatenation | SQLAlchemy ORM or text() with bindparams | SQL injection prevention, type safety |

**Key insight:** Database tooling is mature. Flask-Migrate, SQLAlchemy, and pg_dump handle the complexity. Custom solutions introduce bugs and maintenance burden.

## Common Pitfalls

### Pitfall 1: Connection String Format for psycopg3
**What goes wrong:** App fails to connect with "No module named psycopg2" or wrong driver error.
**Why it happens:** Using `postgresql://` or `postgresql+psycopg2://` with psycopg3 installed.
**How to avoid:** Use `postgresql+psycopg://` for psycopg3 driver.
**Warning signs:** Import errors, "driver not found" messages.

### Pitfall 2: Pool Exhaustion in Multi-Service Setup
**What goes wrong:** "too many connections" error when backend + celery_worker both run.
**Why it happens:** Default pool_size=5 per service, PostgreSQL default max_connections=100.
**How to avoid:**
- Development: pool_size=5, max_overflow=2 per service (7 connections each, 14 total for 2 services)
- Monitor with `SELECT count(*) FROM pg_stat_activity;`
**Warning signs:** Intermittent connection errors, slow queries during peaks.

### Pitfall 3: Alembic Not Detecting Model Changes
**What goes wrong:** `flask db migrate` creates empty migration.
**Why it happens:** Models not imported before migration runs.
**How to avoid:** Import all models in `src/models/__init__.py` and ensure it's imported by app.
**Warning signs:** Empty migration files, schema out of sync with models.

### Pitfall 4: Binary vs Plain Backups for Restore
**What goes wrong:** `psql < backup.sql` fails with encoding or permission errors.
**Why it happens:** Mixing pg_dump formats with wrong restore command.
**How to avoid:**
- Custom format (`-Fc`): restore with `pg_restore -d dbname backup.dump`
- Plain format (`-Fp`): restore with `psql dbname < backup.sql`
**Warning signs:** Restore errors, partial data recovery.

### Pitfall 5: Forgetting to Run Migrations in Docker
**What goes wrong:** App starts but crashes with "relation does not exist" errors.
**Why it happens:** Container starts before migrations run.
**How to avoid:** Run migrations as entrypoint or startup command:
```dockerfile
CMD flask db upgrade && gunicorn ...
```
Or use a dedicated migration container in docker-compose.
**Warning signs:** Immediate crashes after docker compose up.

### Pitfall 6: Losing Encrypted Credentials During Migration
**What goes wrong:** Shopify OAuth tokens become undecryptable after data migration.
**Why it happens:** Different encryption keys or corrupted binary data during transfer.
**How to avoid:**
1. Export encrypted data as-is (don't decrypt during migration)
2. Verify encryption key is available in new environment
3. Test decryption of migrated data before marking migration complete
**Warning signs:** OAuth refresh fails, "Invalid token" errors.

### Pitfall 7: SQLite Habits in PostgreSQL
**What goes wrong:** Queries that worked in SQLite fail or perform poorly.
**Why it happens:** SQLite is more permissive (type affinity, implicit casting).
**How to avoid:**
- Use explicit types in models (not just `Integer` but `BigInteger` for Shopify IDs)
- Test with PostgreSQL in development, not SQLite
- PostgreSQL arrays require `db.ARRAY(db.String)`, not JSON strings
**Warning signs:** Type errors, unexpected NULL handling, performance issues.

## Code Examples

Verified patterns from official sources:

### Flask App with Database Configuration
```python
# Source: Flask-SQLAlchemy 3.1+ docs, SQLAlchemy 2.0 pooling docs
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import MetaData

# Naming convention for constraints (recommended)
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}
metadata = MetaData(naming_convention=convention)
db = SQLAlchemy(metadata=metadata)
migrate = Migrate()

def create_app():
    app = Flask(__name__)

    # Update connection string for psycopg3
    database_url = os.getenv('DATABASE_URL', '')
    if database_url.startswith('postgresql://'):
        database_url = database_url.replace('postgresql://', 'postgresql+psycopg://', 1)

    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 5,
        'max_overflow': 2,
        'pool_pre_ping': True,
        'pool_recycle': 1800,
    }

    db.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)  # batch mode for SQLite compat

    return app
```

### Database Backup Script
```bash
#!/bin/bash
# Source: PostgreSQL pg_dump docs, SimpleBackups Docker guide
# File: scripts/backup_db.sh

set -e

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
DB_CONTAINER="${DB_CONTAINER:-shopifyscrapingscript-db-1}"
DB_NAME="${DB_NAME:-shopify_platform}"
DB_USER="${DB_USER:-admin}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.dump"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Create backup with custom format and gzip compression
# -Fc: custom format (allows pg_restore selective restore)
# -Z: compression level (6 is default, good balance)
docker exec "$DB_CONTAINER" pg_dump \
    -U "$DB_USER" \
    -Fc \
    -Z 6 \
    "$DB_NAME" > "$BACKUP_FILE"

# Show backup size
ls -lh "$BACKUP_FILE"

# Optional: Keep only last 5 backups (development retention)
cd "$BACKUP_DIR" && ls -t backup_*.dump | tail -n +6 | xargs -r rm --

echo "Backup created: $BACKUP_FILE"
```

### Database Restore Script
```bash
#!/bin/bash
# Source: PostgreSQL pg_restore docs
# File: scripts/restore_db.sh

set -e

BACKUP_FILE="$1"
DB_CONTAINER="${DB_CONTAINER:-shopifyscrapingscript-db-1}"
DB_NAME="${DB_NAME:-shopify_platform}"
DB_USER="${DB_USER:-admin}"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file.dump>"
    exit 1
fi

echo "WARNING: This will replace all data in $DB_NAME"
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

# Restore from custom format backup
# -c: clean (drop objects before recreating)
# -d: target database
cat "$BACKUP_FILE" | docker exec -i "$DB_CONTAINER" pg_restore \
    -U "$DB_USER" \
    -c \
    -d "$DB_NAME"

echo "Restore complete. Verify with: flask db current"
```

### Initial Migration Setup
```bash
# First-time setup (run once)
flask db init

# After defining models, generate migration
flask db migrate -m "Initial schema: users, products, vendors, jobs"

# Apply migration
flask db upgrade

# Verify current state
flask db current
```

### Sample Schema Design (Key Tables)
```python
# Source: Research synthesis - multi-tenant e-commerce patterns
# File: src/models/schema.py

from . import db, TimestampMixin

class User(db.Model, TimestampMixin):
    """Platform user - owns one Shopify store in v1.0."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255))  # For future auth
    tier = db.Column(db.String(20), default='free')  # free, pro, enterprise

    # Single store per user (v1.0)
    shopify_store = db.relationship('ShopifyStore', backref='user', uselist=False)
    vendors = db.relationship('Vendor', backref='user', lazy='dynamic')
    jobs = db.relationship('Job', backref='user', lazy='dynamic')


class ShopifyStore(db.Model, TimestampMixin):
    """User's connected Shopify store."""
    __tablename__ = 'shopify_stores'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)

    store_url = db.Column(db.String(255), nullable=False)  # xxx.myshopify.com
    access_token_encrypted = db.Column(db.LargeBinary)  # Fernet encrypted
    api_version = db.Column(db.String(20), default='2024-01')

    products = db.relationship('Product', backref='store', lazy='dynamic')


class Vendor(db.Model, TimestampMixin):
    """Vendor/supplier whose catalog has been imported."""
    __tablename__ = 'vendors'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    name = db.Column(db.String(255), nullable=False)
    code = db.Column(db.String(50), index=True)  # Short code like 'PENTART'
    website_url = db.Column(db.String(500))

    catalog_items = db.relationship('VendorCatalogItem', backref='vendor', lazy='dynamic')


class VendorCatalogItem(db.Model, TimestampMixin):
    """Parsed vendor catalog data (from CSV imports)."""
    __tablename__ = 'vendor_catalog_items'

    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendors.id'), nullable=False, index=True)

    sku = db.Column(db.String(100), index=True)
    barcode = db.Column(db.String(50), index=True)  # EAN/UPC
    weight_grams = db.Column(db.Integer)
    # Sparse columns - only populate what exists in source
    title = db.Column(db.String(500))
    price = db.Column(db.Numeric(10, 2))

    # Composite index for fast catalog search
    __table_args__ = (
        db.Index('ix_vendor_catalog_sku_barcode', 'vendor_id', 'sku', 'barcode'),
    )


class Product(db.Model, TimestampMixin):
    """Product synced from/to Shopify."""
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('shopify_stores.id'), nullable=False, index=True)

    shopify_product_id = db.Column(db.BigInteger, index=True)
    sku = db.Column(db.String(100), index=True)
    barcode = db.Column(db.String(50), index=True)
    title = db.Column(db.String(500))
    vendor = db.Column(db.String(255))
    product_type = db.Column(db.String(255))
    status = db.Column(db.String(20))  # active, draft, archived

    # Relationships
    enrichment = db.relationship('ProductEnrichment', backref='product', uselist=False)
    images = db.relationship('ProductImage', backref='product', lazy='dynamic')


class ProductEnrichment(db.Model, TimestampMixin):
    """AI-generated and scraped product data."""
    __tablename__ = 'product_enrichments'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), unique=True, nullable=False)

    # SEO
    meta_title = db.Column(db.String(70))
    meta_description = db.Column(db.String(160))

    # Content
    description_html = db.Column(db.Text)
    tags = db.Column(db.ARRAY(db.String(100)))  # PostgreSQL array

    # Customs/shipping
    hs_code = db.Column(db.String(20))
    country_of_origin = db.Column(db.String(100))

    # Tracking
    source = db.Column(db.String(50))  # vision_ai, web_scrape, manual
    version = db.Column(db.Integer, default=1)


class Job(db.Model, TimestampMixin):
    """Background job tracking (Celery task metadata)."""
    __tablename__ = 'jobs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    celery_task_id = db.Column(db.String(50), unique=True)
    job_type = db.Column(db.String(50))  # scrape, enrich, sync
    status = db.Column(db.String(20), default='pending')  # pending, running, completed, failed

    # Progress tracking
    total_items = db.Column(db.Integer)
    processed_items = db.Column(db.Integer, default=0)

    # Results
    result_data = db.Column(db.JSON)  # PostgreSQL JSONB
    error_message = db.Column(db.Text)

    completed_at = db.Column(db.DateTime(timezone=True))
```

## Backup and Recovery Recommendation

### Recommendation: pg_dump with Custom Format

**Method:** `pg_dump -Fc -Z 6` (custom format with gzip compression level 6)

**Rationale:**
- **Portability:** Works across PostgreSQL versions (unlike volume snapshots)
- **Flexibility:** pg_restore can selectively restore tables/schemas
- **Compression:** ~17x smaller than uncompressed (4.7GB -> 276MB typical)
- **Speed:** gzip level 6 is 3x faster than level 9 with only 10% larger files
- **Docker-friendly:** Runs via `docker exec`, no volume access needed

**Development Workflow:**
1. Manual backup before risky operations: `./scripts/backup_db.sh`
2. Keep last 5 backups (configurable retention)
3. Store in `./backups/` (gitignored)
4. Restore time target: Under 5 minutes for typical dev database

**Storage Estimate (cost-conscious):**
- 10,000 products + enrichment: ~50MB compressed
- 5 backup retention: ~250MB total
- Local filesystem - no cloud costs during development

**Production (Phase 13):** Automated daily backups to cloud storage with 30-day retention.

### Alternative: Docker Volume Snapshots

**When to consider:**
- Very large databases (100GB+) where pg_dump takes too long
- Need point-in-time recovery
- Using managed PostgreSQL with snapshot support

**Why not for this phase:**
- More complex restore process
- Ties to specific Docker/storage setup
- Not portable across environments

## Schema Versioning Recommendation

### Recommendation: Flask-Migrate (Alembic)

**Why Flask-Migrate over raw Alembic:**
- Integrated `flask db` commands (init, migrate, upgrade, downgrade)
- Automatic batch mode (works with SQLite during local dev)
- Automatic type change detection (compare_type=True)
- Flask app context handling built-in

**Why not simple SQL scripts:**
- No automatic change detection
- Manual version tracking
- No rollback support
- Team sync issues (ordering, conflicts)

**Workflow:**
```bash
# After model changes
flask db migrate -m "Add product_type to products"
# Review generated migration in migrations/versions/
flask db upgrade
git add migrations/ && git commit -m "migration: add product_type"
```

## Connection Pool Recommendation

### Development Settings

```python
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 5,        # Keep 5 persistent connections
    'max_overflow': 2,     # Allow 2 extra during peaks
    'pool_pre_ping': True, # Validate connections (handles db restarts)
    'pool_recycle': 1800,  # Recycle after 30 min (prevent stale)
}
```

**Total connections per service:** 7 max (5 + 2 overflow)
**With backend + celery_worker:** 14 connections max
**PostgreSQL default max_connections:** 100 (plenty of headroom)

**Why these settings:**
- pool_size=5 is SQLAlchemy default, sufficient for single-developer
- pool_pre_ping prevents "server closed connection" errors after idle
- Small overflow allows burst handling without exhausting connections
- Debugging easier with fewer connections

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| psycopg2-binary | psycopg[binary] (v3) | 2023-2024 | 4-5x memory efficiency, async support |
| flask db upgrade in app | Run as entrypoint/init container | 2024+ | Cleaner separation, atomic deployments |
| Plain SQL backups | Custom format with compression | Always, but zstd in PG16 | 17x smaller backups, faster restore |
| Manual migration SQL | Alembic auto-generation | 2015+ | Automatic change detection, version control |

**Deprecated/outdated:**
- **FLASK_ENV variable:** Deprecated in Flask 2.3+, use FLASK_DEBUG=1
- **psycopg2 in new projects:** psycopg3 is recommended for new development
- **SQLAlchemy 1.x patterns:** Use 2.0 style (select(), Session, type hints)

## Open Questions

Things that couldn't be fully resolved:

1. **Encryption library for Shopify tokens**
   - What we know: Need authenticated encryption (Fernet recommended)
   - What's unclear: Key storage/rotation strategy in Docker secrets
   - Recommendation: Use Fernet, store key in Docker secret file, address rotation in Phase 13

2. **Pentart data import details**
   - What we know: 3 columns (barcode, SKU, weight) from 10-column CSV
   - What's unclear: Exact file location, encoding, row count
   - Recommendation: Verify file location during planning, create import script

3. **Existing SQLite vision_cache migration**
   - What we know: `src/core/vision_cache.py` uses SQLite for alt-text cache
   - What's unclear: Whether to migrate this data or regenerate
   - Recommendation: Vision cache can be regenerated (AI calls are cached), defer migration

## Sources

### Primary (HIGH confidence)
- [Flask-SQLAlchemy Documentation](https://flask-sqlalchemy.palletsprojects.com/) - ORM setup patterns
- [Flask-Migrate Documentation](https://flask-migrate.readthedocs.io/) - Migration commands and configuration
- [SQLAlchemy 2.0 Connection Pooling](https://docs.sqlalchemy.org/en/20/core/pooling.html) - Pool parameters
- [SQLAlchemy 2.0 PostgreSQL Dialect](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html) - Driver options
- [PostgreSQL pg_dump Documentation](https://www.postgresql.org/docs/current/app-pgdump.html) - Backup options
- [psycopg3 Documentation](https://www.psycopg.org/psycopg3/docs/basic/from_pg2.html) - Migration from psycopg2

### Secondary (MEDIUM confidence)
- [OneUptime Flask Database Migrations 2026](https://oneuptime.com/blog/post/2026-02-02-flask-database-migrations/view) - Docker deployment patterns
- [SimpleBackups Docker Postgres Guide](https://simplebackups.com/blog/docker-postgres-backup-restore-guide-with-examples) - Backup scripts
- [Crunchy Data Multi-Tenancy Design](https://www.crunchydata.com/blog/designing-your-postgres-database-for-multi-tenancy) - Tenant isolation patterns
- [pg_dump Compression Comparison](https://kmoppel.github.io/2024-01-05-best-pgdump-compression-settings-in-2024/) - Compression benchmarks
- [Cybertec pg_dump Compression PG16](https://www.cybertec-postgresql.com/en/pg_dump-compression-specifications-postgresql-16/) - PG16 compression options

### Tertiary (LOW confidence)
- [psycopg2 vs psycopg3 Benchmark](https://www.tigerdata.com/blog/psycopg2-vs-psycopg3-performance-benchmark) - Performance comparison
- [E-commerce Database Schema GitHub](https://github.com/larbisahli/e-commerce-database-schema) - Reference schema

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Official documentation for all libraries
- Architecture: HIGH - Patterns from official Flask-SQLAlchemy and Alembic docs
- Backup/Recovery: HIGH - PostgreSQL official docs plus verified community benchmarks
- Schema design: MEDIUM - Synthesized from multiple multi-tenant patterns
- Pitfalls: HIGH - Cross-referenced with official docs and real-world reports

**Research date:** 2026-02-08
**Valid until:** 2026-04-08 (60 days - PostgreSQL and Flask-SQLAlchemy are stable)

**Special notes:**
- CONTEXT.md decisions followed: Fresh schema from requirements (not SQLite migration), single Shopify store per user, development-friendly pool settings
- Deferred items respected: Production backups (Phase 13), product version history (Phase 11), multi-store (v2.0)
- Existing vision_cache.py uses SQLite - recommend regenerating cache rather than migrating
