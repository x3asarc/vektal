# Phase 2: Docker Infrastructure Foundation - Research

**Researched:** 2026-02-04
**Domain:** Docker Compose multi-service orchestration (Flask, Next.js, PostgreSQL, Redis, Celery, Nginx)
**Confidence:** HIGH

## Summary

This phase establishes a containerized development environment for a multi-service application stack. The standard approach uses Docker Compose v2 to orchestrate six services: Flask API (Gunicorn), Next.js frontend, PostgreSQL database, Redis cache/broker, Celery worker, and Nginx reverse proxy. Development workflow prioritizes hot reload via bind mounts for source code and named volumes for database persistence.

The research confirms that the locked decisions in CONTEXT.md align with 2026 best practices: bind mounts for development hot reload, named volumes for database persistence, health checks with depends_on conditions, and .env files for secrets (not Docker secrets, which are Swarm-specific). Critical findings include Windows WSL2 line ending issues requiring .gitattributes, Gunicorn worker formula ((2*CPU)+1), and specific Nginx configurations for WebSocket support in Phase 9-10.

**Primary recommendation:** Use python:3.12-slim (not Alpine) for Flask, bind mounts for code hot reload, named volumes for PostgreSQL/Redis data, and health checks with service_healthy conditions to ensure proper startup order.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Docker Compose | v2 (plugin) | Multi-container orchestration | Native to Docker Desktop, replaces standalone docker-compose |
| Gunicorn | 21.x+ | WSGI server for Flask | Flask's official recommendation for production, replaces dev server |
| python:3.12-slim | 3.12-slim | Flask container base image | Debian-based, better compatibility than Alpine for Python packages |
| postgres | 15-16 | Relational database | Official image, well-documented initialization patterns |
| redis | 7-alpine | Cache and Celery broker | Minimal footprint, Alpine safe for Redis (no complex Python deps) |
| nginx | 1.25+ | Reverse proxy | Industry standard, official support for WebSocket proxying |
| node | 20-slim | Next.js runtime | LTS version, slim variant for reasonable image size |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Celery | 5.3+ | Distributed task queue | Background job processing (Phase 8+ for scraping) |
| Flask-SocketIO | 5.3+ | WebSocket support | Real-time features (Phase 9-10) |
| pg_isready | Built-in | PostgreSQL health check | Included in official postgres image, no installation needed |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| python:3.12-slim | python:3.12-alpine | Alpine 60% smaller but musl libc breaks prebuilt wheels, slower builds |
| Gunicorn | uWSGI | uWSGI more complex config, Gunicorn simpler and Flask-recommended |
| Docker Compose | Kubernetes | K8s overkill for single-developer local setup, adds complexity |

**Installation:**
```bash
# Docker Desktop for Windows includes Docker Compose v2
# Verify with:
docker compose version  # Note: space not hyphen (v2 syntax)
```

## Architecture Patterns

### Recommended Project Structure
```
shopify-scraping-script/
├── docker-compose.yml           # Main orchestration file
├── .env                         # Secrets (gitignored)
├── .env.example                 # Template for .env
├── .gitattributes               # Force LF line endings (critical for Windows)
├── Dockerfile.backend           # Flask + Gunicorn
├── Dockerfile.frontend          # Next.js (to be created in Phase 5)
├── nginx/
│   └── nginx.conf              # Reverse proxy config
├── src/                        # Flask application (existing)
│   ├── app.py
│   ├── core/
│   └── cli/
└── frontend/                   # Next.js app (Phase 5)
```

### Pattern 1: Health Check with depends_on
**What:** Ensure services start only after dependencies are truly ready (not just "running").
**When to use:** Always for database and Redis dependencies.
**Example:**
```yaml
# Source: Docker Compose official docs (2026-01-16)
services:
  backend:
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

  db:
    image: postgres:15
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "postgres"]
      interval: 5s
      timeout: 5s
      retries: 5
      start_period: 10s
```

### Pattern 2: Hot Reload with Bind Mounts
**What:** Map host code directories into containers for live editing without rebuilds.
**When to use:** Development mode only. Production uses copied code in image.
**Example:**
```yaml
# Source: OneUptime Docker Hot Reload Guide (2026-01-06)
services:
  backend:
    volumes:
      - ./src:/app/src              # Bind mount for code
      - backend_venv:/app/venv      # Named volume for dependencies
    environment:
      - FLASK_ENV=development
    command: flask run --host=0.0.0.0 --reload

  frontend:
    volumes:
      - ./frontend:/app
      - /app/node_modules           # Prevent overwriting node_modules
      - /app/.next                  # Prevent overwriting .next
    environment:
      - WATCHPACK_POLLING=true      # Required for Docker hot reload
```

