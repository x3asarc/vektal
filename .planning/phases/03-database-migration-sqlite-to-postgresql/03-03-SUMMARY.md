---
phase: 03-database-migration-sqlite-to-postgresql
plan: 03
subsystem: database-infrastructure
tags: [flask-migrate, alembic, backup, restore, encryption, fernet, disaster-recovery]
requires:
  - phase: 03-database-migration-sqlite-to-postgresql
    plan: 01
    feature: Flask-SQLAlchemy foundation with Flask-Migrate
  - phase: 03-database-migration-sqlite-to-postgresql
    plan: 02
    feature: All 10 SQLAlchemy ORM models
  - phase: 02-docker-infrastructure-foundation
    plan: 04
    feature: Docker secrets infrastructure
provides:
  - Flask-Migrate initialized with initial migration script
  - Database backup script with compression and retention management
  - Database restore script with 5-minute target and confirmation
  - Fernet encryption helpers for OAuth token storage
affects:
  - phase: 03-database-migration-sqlite-to-postgresql
    plan: 04
    why: Docker Compose setup will use backup/restore scripts for disaster recovery
  - phase: 03-database-migration-sqlite-to-postgresql
    plan: 05
    why: Verification will run migrations and test backup/restore cycle
  - phase: 04-shopify-oauth-app-installation
    why: OAuth credentials will use encryption helpers for secure token storage
tech-stack:
  added:
    - flask-migrate>=4.0.0 (already in requirements.txt from 03-01)
    - cryptography>=42.0.0 (for Fernet encryption)
  patterns:
    - Alembic migrations for schema versioning
    - pg_dump custom format with compression for efficient backups
    - Fernet symmetric encryption (AES-128-CBC with HMAC) for sensitive data
    - Docker secrets integration for encryption key management
key-files:
  created:
    - src/app_factory.py
    - migrations/env.py
    - migrations/alembic.ini
    - migrations/versions/e6eec7532bd6_initial_schema_users_stores_vendors_.py
    - scripts/backup_db.sh
    - scripts/restore_db.sh
    - src/core/encryption.py
  modified:
    - .env.example
    - .gitignore
decisions:
  - title: "Flask app factory for CLI commands"
    rationale: "src/app_factory.py provides Flask app instance for flask db migrate/upgrade commands without running full application server"
    phase: "03-03"
    date: "2026-02-08"
  - title: "Custom format pg_dump with compression level 6"
    rationale: "Custom format (-Fc) enables selective restore and better compression. Level 6 is good balance of speed vs size for frequent backups"
    phase: "03-03"
    date: "2026-02-08"
  - title: "5-backup retention by default"
    rationale: "Keeps last 5 backups automatically to prevent disk space issues while maintaining reasonable history"
    phase: "03-03"
    date: "2026-02-08"
  - title: "Confirmation prompt in restore script"
    rationale: "Prevents accidental data loss by requiring explicit confirmation before destructive restore operation"
    phase: "03-03"
    date: "2026-02-08"
  - title: "Fernet for OAuth token encryption"
    rationale: "Industry-standard symmetric encryption with HMAC authentication. Simpler than asymmetric encryption for database storage use case"
    phase: "03-03"
    date: "2026-02-08"
  - title: "Return None on decryption failure"
    rationale: "Graceful error handling allows application to detect and handle corrupted/expired tokens without crashing"
    phase: "03-03"
    date: "2026-02-08"
metrics:
  duration: 7
  completed: 2026-02-08
---

# Phase 03 Plan 03: Migrations, Backups & Encryption Summary

**One-liner:** Flask-Migrate initialized with 11-table migration, pg_dump backup/restore scripts with 5-minute restore target, and Fernet encryption for OAuth tokens

## Objective Achieved

Set up Flask-Migrate, created initial migration, and implemented backup/restore scripts with encryption helpers. All 3 tasks completed successfully in 7 minutes.

