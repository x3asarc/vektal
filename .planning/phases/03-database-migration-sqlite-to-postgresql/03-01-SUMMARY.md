---
phase: 03-database-migration-sqlite-to-postgresql
plan: 01
subsystem: database-infrastructure
tags: [postgresql, sqlalchemy, flask-migrate, psycopg3, orm]
requires:
  - phase: 02-docker-infrastructure-foundation
    feature: PostgreSQL container configuration
  - phase: 02-docker-infrastructure-foundation
    feature: Docker secrets for credentials
provides:
  - Flask-SQLAlchemy 3.1+ ORM with psycopg3 driver
  - Application factory pattern with database initialization
  - Development-friendly connection pooling (5 + 2 overflow)
  - TimestampMixin for automatic created_at/updated_at tracking
affects:
  - phase: 03-database-migration-sqlite-to-postgresql
    plan: 02
    why: Model definitions will use db instance and TimestampMixin
  - phase: 03-database-migration-sqlite-to-postgresql
    plan: 03
    why: Migration setup will use Flask-Migrate configured here
tech-stack:
  added:
    - Flask-SQLAlchemy>=3.1.0
    - Flask-Migrate>=4.0.0
    - psycopg[binary]>=3.2.0
    - cryptography>=42.0.0
  patterns:
    - Application factory pattern for database initialization
    - Naming convention for Alembic constraint generation
    - Automatic URL conversion for psycopg3 driver compatibility
key-files:
  created:
    - src/models/__init__.py
    - src/database.py
  modified:
    - requirements.txt
    - docker-compose.yml
decisions:
  - title: "psycopg3 over psycopg2"
    rationale: "4-5x more memory efficient, async support, better connection handling for production scaling"
    phase: "03-01"
    date: "2026-02-08"
  - title: "Development-friendly pool settings"
    rationale: "pool_size=5, max_overflow=2 = 7 connections max per service. With backend + celery_worker = 14 connections total (well under PostgreSQL default max_connections=100)"
    phase: "03-01"
    date: "2026-02-08"
  - title: "PostgreSQL 16 upgrade"
    rationale: "Latest stable version with performance improvements and better connection management per RESEARCH.md recommendations"
    phase: "03-01"
    date: "2026-02-08"
metrics:
  duration: 5 minutes
  tasks: 3
  commits: 3
  files_created: 2
  files_modified: 2
completed: 2026-02-08
---

# Phase 3 Plan 01: Flask-SQLAlchemy + PostgreSQL Setup Summary

**One-liner:** Flask-SQLAlchemy 3.1 ORM with psycopg3 driver, development pool settings (5+2), and PostgreSQL 16 container

## What Was Built

Set up Flask-SQLAlchemy and Flask-Migrate with PostgreSQL connection using psycopg3 driver. This establishes the database foundation for production schema, replacing the temporary SQLite setup with a proper ORM-based approach.

### Task Breakdown

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add database dependencies | fc3af24 | requirements.txt |
| 2 | Create SQLAlchemy instance and base models module | a4535a0 | src/models/__init__.py |
| 3 | Create database configuration and verify PostgreSQL container | 8d2a737 | src/database.py, docker-compose.yml |

### Key Components

**1. Database Dependencies (requirements.txt)**
- Flask-SQLAlchemy>=3.1.0 for SQLAlchemy 2.0 support
- Flask-Migrate>=4.0.0 for Alembic migration commands
- psycopg[binary]>=3.2.0 for psycopg3 driver with pre-built binaries
- cryptography>=42.0.0 for Fernet encryption of Shopify tokens

**2. SQLAlchemy Instance (src/models/__init__.py)**
- Configured with naming convention for Alembic constraint generation:
  - `ix_%(column_0_label)s` - indexes
  - `uq_%(table_name)s_%(column_0_name)s` - unique constraints
  - `fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s` - foreign keys
  - `pk_%(table_name)s` - primary keys
- TimestampMixin class for automatic created_at/updated_at timestamps with timezone awareness
- Exports `db` and `TimestampMixin` at module level for model definitions

**3. Application Factory (src/database.py)**
- `create_app()` function with database configuration
- Automatic URL conversion: `postgresql://` → `postgresql+psycopg://` for psycopg3 compatibility
- Development-friendly connection pool settings:
  - `pool_size=5` - Keep 5 persistent connections
  - `max_overflow=2` - Allow 2 extra during peaks (7 connections max per service)
  - `pool_pre_ping=True` - Validate connections before use (handles db restarts)
  - `pool_recycle=1800` - Recycle connections after 30 minutes
- Flask-Migrate initialization with `render_as_batch=True` for SQLite compatibility during development
- Config override support for testing