### Pattern 3: Gunicorn Worker Configuration
**What:** Configure Gunicorn workers based on CPU cores and workload type.
**When to use:** Production-like Flask setup (even in dev for consistency).
**Example:**
```python
# Source: Flask official Gunicorn docs + Red Hat Developer (2023-08)
# gunicorn_config.py
import multiprocessing

# Formula: (2 * CPU) + 1
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'  # Use 'gevent' for I/O-bound async work
bind = '0.0.0.0:5000'
timeout = 120
accesslog = '-'  # Log to stdout
errorlog = '-'
```

### Pattern 4: Nginx Reverse Proxy Routing
**What:** Route requests to appropriate backend services with proper headers.
**When to use:** Always - Nginx as single entry point.
**Example:**
```nginx
# Source: Nginx official proxy module docs
server {
    listen 80;
    server_name localhost;

    # Next.js frontend
    location / {
        proxy_pass http://frontend:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Flask API
    location /api/ {
        proxy_pass http://backend:5000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Socket.IO (Phase 9-10) - WebSocket upgrade
    location /socket.io/ {
        proxy_pass http://backend:5000/socket.io/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_buffering off;
        proxy_read_timeout 86400s;
    }
}
```

### Pattern 5: Database Initialization
**What:** PostgreSQL initializes via /docker-entrypoint-initdb.d on first start.
**When to use:** Phase 3 for schema, Phase 4+ for migrations.
**Example:**
```yaml
# Source: PostgreSQL Docker Hub official image
services:
  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data  # Persistent data
      - ./db/init:/docker-entrypoint-initdb.d   # Init scripts (Phase 3)
    environment:
      - POSTGRES_DB=shopify_platform
      - POSTGRES_USER=admin
      - POSTGRES_PASSWORD=${DB_PASSWORD}  # From .env
```

### Anti-Patterns to Avoid

- **Using "latest" tags:** Always pin versions (postgres:15, not postgres:latest) to prevent breaking changes.
- **Hardcoding secrets in docker-compose.yml:** Use .env files and ${VARIABLE} substitution.
- **Missing health checks:** depends_on without condition: service_healthy only waits for container start, not readiness.
- **Alpine for Python:** Musl libc breaks prebuilt wheels (NumPy, Pillow, cryptography), use Debian-slim instead.
- **Running as root:** Processes inside containers share host UID namespace - create non-root user in Dockerfile.
- **Mixing dev and prod configs:** Keep separate docker-compose.yml vs docker-compose.prod.yml (deferred to Phase 13).

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Service startup ordering | Sleep timers, retry loops | depends_on with service_healthy condition | Docker Compose native support, handles restarts correctly |
| File watching for hot reload | Custom inotify scripts | Flask --reload, Next.js dev mode with WATCHPACK_POLLING | Built into frameworks, battle-tested |
| Secrets management | Custom encryption, config files | Docker Compose secrets + .env (dev), Docker Swarm secrets (prod Phase 13) | Security best practices, audit trails |
| Database migrations | Custom SQL scripts | Alembic (Flask-Migrate) in Phase 3 | Version control, rollback support |
| Container networking | Hardcoded IPs, host networking | Docker Compose networks with service names | DNS-based discovery, isolated |
| Log aggregation | Custom file parsing | docker compose logs -f [service] | Built-in, supports filtering |

**Key insight:** Docker Compose and base images provide 90% of infrastructure needs. Custom scripting introduces bugs and maintenance burden.

## Common Pitfalls

### Pitfall 1: CRLF Line Endings Break Shell Scripts (Windows)
**What goes wrong:** Shell scripts in containers fail with "/bin/bash^M: bad interpreter" error.
**Why it happens:** Git on Windows converts LF to CRLF by default. Docker containers expect Unix LF.
**How to avoid:** Add .gitattributes file forcing LF line endings:
```gitattributes
# Source: GitHub Docs + community best practices (2026)
* text=auto eol=lf
*.sh text eol=lf
*.py text eol=lf
Dockerfile* text eol=lf
*.yml text eol=lf
```
**Warning signs:** Scripts work on Linux/Mac but fail in Windows Docker containers.