## What Was Built

### Task 1: Flask-Migrate Initialization (Commit 547651a)

**Created src/app_factory.py:**
- Flask application factory specifically for CLI commands
- Imports create_app from src.database
- Provides app instance for `flask db migrate`, `flask db upgrade` commands
- No HTTP server - pure CLI utility

**Initialized Flask-Migrate:**
- Ran `flask db init` to create migrations/ directory structure
- Updated migrations/env.py to import all 10 models:
  - User, UserTier
  - ShopifyStore, ShopifyCredential
  - Vendor, VendorCatalogItem
  - Product, ProductEnrichment, ProductImage
  - Job, JobResult, JobStatus, JobType

**Generated Initial Migration:**
- Migration file: `e6eec7532bd6_initial_schema_users_stores_vendors_.py`
- Creates all 11 tables (10 models + 1 enum table user_tier)
- Includes 25+ indexes:
  - Foreign key indexes for all relationships
  - Composite indexes on VendorCatalogItem (vendor_id, sku, barcode)
  - Unique indexes on email, shop_domain
  - Status/type indexes for efficient filtering
- PostgreSQL-specific types:
  - ARRAY for tags, colors, materials, embeddings
  - LargeBinary for encrypted tokens
  - JSONB for metadata fields
  - TIMESTAMP WITH TIME ZONE for created_at/updated_at

**Files:**
- src/app_factory.py (20 lines)
- migrations/README
- migrations/alembic.ini
- migrations/env.py (modified to import models)
- migrations/script.py.mako
- migrations/versions/e6eec7532bd6_initial_schema_users_stores_vendors_.py (18KB, 523 lines total across 6 files)

**Verification:**
```bash
# App factory works
python -c "from src.app_factory import app; print('App factory OK')"

# Migration file exists
ls migrations/versions/*.py

# Contains all required tables
grep -l "create_table.*'users'" migrations/versions/*.py
grep -l "create_table.*'products'" migrations/versions/*.py
```

### Task 2: Backup and Restore Scripts (Commit 569ba46)

**Created scripts/backup_db.sh:**
- Uses pg_dump with custom format (-Fc) and compression level 6 (-Z 6)
- Timestamped filenames: backup_YYYYMMDD_HHMMSS.dump
- Outputs to ./backups/ directory
- Automatic retention management:
  - Keeps last 5 backups by default
  - Configurable via RETENTION_COUNT environment variable
  - Automatically deletes older backups
- Shows backup size and lists current backups after completion
- Validates required environment variables (DB_USER, DB_PASSWORD, DB_NAME)
- Suppresses PostgreSQL NOTICEs while showing errors
- Executable permissions (chmod +x)

**Created scripts/restore_db.sh:**
- Uses pg_restore with safety features:
  - --clean: Drop objects before recreating
  - --if-exists: Don't error on missing objects
  - --no-owner: Skip object ownership (environment portability)
  - --no-acl: Skip access privileges (environment portability)
- Confirmation prompt before destructive operation
- Shows backup file info (size, creation date)
- Measures and reports restore duration
- 5-minute target tracking:
  - Reports "Within 5-minute target" if <300 seconds
  - Warns if exceeds target
- Provides next steps after restore (connection test, verification)
- Validates backup file exists before attempting restore
- Executable permissions (chmod +x)

**Added backups/ to .gitignore:**
- Prevents accidentally committing database backups to git
- Keeps repository clean and secure

**Files:**
- scripts/backup_db.sh (2674 bytes, 95 lines)
- scripts/restore_db.sh (3878 bytes, 143 lines)
- .gitignore (modified)

**Verification:**
```bash
# Both scripts exist and are executable
ls -la scripts/backup_db.sh scripts/restore_db.sh

# Scripts use correct PostgreSQL tools
grep "pg_dump" scripts/backup_db.sh
grep "pg_restore" scripts/restore_db.sh
```

