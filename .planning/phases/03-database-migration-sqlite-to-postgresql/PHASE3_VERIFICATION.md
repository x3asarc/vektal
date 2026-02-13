# Phase 3 Verification Steps

Database Migration (SQLite to PostgreSQL) - Complete Verification Guide

## Prerequisites

Wait for Docker build to complete, then proceed with these steps.

## 1. Start the Stack

```bash
docker compose up -d
```

Wait for all containers to be healthy (about 30 seconds).

## 2. Verify Database Tables Created

```bash
docker compose exec db psql -U admin -d shopify_platform -c "\dt"
```

**Expected Output:** Should show 10 tables:
- users
- shopify_stores
- shopify_credentials
- vendors
- vendor_catalog_items
- products
- product_enrichments
- product_images
- jobs
- job_results
- alembic_version

## 3. Test Backup/Restore Cycle

```bash
# Create backup
./scripts/backup_db.sh

# Insert test data
docker compose exec db psql -U admin -d shopify_platform -c "INSERT INTO users (email, tier, created_at, updated_at) VALUES ('test@example.com', 'free', NOW(), NOW())"

# Verify test data exists
docker compose exec db psql -U admin -d shopify_platform -c "SELECT email FROM users WHERE email='test@example.com'"

# Restore backup (removes test data)
./scripts/restore_db.sh backups/backup_*.dump
# Type 'y' to confirm

# Verify test data gone
docker compose exec db psql -U admin -d shopify_platform -c "SELECT * FROM users WHERE email='test@example.com'"
```

**Expected:** Test data should be gone after restore (should return 0 rows)

## 4. Test Health Endpoint

```bash
curl http://localhost:5000/health
```

**Expected:** `{"database": "connected", "status": "ok"}`

## 5. Verify Encryption Module Works

```bash
docker compose exec backend python -c "
from src.core.encryption import encrypt_token, decrypt_token
token = 'shpat_test_12345'
encrypted = encrypt_token(token)
decrypted = decrypt_token(encrypted)
print(f'Original: {token}')
print(f'Decrypted: {decrypted}')
print(f'Match: {token == decrypted}')
"
```

**Expected:** `Match: True`

## 6. Verify ShopifyStore Encryption Wiring (CRITICAL)

This tests that the ShopifyStore model can encrypt/decrypt tokens using deferred imports.

```bash
docker compose exec backend python -c "
from src.database import create_app, db
from src.models import User, ShopifyStore

app = create_app()
with app.app_context():
    # Create test user and store
    user = User(email='encryption_test@example.com', tier='free')
    db.session.add(user)
    db.session.flush()

    store = ShopifyStore(user_id=user.id, store_url='test.myshopify.com')

    # Test set_access_token (uses deferred import to encryption.py)
    test_token = 'shpat_encryption_wiring_test_12345'
    store.set_access_token(test_token)

    # Verify token was encrypted (not stored as plaintext)
    assert store.access_token_encrypted is not None
    assert store.access_token_encrypted != test_token.encode()

    # Test get_access_token (uses deferred import to encryption.py)
    retrieved_token = store.get_access_token()
    assert retrieved_token == test_token, f'Token mismatch: {retrieved_token} != {test_token}'

    # Cleanup - rollback test data
    db.session.rollback()

    print('ShopifyStore.set_access_token(): OK')
    print('ShopifyStore.get_access_token(): OK')
    print('Encryption wiring: VERIFIED')
"
```

**Expected Output:**
```
ShopifyStore.set_access_token(): OK
ShopifyStore.get_access_token(): OK
Encryption wiring: VERIFIED
```

## 7. Verify No SQLite3 in app.py

```bash
grep -c "sqlite3" src/app.py
```

**Expected:** `0` (no sqlite3 imports/usage)

## 8. Check Backend Logs

```bash
docker compose logs backend --tail 20
```

**Expected:** Should show migrations running successfully and Gunicorn starting

## Summary of What Was Built

**Phase 3 Complete - Database Migration (SQLite to PostgreSQL)**

All 5 plans executed (18 minutes total):
- **03-01:** Flask-SQLAlchemy + psycopg3 foundation (5 min)
- **03-02:** 10 SQLAlchemy models with relationships (5 min)
- **03-03:** Migrations, backup/restore, encryption (7 min)
- **03-04:** Pentart import script, auto-migrations (3 min)
- **03-05:** app.py SQLAlchemy refactor (completed auto tasks)

**Key Infrastructure:**
1. SQLAlchemy models for all entities (User, ShopifyStore, Vendor, Product, Job)
2. Flask-Migrate with initial migration (11 tables, 25+ indexes)
3. Backup/restore scripts (pg_dump/pg_restore, <5min restore target)
4. Fernet encryption for OAuth tokens
5. Pentart catalog import (3 columns only - initial data, not migration)
6. app.py using SQLAlchemy ORM (no sqlite3)
7. Auto-migration on container startup
8. ShopifyStore encryption wiring via deferred imports

**PostgreSQL 16 Configuration:**
- Connection pooling (5+2 per service)
- psycopg3 driver (4-5x more memory efficient)
- Development-friendly pool settings with pre-ping validation

---

## Troubleshooting

### Issue: Database container fails with "incompatible version"
**Fix:** Old PostgreSQL 15 data volume needs removal
```bash
docker compose down
docker volume rm shopify_postgres_data
docker compose up -d
```

### Issue: "ModuleNotFoundError: No module named 'flask_migrate'"
**Fix:** Rebuild backend container with new dependencies
```bash
docker compose build backend
docker compose up -d
```

### Issue: Syntax errors in app.py
**Fix:** Already fixed in Plan 03-05 (removed incomplete try blocks, fixed indentation)

---

## Approval

Once all verifications pass, the checkpoint is complete and Phase 3 is verified.

**Next Phase:** Phase 4 - Authentication & User Management