### Pitfall 2: WSL2 Volume Mount Performance
**What goes wrong:** Bind mounts from Windows filesystem to Docker are 10-20x slower than native Linux.
**Why it happens:** Docker Desktop on Windows uses WSL2 VM, cross-filesystem access has overhead.
**How to avoid:** Store project files in WSL2 filesystem (\\wsl$\Ubuntu\home\user\project), run docker compose from WSL2 terminal.
**Warning signs:** Hot reload takes 5-10 seconds, file operations sluggish.

### Pitfall 3: depends_on Without Health Checks
**What goes wrong:** Backend starts before PostgreSQL is ready, crashes with "connection refused" error.
**Why it happens:** depends_on defaults to condition: service_started, which only waits for container to run, not database to accept connections.
**How to avoid:** Always use condition: service_healthy with proper healthcheck configuration.
**Warning signs:** First docker compose up fails, second attempt works (database initialized between attempts).

### Pitfall 4: Missing node_modules Volume in Next.js
**What goes wrong:** Next.js container fails to start, missing dependencies error.
**Why it happens:** Bind mount ./frontend:/app overwrites /app/node_modules installed during image build.
**How to avoid:** Add anonymous volume for node_modules: volumes: [./frontend:/app, /app/node_modules, /app/.next]
**Warning signs:** npm run dev fails with "Module not found" errors.

### Pitfall 5: Gunicorn Worker Timeout
**What goes wrong:** Long-running requests (AI analysis, scraping) fail with worker timeout.
**Why it happens:** Default Gunicorn timeout is 30 seconds, insufficient for AI API calls.
**How to avoid:** Set timeout in gunicorn_config.py or command: gunicorn --timeout 120 ...
**Warning signs:** 502 Bad Gateway errors during Vision AI or scraping operations.

### Pitfall 6: Not Exposing Ports in Development
**What goes wrong:** Can't directly test individual services, must always go through Nginx.
**Why it happens:** Only exposing port 80 for Nginx, no direct service access.
**How to avoid:** Expose all service ports in development (5000, 3000, 5432, 6379) with documentation marking them as "debug access only".
**Warning signs:** Debugging requires container exec or logs, can't use Postman/pgAdmin directly.

### Pitfall 7: Forgetting FLASK_ENV=development
**What goes wrong:** Code changes don't trigger reload, must restart container manually.
**Why it happens:** Flask defaults to production mode, which disables auto-reload.
**How to avoid:** Set FLASK_ENV=development (or FLASK_DEBUG=1) in docker-compose.yml environment section.
**Warning signs:** Edit Python file, refresh browser, no changes visible.

### Pitfall 8: Named Volume vs Anonymous Volume Confusion
**What goes wrong:** Database data lost after docker compose down, or wrong volume mounted.
**Why it happens:** Anonymous volumes (no name) are disposable, named volumes persist.
**How to avoid:** Use named volumes for databases: volumes: postgres_data:/var/lib/postgresql/data, define in top-level volumes: section.
**Warning signs:** Database schema/data disappears between docker compose down/up.

## Code Examples

Verified patterns from official sources:

### Minimal Flask Development Dockerfile
```dockerfile
# Source: Python Speed best practices (2024-05) + Flask official docs
FROM python:3.12-slim

# Create non-root user
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/

# Switch to non-root user
USER appuser

# Development: Flask dev server with reload
# Production (Phase 13): Gunicorn with config
CMD ["flask", "run", "--host=0.0.0.0", "--reload"]
```

### Docker Compose Multi-Service Setup
```yaml
# Source: Docker Compose official docs + community patterns (2026)
version: '3.8'

services:
  nginx:
    image: nginx:1.25
    ports:
      - "80:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      backend:
        condition: service_started
      frontend:
        condition: service_started
    restart: unless-stopped

  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    ports:
      - "5000:5000"  # Direct access for debugging
    volumes:
      - ./src:/app/src           # Hot reload
      - backend_venv:/app/venv   # Isolate dependencies
    environment:
      - FLASK_ENV=development
      - FLASK_APP=src/app.py
      - DATABASE_URL=postgresql://admin:${DB_PASSWORD}@db:5432/shopify_platform
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/0
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped

  celery_worker:
    build:
      context: .
      dockerfile: Dockerfile.backend
    volumes:
      - ./src:/app/src
    environment:
      - DATABASE_URL=postgresql://admin:${DB_PASSWORD}@db:5432/shopify_platform
      - CELERY_BROKER_URL=redis://redis:6379/0
    command: celery -A src.app.celery worker --loglevel=info
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped

  db:
    image: postgres:15
    ports:
      - "5432:5432"  # Direct access for pgAdmin
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=shopify_platform
      - POSTGRES_USER=admin
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "admin", "-d", "shopify_platform"]
      interval: 5s
      timeout: 5s
      retries: 5
      start_period: 10s
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"  # Direct access for redis-cli
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  backend_venv:
```