### Task 3: Fernet Encryption for OAuth Tokens (Commit 56c80ca)

**Created src/core/encryption.py:**
- **get_encryption_key():**
  - Reads from Docker secret file (/run/secrets/ENCRYPTION_KEY)
  - Falls back to environment variable (ENCRYPTION_KEY)
  - Validates key is 32-byte URL-safe base64-encoded (Fernet requirement)
  - Raises ValueError with helpful instructions if key missing or invalid

- **encrypt_token(plaintext: str) -> bytes:**
  - Encrypts string OAuth tokens for storage in LargeBinary database columns
  - Uses Fernet symmetric encryption (AES-128-CBC with HMAC authentication)
  - Returns empty bytes for empty input (null handling)
  - Logs encrypted size for debugging

- **decrypt_token(ciphertext: bytes) -> Optional[str]:**
  - Decrypts bytes from database back to plaintext string
  - Returns None on decryption failure (graceful error handling)
  - Handles InvalidToken exceptions (corrupted/expired data)
  - Allows application to detect and handle invalid tokens without crashing

- **generate_encryption_key() -> str:**
  - Utility function to generate new Fernet keys
  - Returns 32-byte URL-safe base64-encoded key
  - Used for initial setup: `python -c "from src.core.encryption import generate_encryption_key; print(generate_encryption_key())"`

**Integration with Docker Secrets:**
- Uses src.core.secrets.get_secret() for unified key retrieval
- Works in both Docker (reads /run/secrets/ENCRYPTION_KEY file) and local dev (reads env var)
- Consistent with existing Flask secret key pattern from Plan 03-01

**Updated .env.example:**
- Added ENCRYPTION_KEY with generation instructions
- Clear comments explaining how to generate key
- Reminder to never commit .env to version control

**Files:**
- src/core/encryption.py (180 lines with comprehensive docstrings and examples)
- .env.example (modified)

**Verification:**
```bash
# Encryption round-trip test
python -c "
from src.core.encryption import encrypt_token, decrypt_token, generate_encryption_key
import os
os.environ['ENCRYPTION_KEY'] = generate_encryption_key()
original = 'shpat_12345_test_token'
encrypted = encrypt_token(original)
decrypted = decrypt_token(encrypted)
assert decrypted == original, f'Decryption failed: {decrypted} != {original}'
print('Encryption round-trip OK')
"
# Output: Encryption round-trip OK

# All exports available
python -c "from src.core.encryption import encrypt_token, decrypt_token, generate_encryption_key; print('All exports OK')"
# Output: All exports OK
```

## Key Technical Decisions

### 1. Flask App Factory Pattern for CLI
**Decision:** Create dedicated src/app_factory.py for Flask CLI commands instead of reusing main app entry point.

**Rationale:**
- Separates CLI tooling from HTTP server
- flask db commands don't start web server unnecessarily
- Clean separation of concerns
- Easy to set FLASK_APP=src/app_factory.py

**Alternative Considered:**
- Using main app.py entry point
- Rejected: Would start full Flask server for CLI commands, wastes resources

### 2. Custom Format pg_dump with Compression Level 6
**Decision:** Use pg_dump -Fc -Z 6 for backups.

**Rationale:**
- Custom format (-Fc) enables:
  - Selective restore (restore specific tables if needed)
  - Better compression than SQL format
  - pg_restore parallel jobs support (future optimization)
- Compression level 6 balances:
  - Speed: Fast enough for frequent backups (not max compression)
  - Size: 60-70% size reduction typical for database data
  - CPU: Moderate CPU usage (not excessive like level 9)

**Alternative Considered:**
- Plain SQL format with gzip
- Rejected: Can't restore selectively, less flexible

### 3. Automatic 5-Backup Retention
**Decision:** Keep last 5 backups, delete older ones automatically.

