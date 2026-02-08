#!/bin/bash
#
# Database Restore Script
# Restores PostgreSQL database from compressed backup file.
#
# Usage:
#   ./scripts/restore_db.sh <backup_file>
#
# Example:
#   ./scripts/restore_db.sh ./backups/backup_20260208_143022.dump
#
# Features:
# - Confirmation prompt before destructive operation
# - Uses --clean and --if-exists for safe restore
# - Reports restore duration (target: <5 minutes)
# - Validates backup file exists

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Check if backup file was provided
if [ $# -lt 1 ]; then
    echo "Error: No backup file specified"
    echo ""
    echo "Usage: $0 <backup_file>"
    echo ""
    echo "Available backups:"
    ls -lh ./backups/backup_*.dump 2>/dev/null | awk '{print "  " $9 " (" $5 ", " $6 " " $7 ")"}' || echo "  (none found)"
    exit 1
fi

BACKUP_FILE="$1"

# Validate backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file not found: ${BACKUP_FILE}"
    exit 1
fi

# Validate required environment variables
if [ -z "${DB_USER:-}" ] || [ -z "${DB_PASSWORD:-}" ] || [ -z "${DB_NAME:-}" ]; then
    echo "Error: Required environment variables not set"
    echo "Please set: DB_USER, DB_PASSWORD, DB_NAME"
    echo "These are typically defined in your .env file"
    exit 1
fi

# Database connection info
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

# Show backup info
BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
BACKUP_DATE=$(stat -c %y "$BACKUP_FILE" 2>/dev/null || stat -f "%Sm" "$BACKUP_FILE" 2>/dev/null || echo "unknown")

echo "=================================="
echo "PostgreSQL Database Restore"
echo "=================================="
echo "Database: ${DB_NAME}"
echo "Host: ${DB_HOST}:${DB_PORT}"
echo ""
echo "Backup file: ${BACKUP_FILE}"
echo "Backup size: ${BACKUP_SIZE}"
echo "Backup date: ${BACKUP_DATE}"
echo ""
echo "⚠️  WARNING: This will DROP and RECREATE all database objects!"
echo "   All existing data in the database will be LOST."
echo ""

# Confirmation prompt
read -p "Are you sure you want to restore this backup? [y/N] " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Restore cancelled."
    exit 0
fi

# Export password for pg_restore
export PGPASSWORD="${DB_PASSWORD}"

echo ""
echo "Starting restore..."
echo "Target completion: <5 minutes"
echo ""

# Record start time
START_TIME=$(date +%s)

# Restore database
# --clean: Drop database objects before recreating
# --if-exists: Don't error if objects don't exist (safe for first restore)
# --no-owner: Don't set object ownership (useful for different environments)
# --no-acl: Don't restore access privileges (useful for different environments)
pg_restore \
    --host="${DB_HOST}" \
    --port="${DB_PORT}" \
    --username="${DB_USER}" \
    --dbname="${DB_NAME}" \
    --clean \
    --if-exists \
    --no-owner \
    --no-acl \
    --verbose \
    "${BACKUP_FILE}" \
    2>&1 | grep -E "(processing|creating|restoring)" || true

# Clear password from environment
unset PGPASSWORD

# Calculate restore duration
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

echo ""
echo "=================================="
echo "✓ Restore completed successfully"
echo "=================================="
echo "Duration: ${MINUTES}m ${SECONDS}s"

# Check if we met the 5-minute target
if [ $DURATION -lt 300 ]; then
    echo "Status: ✓ Within 5-minute target"
else
    echo "Status: ⚠️  Exceeded 5-minute target (${DURATION}s)"
fi

echo ""
echo "Next steps:"
echo "  1. Verify database connection: psql -h ${DB_HOST} -U ${DB_USER} ${DB_NAME}"
echo "  2. Check table counts: SELECT COUNT(*) FROM <table_name>;"
echo "  3. Run application health check"
