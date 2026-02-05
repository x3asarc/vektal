# Docker Secrets Guide

## What Are Docker Secrets?

Docker secrets provide a secure way to handle sensitive data (API keys, passwords, tokens) in containerized environments. Unlike environment variables, secrets:

- **Are NOT visible in `docker inspect` output** - prevents accidental exposure
- **Are mounted as files** at `/run/secrets/{secret_name}` inside containers
- **Are encrypted at rest** (in Docker Swarm mode)
- **Follow principle of least privilege** - only specified services can access them

## Why This Matters

**The Problem:**
```bash
# Without secrets - API keys exposed
docker inspect shopifyscrapingscript-backend-1 | grep GEMINI_API_KEY
# Output: "GEMINI_API_KEY=sk-your-actual-api-key-here"  ⚠️ EXPOSED
```

**The Solution:**
```bash
# With secrets - values hidden
docker inspect shopifyscrapingscript-backend-1 | grep GEMINI_API_KEY
# Output: "GEMINI_API_KEY="  ✓ SAFE
```

## Setup Instructions

### 1. Create Secret Files

Create a file for each secret in the `secrets/` directory:

```bash
# Navigate to project root
cd "C:\Users\Hp\Documents\Shopify Scraping Script"

# Database password
echo "your-secure-db-password" > secrets/DB_PASSWORD

# Flask session key (generate random 32-byte hex)
python -c "import os; print(os.urandom(32).hex())" > secrets/FLASK_SECRET_KEY

# AI service keys
echo "your-gemini-api-key" > secrets/GEMINI_API_KEY
echo "your-openrouter-api-key" > secrets/OPENROUTER_API_KEY

# Shopify credentials
echo "your-shopify-api-key" > secrets/SHOPIFY_API_KEY
echo "your-shopify-api-secret" > secrets/SHOPIFY_API_SECRET
```

**Important:** The `secrets/` directory is gitignored. Never commit actual secret values to version control.

### 2. Run with Secrets Overlay

Use the `-f` flag to merge the secrets overlay with the base configuration:

```bash
docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d
```

This command:
1. Loads base config from `docker-compose.yml`
2. Overlays secrets config from `docker-compose.secrets.yml`
3. Mounts secret files to `/run/secrets/` in containers
4. Application reads from files instead of environment variables

### 3. Verify Secrets Are Hidden

After starting the stack:

```bash
# Check that secrets are NOT in environment (should show empty values)
docker inspect shopifyscrapingscript-backend-1 | grep -E "GEMINI_API_KEY|SHOPIFY_API_SECRET"

# Verify app can read secrets from files
docker compose exec backend python -c "from src.core.secrets import get_secret; print(get_secret('GEMINI_API_KEY'))"
```

Expected: `docker inspect` shows empty values, but the Python test prints the actual key.

## How It Works

### File-Based Secret Storage

Secrets are mounted as read-only files inside containers:

```
/run/secrets/
├── DB_PASSWORD
├── FLASK_SECRET_KEY
├── GEMINI_API_KEY
├── OPENROUTER_API_KEY
├── SHOPIFY_API_KEY
└── SHOPIFY_API_SECRET
```

### Application Secret Reading

The `src/core/secrets.py` module provides a `get_secret()` function that:

1. **First tries** to read from `/run/secrets/{name}` (Docker secrets)
2. **Falls back** to `os.getenv(name)` (environment variables)
3. **Returns** a default value if neither source has the secret

This design works in both Docker (with secrets) and local development (with `.env`).

**Example:**
```python
from src.core.secrets import get_secret

# Works in Docker (reads file) AND locally (reads env var)
api_key = get_secret("GEMINI_API_KEY")
```

### PostgreSQL Native Secret Support

PostgreSQL natively supports file-based passwords via `POSTGRES_PASSWORD_FILE`. The secrets overlay sets:

```yaml
environment:
  - POSTGRES_PASSWORD_FILE=/run/secrets/DB_PASSWORD
  - POSTGRES_PASSWORD=  # Empty to disable env var
```

## Development vs Production

### Local Development (without Docker)

Run Flask/Celery directly with `.env` file:

```bash
# .env file provides secrets as environment variables
flask run
```

The `get_secret()` function automatically falls back to environment variables.

### Development (with Docker, no secrets)

Use base `docker-compose.yml` with `.env` file:

```bash
docker compose up
```

Environment variables passed from `.env` → containers. Less secure but simpler for development.

### Production (with Docker secrets)

Use secrets overlay:

```bash
docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d
```

Secrets read from files. More secure - prevents exposure via `docker inspect`.

## Troubleshooting

### "No such file or directory: secrets/GEMINI_API_KEY"

**Cause:** Secret file doesn't exist.

**Solution:** Create the missing secret file:
```bash
echo "your-api-key-here" > secrets/GEMINI_API_KEY
```

### "Permission denied: /run/secrets/DB_PASSWORD"

**Cause:** Container user doesn't have read permission on secret file.

**Solution:** This shouldn't happen with Docker Compose secrets (they're mounted with correct permissions). If it does, check your secret file permissions:
```bash
ls -l secrets/
# Should be readable by your user
```

### Application still reads from environment variables

**Cause:** Forgot to use secrets overlay, or secrets overlay not loaded correctly.

**Solution:** Ensure you're using `-f docker-compose.secrets.yml`:
```bash
docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d
```

Verify with:
```bash
docker compose -f docker-compose.yml -f docker-compose.secrets.yml config | grep -A 5 "secrets:"
```

### "Secret not found" but file exists

**Cause:** Secret file has wrong name or whitespace issues.

**Solution:**
- Check filename matches exactly (case-sensitive)
- Remove trailing newlines if causing issues (the app strips them automatically)

## Further Reading

- [Docker Secrets Official Documentation](https://docs.docker.com/engine/swarm/secrets/)
- [Docker Compose Secrets Reference](https://docs.docker.com/compose/compose-file/compose-file-v3/#secrets)
- [Best Practices for Secrets Management](https://docs.docker.com/develop/security-best-practices/#manage-secrets)