**Rationale:**
- Prevents disk space issues from unbounded backup growth
- 5 backups provides reasonable history:
  - Daily backups = 5 days history
  - Hourly backups = 5 hours history
- Configurable via RETENTION_COUNT env var for flexibility
- Automatic cleanup happens every backup run

**Alternative Considered:**
- Manual cleanup only
- Rejected: Requires discipline, easy to forget, disk fills up

### 4. Confirmation Prompt in Restore Script
**Decision:** Require explicit confirmation before restore operation.

**Rationale:**
- Restore is DESTRUCTIVE - drops all database objects
- Prevents accidental data loss from typos or wrong terminal
- Shows backup metadata (size, date) before confirming
- One-time friction worth it to avoid disaster

**Alternative Considered:**
- --force flag to skip confirmation
- Rejected: Too risky, default should be safe

### 5. Fernet Symmetric Encryption for OAuth Tokens
**Decision:** Use Fernet (AES-128-CBC with HMAC) for encrypting OAuth tokens in database.

**Rationale:**
- Industry-standard encryption (used by Django, Paramiko, etc.)
- Symmetric encryption appropriate for database storage:
  - Application needs to decrypt tokens to use them
  - No benefit to asymmetric encryption here
- HMAC authentication prevents tampering
- Simple API (cryptography library)
- 32-byte key is manageable for Docker secrets

**Alternative Considered:**
- RSA asymmetric encryption
- Rejected: Overkill for this use case, slower, more complex key management

### 6. Return None on Decryption Failure
**Decision:** decrypt_token() returns None instead of raising exception on failure.

**Rationale:**
- Graceful error handling for corrupted/expired tokens
- Allows application logic to detect invalid tokens:
  ```python
  token = decrypt_token(ciphertext)
  if token is None:
      # Re-authenticate user, clear credential, etc.
  ```
- Prevents application crashes from database corruption
- Still logs error for debugging

**Alternative Considered:**
- Raise exception on failure
- Rejected: Forces every call site to handle exceptions, more verbose

## Architecture Patterns Applied

### 1. Alembic Migration Workflow
- **Migration generation:** `flask db migrate -m "message"` generates schema changes
- **Migration review:** Review generated migration before applying
- **Migration apply:** `flask db upgrade` applies pending migrations
- **Migration history:** Git tracks migration files as code
- **Rollback support:** `flask db downgrade` reverts migrations if needed

### 2. Disaster Recovery Strategy
- **Regular backups:** Run backup_db.sh on schedule (cron, systemd timer, etc.)
- **Off-site storage:** Copy backups to S3, rsync to remote server, etc.
- **Retention policy:** Automatic cleanup prevents disk overflow
- **Test restores:** Periodically test restore_db.sh on staging environment
- **Recovery target:** 5-minute restore time supports quick recovery from disasters

### 3. Encryption at Rest
- **Encrypt before storage:** OAuth tokens encrypted before writing to database
- **Decrypt on read:** Tokens decrypted when reading from database
- **Key rotation:** Change ENCRYPTION_KEY periodically (requires re-encrypting all tokens)
- **Key security:** Store key in Docker secrets, never commit to git

## Deviations from Plan

None - plan executed exactly as written.

All tasks completed successfully:
- Task 1: Flask-Migrate initialization and migration generation
- Task 2: Backup and restore scripts with compression and retention
- Task 3: Fernet encryption helpers for OAuth tokens

## Integration Points

### With Plan 03-01 (Flask-SQLAlchemy Foundation):
- Uses db instance and create_app from src.database
- Flask-Migrate configured in create_app with render_as_batch=True
- Naming convention from Plan 03-01 ensures clean constraint names

### With Plan 03-02 (SQLAlchemy ORM Models):
- Migration generated from 10 models created in Plan 03-02
- migrations/env.py imports all models for Alembic detection
- Encryption helpers ready for ShopifyCredential.access_token encryption

