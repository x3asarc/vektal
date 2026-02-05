# Docker Quickstart Guide

This guide explains how to run the Shopify Multi-Supplier Platform using Docker.

## Prerequisites

- **Docker Desktop** installed and running
  - Windows: [Download Docker Desktop](https://www.docker.com/products/docker-desktop/)
  - Must have WSL2 enabled (Docker Desktop installer handles this)
- **.env file** configured (copy from .env.example)

## Quick Start

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Edit .env with your actual values
# At minimum, set DB_PASSWORD to something secure

# 3. Start all services
docker compose up

# 4. Access the application
# Primary: http://localhost (via Nginx)
# API only: http://localhost:5000/health
```

## Understanding the Services

Think of Docker Compose like an apartment building where each service is a tenant:

| Service | What it does | Port | URL |
|---------|--------------|------|-----|
| **nginx** | Front door - routes traffic | 80 | http://localhost |
| **backend** | Flask API - business logic | 5000 | http://localhost:5000 |
| **frontend** | Next.js UI (placeholder) | 3000 | http://localhost:3000 |
| **db** | PostgreSQL database | 5432 | localhost:5432 |
| **redis** | Job queue & cache | 6379 | localhost:6379 |
| **celery_worker** | Background jobs | - | (no direct access) |

### Service Dependencies

```
                    +---------+
                    |  nginx  | <- Entry point (port 80)
                    +----+----+
                         |
           +-------------+-------------+
           |             |             |
           v             v             v
      +---------+   +---------+   +---------+
      | backend |   |frontend |   |  (API)  |
      +----+----+   +---------+   +---------+
           |
     +-----+-----+
     |           |
     v           v
+---------+ +---------+
|   db    | |  redis  |
+---------+ +---------+
     ^           ^
     |           |
     +-----+-----+
           |
    +------+------+
    |celery_worker|
    +-------------+
```

## Common Commands

### Starting and Stopping

```bash
# Start all services (with logs in terminal)
docker compose up

# Start in background (detached mode)
docker compose up -d

# Stop all services
docker compose down

# Stop and remove all data (fresh start)
docker compose down -v
```

### Viewing Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f celery_worker

# Last 100 lines
docker compose logs --tail=100 backend
```

### Checking Status

```bash
# Service status
docker compose ps

# Health check
curl http://localhost:5000/health
```

### Development Workflow

**Hot Reload (no restart needed):**
- Edit files in `src/` -> Flask auto-reloads
- Edit files in `frontend/` -> Next.js auto-reloads

**When you DO need to restart:**
- Changed `requirements.txt` -> `docker compose up --build backend`
- Changed `Dockerfile.backend` -> `docker compose up --build backend`
- Changed `docker-compose.yml` -> `docker compose up`

### Database Access

```bash
# Connect to PostgreSQL
docker compose exec db psql -U admin -d shopify_platform

# Or use a GUI tool with these credentials:
# Host: localhost
# Port: 5432
# User: admin
# Password: (from your .env file)
# Database: shopify_platform
```

### Redis Access

```bash
# Connect to Redis CLI
docker compose exec redis redis-cli

# Test connection
docker compose exec redis redis-cli ping
# Should return: PONG
```

## Troubleshooting

### "Port already in use"

Another application is using that port. Options:
1. Stop the other application
2. Change the port in `.env` (e.g., `FLASK_PORT=5001`)

### "Cannot connect to database"

```bash
# Check if db service is healthy
docker compose ps db

# View database logs
docker compose logs db

# Common fix: wait for db to be ready
docker compose down
docker compose up
```

### "Backend container keeps restarting"

```bash
# Check error logs
docker compose logs backend

# Common causes:
# - Missing .env file (copy from .env.example)
# - Invalid Python syntax in src/
# - Missing module import
```

### "Changes not reflected (hot reload not working)"

1. Make sure you're editing files in the correct directory
2. Check the service is using bind mounts (not the built image)
3. Try: `docker compose restart backend`

### Windows-specific: Line Ending Issues

If you see errors like "bad interpreter" or "\\r":
```bash
# Ensure .gitattributes is applied
git add --renormalize .
git status

# Or manually convert a file
dos2unix filename
```

## Performance Notes

- **Windows performance:** Docker runs in WSL2 VM, so file I/O between Windows and Linux has some overhead
- **First start is slow:** Downloading images and building takes time, subsequent starts are fast
- **Memory usage:** This stack uses ~2GB RAM with all services running

## Next Steps

- Configure your actual API keys in `.env`
- Try the API: `curl http://localhost:5000/health`
- Read the [Architecture documentation](../../ARCHITECTURE.md)

---
*Phase 2: Docker Infrastructure Foundation*
*Created: 2026-02-05*