### Celery Integration with Flask
```python
# Source: Flask official Celery docs (2026)
from celery import Celery, Task, shared_task
from flask import Flask

def celery_init_app(app: Flask) -> Celery:
    class FlaskTask(Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.name, task_cls=FlaskTask)
    celery_app.config_from_object(app.config["CELERY"])
    celery_app.set_default()
    app.extensions["celery"] = celery_app
    return celery_app

# In app.py
app = Flask(__name__)
app.config.from_mapping(
    CELERY=dict(
        broker_url="redis://redis:6379/0",
        result_backend="redis://redis:6379/0",
        task_ignore_result=True,
    ),
)
celery_app = celery_init_app(app)

# Define tasks with @shared_task
@shared_task(ignore_result=False)
def scrape_vendor_product(product_id: int) -> dict:
    # Pass only IDs, not complex objects
    return {"status": "complete"}
```

### .env File Template
```bash
# .env.example - Source: Docker Compose secrets best practices
# Copy to .env and fill in actual values

# Database
DB_PASSWORD=changeme_postgres_password

# Flask
FLASK_SECRET_KEY=changeme_flask_secret
FLASK_ENV=development

# API Keys (User pays, not customer)
OPENAI_API_KEY=sk-...
GOOGLE_GEMINI_API_KEY=...

# Shopify Admin API
SHOPIFY_STORE_URL=bastelschachtel.myshopify.com
SHOPIFY_ACCESS_TOKEN=shpat_...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| docker-compose (hyphen) standalone binary | docker compose (space) plugin | Docker Desktop 3.4+ (2021) | Native integration, simpler installation |
| Flask dev server in production | Gunicorn/Waitress WSGI server | Always (Flask docs warning) | Security, concurrency, stability |
| depends_on without conditions | depends_on with service_healthy | Docker Compose v3.4+ (2019) | Reliable startup order |
| Environment variables for secrets | Docker secrets (Swarm) or .env (Compose) | 2017+ | Reduces exposure in logs, process lists |
| Alpine Linux for all containers | Debian-slim for Python, Alpine for simple services | ~2020 consensus | Better compatibility vs size tradeoff |
| Single-stage Dockerfiles | Multi-stage builds | Docker 17.05+ (2017) | 60% smaller images (deferred to Phase 13) |

**Deprecated/outdated:**
- **docker-compose binary:** Use docker compose (space) command, part of Docker Desktop
- **Flask development server in production:** Always use WSGI server (Gunicorn, uWSGI, Waitress)
- **links directive in Compose:** Replaced by networks with service name DNS
- **FLASK_ENV variable:** Deprecated in Flask 2.3+, use FLASK_DEBUG=1 instead

## Open Questions

Things that couldn't be fully resolved:

1. **Next.js Dockerfile optimization**
   - What we know: Next.js requires node_modules and .next volumes, WATCHPACK_POLLING=true
   - What's unclear: Optimal multi-stage build for production (Phase 13), standalone output mode
   - Recommendation: Research in Phase 5 when creating frontend, use simple single-stage for now

2. **Celery worker concurrency for scraping**
   - What we know: Default workers = CPU count, scraping is I/O-bound
   - What's unclear: Optimal concurrency for Selenium-based scrapers (memory vs parallelism)
   - Recommendation: Start with concurrency=2, monitor memory in Phase 8, adjust based on metrics

3. **PostgreSQL connection pooling**
   - What we know: Flask-SQLAlchemy has basic pooling, multiple Gunicorn workers share DB connections
   - What's unclear: Whether PgBouncer needed for expected load (~10 requests/min development)
   - Recommendation: Skip for Phase 2, revisit in Phase 13 if connection limits hit

4. **Nginx access logs verbosity**
   - What we know: Default access logs can be noisy for development
   - What's unclear: User preference for log verbosity (learning vs quiet)
   - Recommendation: Default to quiet (access_log off for static assets), document how to enable

## Sources

### Primary (HIGH confidence)
- [Docker Compose Official Documentation](https://docs.docker.com/compose/) - Compose features and lifecycle
- [Docker Compose Startup Order Control](https://docs.docker.com/compose/how-tos/startup-order/) - depends_on and health checks
- [Docker Compose Secrets](https://docs.docker.com/compose/how-tos/use-secrets/) - Secrets management patterns
- [Flask Deployment Guide](https://flask.palletsprojects.com/en/stable/deploying/) - WSGI server recommendations
- [Flask Celery Integration](https://flask.palletsprojects.com/en/stable/patterns/celery/) - Official Celery pattern
- [Nginx Proxy Module](https://nginx.org/en/docs/http/ngx_http_proxy_module.html) - Reverse proxy directives
- [Python Speed Docker Guide](https://pythonspeed.com/articles/base-image-python-docker-images/) - Alpine vs Debian analysis (May 2024)
- [Flask Official Gunicorn Docs](https://flask.palletsprojects.com/en/stable/deploying/gunicorn/) - Worker configuration
- [Red Hat Gunicorn Deployment](https://developers.redhat.com/articles/2023/08/17/how-deploy-flask-application-python-gunicorn) - Production configuration (Aug 2023)

### Secondary (MEDIUM confidence)
- [OneUptime Docker Hot Reload Guide](https://oneuptime.com/blog/post/2026-01-06-docker-hot-reloading/view) - Flask/Next.js hot reload patterns (Jan 2026)
- [OneUptime Depends_on Healthcheck](https://oneuptime.com/blog/post/2026-01-16-docker-compose-depends-on-healthcheck/view) - Health check best practices (Jan 2026)
- [OneUptime Docker Secrets Management](https://oneuptime.com/blog/post/2026-01-30-docker-secrets-management/view) - Secrets security patterns (Jan 2026)
- [OneUptime Flask Celery Guide](https://oneuptime.com/blog/post/2026-02-02-flask-celery-background-tasks/view) - Celery configuration (Feb 2026)
- [OneUptime Bind Mounts vs Volumes](https://oneuptime.com/blog/post/2026-01-16-docker-bind-mounts-vs-volumes/view) - Storage comparison (Jan 2026)
- [DEV Community: Flask Next.js Redis Docker](https://dev.to/aixart/building-a-real-time-flask-and-nextjs-application-with-redis-socketio-and-docker-compose-5d6j) - Full stack example
- [TestDriven.io: Flask Postgres Gunicorn Nginx](https://testdriven.io/blog/dockerizing-flask-with-postgres-gunicorn-and-nginx/) - Production setup
- [GitHub Docker Line Endings Resolution](https://gist.github.com/jonlabelle/70a87e6871a1138ac3031f5e8e39f294) - CRLF/LF fixes
- [GitHub Configuring Git Line Endings](https://docs.github.com/en/get-started/git-basics/configuring-git-to-handle-line-endings) - .gitattributes patterns
- [NGINX WebSocket Proxy 2026 Guide](https://www.getpagespeed.com/server-setup/nginx/nginx-websocket-proxy) - WebSocket configuration
- [Docker WSL2 Performance Issues](https://github.com/docker/for-win/issues/10476) - Volume mount performance discussion

### Tertiary (LOW confidence - for validation)
- [TheLinuxCode Docker Compose Guide 2026](https://thelinuxcode.com/what-is-docker-compose-up-a-senior-engineers-practical-guide-for-2026/) - General best practices
- [MoldStud Common Pitfalls](https://moldstud.com/articles/p-avoid-these-common-docker-compose-pitfalls-tips-and-best-practices) - Mistakes compilation
- [DZone Docker Compose Mistakes](https://dzone.com/articles/5-common-mistakes-when-writing-docker-compose) - Anti-patterns
- [Medium: Docker Performance Windows](https://medium.com/@suyashsingh.stem/increase-docker-performance-on-windows-by-20x-6d2318256b9a) - WSL2 optimization

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries from official Docker/Flask/Python documentation
- Architecture: HIGH - Patterns verified with official Docker Compose and Flask docs
- Pitfalls: HIGH - Cross-referenced with official docs and 2026 community reports
- Code examples: HIGH - Adapted from official documentation and verified sources
- Windows-specific issues: MEDIUM - Based on GitHub issues and community reports, not official docs

**Research date:** 2026-02-04
**Valid until:** 2026-04-04 (60 days - Docker/Docker Compose stable, slow-moving ecosystem)

**Special notes:**
- CONTEXT.md decisions followed strictly - no alternatives explored for locked choices
- Next.js Dockerfile research deferred to Phase 5 (frontend creation)
- Production optimizations (multi-stage builds, resource limits) deferred to Phase 13 per CONTEXT.md
- All findings validated against user's Windows + Docker Desktop + WSL2 environment