**4. PostgreSQL 16 Container (docker-compose.yml)**
- Updated from postgres:15 to postgres:16
- Verified complete configuration:
  - Environment variables: POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
  - Volume mount: postgres_data:/var/lib/postgresql/data
  - Health check: pg_isready command for startup ordering

## Decisions Made

### 1. psycopg3 over psycopg2
**Decision:** Use psycopg[binary]>=3.2.0 instead of psycopg2-binary
**Rationale:** 4-5x more memory efficient, async support, better connection handling. Pre-built binaries (`[binary]`) eliminate compilation requirements.

### 2. Development-friendly Connection Pool
**Decision:** pool_size=5, max_overflow=2 per service
**Rationale:**
- 7 connections max per service (backend + celery_worker = 14 total)
- Well under PostgreSQL default max_connections=100
- Small pool reduces debugging complexity during development
- Can be increased in Phase 13 for production optimization

### 3. PostgreSQL 16 Upgrade
**Decision:** Upgrade from postgres:15 to postgres:16 in docker-compose.yml
**Rationale:** Latest stable version with performance improvements per 03-RESEARCH.md recommendations. No breaking changes from PostgreSQL 15.

### 4. Naming Convention for Alembic
**Decision:** Configure SQLAlchemy MetaData with explicit naming convention
**Rationale:** Required for Alembic to generate proper constraint names in migrations. Prevents "unnamed constraint" errors during schema changes.

### 5. Automatic psycopg3 URL Conversion
**Decision:** Auto-convert `postgresql://` to `postgresql+psycopg://` in configure_app()
**Rationale:** DATABASE_URL may come from external sources (Docker env, cloud providers) using the generic `postgresql://` scheme. Automatic conversion ensures psycopg3 driver is always used without manual URL editing.

## Verification Results

All success criteria met:

✓ Flask-SQLAlchemy, Flask-Migrate, psycopg[binary], cryptography in requirements.txt
✓ src/models/__init__.py defines db with naming convention
✓ src/database.py application factory with pool settings (pool_size=5, max_overflow=2)
✓ PostgreSQL 16 in docker-compose.yml
✓ POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD environment variables
✓ postgres_data:/var/lib/postgresql/data volume mount
✓ pg_isready health check configured
✓ Connection string uses postgresql+psycopg:// dialect (auto-converted)

## Deviations from Plan

None - plan executed exactly as written.

## Integration Points

**Depends on:**
- Phase 2 Docker infrastructure (PostgreSQL container, secrets module)
- src/core/secrets.py for FLASK_SECRET_KEY retrieval

**Provides for:**
- Plan 02: Model definitions will inherit from db.Model and use TimestampMixin
- Plan 03: Flask-Migrate will use the configured migrate instance
- Plan 04+: All database operations use the application factory pattern

**Files created:**
- `src/models/__init__.py` - SQLAlchemy instance and TimestampMixin
- `src/database.py` - Application factory with database configuration

**Files modified:**
- `requirements.txt` - Added database dependencies
- `docker-compose.yml` - Updated PostgreSQL to version 16

## Next Phase Readiness

**Ready for Plan 02 (Model Definitions):**
- SQLAlchemy db instance available at `from src.models import db`
- TimestampMixin ready for model inheritance
- Application factory established for testing database operations

**Blockers:** None

**Concerns:** None - all dependencies installed, configuration verified

## Technical Notes

### Connection Pool Math
- Backend service: 5 persistent + 2 overflow = 7 max connections
- Celery worker: 5 persistent + 2 overflow = 7 max connections
- **Total: 14 connections** (14% of PostgreSQL default max_connections=100)
- Safe for development, can scale up in Phase 13

### psycopg3 Benefits
- Memory efficiency: 4-5x less memory per connection vs psycopg2
- Async support: Future-proofing for async Flask/FastAPI integration
- Better connection handling: Native pool management, improved error recovery
- Binary package: No compilation required, faster installation

### TimestampMixin Usage
```python
class Product(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    # created_at and updated_at added automatically
```

### Application Factory Usage
```python
from src.database import create_app

# Production
app = create_app()

# Testing
app = create_app(config_override={
    'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
    'TESTING': True
})
```

## Performance Metrics

- **Execution time:** 5 minutes
- **Tasks completed:** 3/3
- **Commits:** 3 (1 per task)
- **Files created:** 2
- **Files modified:** 2
- **Dependencies added:** 4

---

**Phase:** 03-database-migration-sqlite-to-postgresql
**Plan:** 01
**Status:** ✅ Complete
**Date:** 2026-02-08