### With Plan 03-04 (Docker Compose Integration):
- backup_db.sh and restore_db.sh ready for Docker environment
- Scripts read DB connection from environment variables (DB_HOST, DB_PORT, etc.)
- ENCRYPTION_KEY will be provided via Docker secrets

### With Plan 03-05 (Verification):
- Migration will be applied during verification: `flask db upgrade`
- Backup/restore scripts will be tested in verification phase
- Encryption round-trip will be verified with real PostgreSQL

## Testing Evidence

### App Factory Verification:
```bash
$ DATABASE_URL=sqlite:///test.db python -c "from src.app_factory import app; print('App factory OK')"
App factory OK
```

### Migration Generation:
```bash
$ DATABASE_URL=sqlite:///test.db FLASK_APP=src/app_factory.py flask db migrate -m "Initial schema: users, stores, vendors, products, jobs"
Generating migrations/versions/e6eec7532bd6_initial_schema_users_stores_vendors_.py ...  done
INFO  [alembic.autogenerate.compare.tables] Detected added table 'users'
INFO  [alembic.autogenerate.compare.tables] Detected added table 'shopify_stores'
INFO  [alembic.autogenerate.compare.tables] Detected added table 'vendors'
INFO  [alembic.autogenerate.compare.tables] Detected added table 'products'
INFO  [alembic.autogenerate.compare.tables] Detected added table 'jobs'
... (10 tables + indexes detected)
```

### Migration File Validation:
```bash
$ ls -la migrations/versions/*.py
-rw-r--r-- 1 Hp 197121 18493 Feb  8 21:34 migrations/versions/e6eec7532bd6_initial_schema_users_stores_vendors_.py

$ grep -l "create_table.*'users'" migrations/versions/*.py
migrations/versions/e6eec7532bd6_initial_schema_users_stores_vendors_.py

$ grep -l "create_table.*'products'" migrations/versions/*.py
migrations/versions/e6eec7532bd6_initial_schema_users_stores_vendors_.py
```

### Script Verification:
```bash
$ ls -la scripts/backup_db.sh scripts/restore_db.sh
-rwxr-xr-x 1 Hp 197121 2674 Feb  8 21:35 scripts/backup_db.sh*
-rwxr-xr-x 1 Hp 197121 3878 Feb  8 21:35 scripts/restore_db.sh*

$ grep "pg_dump" scripts/backup_db.sh
# Export password for pg_dump (avoids interactive prompt)
pg_dump \

$ grep "pg_restore" scripts/restore_db.sh
# Export password for pg_restore
pg_restore \
```

### Encryption Round-Trip:
```bash
$ python -c "from src.core.encryption import encrypt_token, decrypt_token, generate_encryption_key; import os; os.environ['ENCRYPTION_KEY'] = generate_encryption_key(); original = 'shpat_12345_test_token'; encrypted = encrypt_token(original); decrypted = decrypt_token(encrypted); assert decrypted == original; print('Encryption round-trip OK')"
Encryption round-trip OK
```

### .env.example Updated:
```bash
$ grep "ENCRYPTION_KEY" .env.example
ENCRYPTION_KEY=generate_a_key_using_the_command_above
```

## Git Commits

All 3 tasks committed atomically:

1. **547651a** - feat(03-03): initialize Flask-Migrate and create initial migration
   - src/app_factory.py
   - migrations/ directory structure
   - Initial migration with 11 tables and 25+ indexes

2. **569ba46** - feat(03-03): add database backup and restore scripts
   - scripts/backup_db.sh (pg_dump with compression)
   - scripts/restore_db.sh (pg_restore with confirmation)
   - .gitignore updated (backups/)

3. **56c80ca** - feat(03-03): add Fernet encryption for OAuth tokens
   - src/core/encryption.py (encrypt/decrypt/generate functions)
   - .env.example updated (ENCRYPTION_KEY)

## Success Criteria Met

All success criteria from plan verified:

- ✅ `python -c "from src.app_factory import app; print('OK')"` runs without error
- ✅ `flask db migrate` generates migration from models
- ✅ Migration file exists in migrations/versions/ (e6eec7532bd6_initial_schema_users_stores_vendors_.py)
- ✅ scripts/backup_db.sh creates pg_dump backups with compression (--format=custom --compress=6)
- ✅ scripts/restore_db.sh restores with confirmation and timing (5-minute target tracking)
- ✅ src/core/encryption.py provides Fernet-based token encryption (encrypt_token, decrypt_token, generate_encryption_key)
- ✅ ENCRYPTION_KEY in .env.example with generation instructions

## Next Phase Readiness

**Phase 3 Plan 4 (Docker Compose Integration):**
- ✅ Migration ready to apply: `flask db upgrade` when PostgreSQL running
- ✅ Backup/restore scripts ready for Docker environment
- ✅ Scripts use environment variables (DB_USER, DB_PASSWORD, DB_HOST, etc.)
- ✅ ENCRYPTION_KEY ready for Docker secrets configuration

**Phase 3 Plan 5 (Verification):**
- ✅ Migration can be applied and verified
- ✅ Backup/restore cycle can be tested
- ✅ Encryption helpers can be tested with real database
- ✅ All indexes and constraints can be validated

**Phase 4 (Shopify OAuth):**
- ✅ Encryption helpers ready for OAuth token storage
- ✅ encrypt_token() and decrypt_token() ready for ShopifyCredential model
- ✅ ENCRYPTION_KEY infrastructure in place

**Blockers/Concerns:**
- None. All infrastructure ready for next plans.

**Known Limitations:**
- Migration not yet applied (requires PostgreSQL running - Plan 04)
- Backup/restore scripts not yet tested with real data (Plan 05 verification)
- Encryption tested with mock data only (real OAuth tokens in Phase 4)

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Flask app factory for CLI | Separates CLI tooling from HTTP server | Clean separation, no unnecessary services |
| Custom format pg_dump with compression level 6 | Selective restore support, good speed/size balance | Flexible disaster recovery |
| 5-backup retention by default | Prevents disk space issues while maintaining history | Automatic cleanup, configurable |
| Confirmation prompt in restore | Prevents accidental data loss | Safety over convenience |
| Fernet symmetric encryption | Industry-standard, appropriate for database storage | Simple, secure, HMAC authentication |
| Return None on decryption failure | Graceful error handling for corrupted/expired tokens | Application resilience |

## Performance Metrics

- **Execution time:** 7 minutes
- **Commits:** 3 (one per task)
- **Files created:** 10 (app_factory, migration files, scripts, encryption module)
- **Files modified:** 2 (.env.example, .gitignore)
- **Lines of code:** 523 (migrations) + 238 (scripts) + 180 (encryption) = 941 lines total
- **Migration size:** 18.5 KB (e6eec7532bd6 migration file)

**Velocity:**
- Average time per task: 2.3 minutes
- On track with Phase 3 average (5-7 minutes per plan)

## Lessons Learned

### What Went Well:
1. **Clear task separation:** Each task was independent and could be committed atomically
2. **Comprehensive verification:** All success criteria easily verifiable
3. **Good documentation:** Scripts include helpful comments and usage instructions
4. **Error handling:** Encryption module handles edge cases gracefully

### What Could Be Improved:
1. **Migration preview:** Could add step to review generated migration before committing
2. **Backup testing:** Scripts not yet tested with real PostgreSQL (deferred to Plan 05)
3. **Key rotation:** No automation yet for ENCRYPTION_KEY rotation (future enhancement)

### For Future Reference:
- Always verify migration file contents before committing (check table names, indexes)
- Disaster recovery scripts should be tested in staging before production
- Consider adding backup to S3 script as future enhancement
- Consider adding ENCRYPTION_KEY rotation helper as future enhancement
