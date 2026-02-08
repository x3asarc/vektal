#!/bin/bash
#
# Database Backup Script
# Creates compressed PostgreSQL backups with automatic retention management.
#
# Usage:
#   ./scripts/backup_db.sh
#
# Features:
# - Custom format with compression level 6 (good balance of speed/size)
# - Timestamped filenames (YYYYMMDD_HHMMSS)
# - Automatic retention (keeps last 5 backups by default)
# - Backup size reporting
# - Validates required environment variables

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_COUNT="${RETENTION_COUNT:-5}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.dump"

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

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

echo "=================================="
echo "PostgreSQL Database Backup"
echo "=================================="
echo "Database: ${DB_NAME}"
echo "Host: ${DB_HOST}:${DB_PORT}"
echo "Backup file: ${BACKUP_FILE}"
echo ""

# Export password for pg_dump (avoids interactive prompt)
export PGPASSWORD="${DB_PASSWORD}"

# Create backup with custom format and compression
echo "Creating backup..."
pg_dump \
    --host="${DB_HOST}" \
    --port="${DB_PORT}" \
    --username="${DB_USER}" \
    --dbname="${DB_NAME}" \
    --format=custom \
    --compress=6 \
    --verbose \
    --file="${BACKUP_FILE}" \
    2>&1 | grep -v "NOTICE:" || true  # Suppress NOTICEs, show errors

# Clear password from environment
unset PGPASSWORD

# Check if backup was created successfully
if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file was not created"
    exit 1
fi

# Show backup size
BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo ""
echo "✓ Backup completed successfully"
echo "  Size: ${BACKUP_SIZE}"
echo ""

# Cleanup old backups (keep last N)
echo "Managing backup retention (keeping last ${RETENTION_COUNT} backups)..."
cd "$BACKUP_DIR"
ls -t backup_*.dump 2>/dev/null | tail -n +$((RETENTION_COUNT + 1)) | xargs -r rm -v
cd - > /dev/null

# List current backups
echo ""
echo "Current backups in ${BACKUP_DIR}:"
ls -lh "$BACKUP_DIR"/backup_*.dump 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}' || echo "  (none)"

echo ""
echo "✓ Backup process complete"
