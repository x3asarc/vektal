# Phase 2: Docker Infrastructure Foundation - Context

**Gathered:** 2026-02-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Establish containerized service architecture for the entire platform (backend, frontend, database, job queue, reverse proxy). Focus on development workflow - local docker-compose setup with hot reload, good debugging, and production-like structure. SSL, deployment automation, and rollback strategies deferred to Phase 13.

</domain>

<decisions>
## Implementation Decisions

### Container Architecture
- **All containers from day one**: Flask backend, Next.js frontend, PostgreSQL, Redis, Celery worker, Nginx reverse proxy
- **Complete infrastructure in Phase 2**: Later phases add features into this structure, not new containers
- **Separation of concerns**: Backend/frontend develop independently, supporting services isolate failures

### Development Workflow
- **Hot reload via volume mounts**: Local code folders map into containers (src/ → Flask, frontend/ → Next.js)
- **Change Python file → Flask auto-reloads**: No container rebuild needed for code changes
- **Development-first approach**: Production features (health checks, rollback, monitoring) belong in Phase 13

### Secrets Management (Business Model Decision)
- **You pay for APIs, bill users via tiers**: Your OpenAI/Gemini/Vision API keys in backend
- **Users provide only Shopify credentials**: Stored encrypted in PostgreSQL per-user
- **Standard SaaS model**: Low friction for users, you control costs via tier limits
- **Implementation**: .env file (gitignored) for your API keys, environment variables for config
- **Future BYOK option**: Phase 12+ can add optional user-provided API keys for unlimited usage

### Nginx Reverse Proxy
- **Local development focus**: Phase 2 targets localhost, SSL/domain setup deferred to Phase 13
- **Routing strategy**:
  - `/api/*` → Flask backend
  - `/*` → Next.js frontend
  - WebSocket connections handled for Phase 9-10
- **Primary access point**: Nginx on port 80 (`localhost`)

### Port Exposure (Development Mode)
- **All services exposed for debugging**:
  - Nginx: port 80 (primary interface)
  - Flask: port 5000 (direct API testing)
  - Next.js: port 3000 (direct frontend access)
  - PostgreSQL: port 5432 (database queries)
  - Redis: port 6379 (job queue inspection)
- **Rationale**: Learning phase - ability to test each service individually aids understanding
- **Documentation**: Mark Nginx as primary, others as "debug access"
- **Production**: Phase 13 removes debug ports, locks down to Nginx-only

### Data Persistence
- **PostgreSQL data persists via Docker volumes**: Database survives `docker-compose down`
- **SQLite migration note**: Existing SQLite (Pentart catalog) migrates to PostgreSQL in Phase 3
- **Volume strategy**: Named volumes for databases, bind mounts for code (hot reload)

### Database Initialization
- **Empty database on first start**: PostgreSQL creates tables from models, no seed data
- **Natural progression**:
  - Phase 3: Migration scripts + schema
  - Phase 4: User connects test store (10-30 products) via OAuth
  - Phase 8: Products import into PostgreSQL
- **Test store available**: User has second Shopify store for testing (different niche, small catalog)

### Restart Policies & Debugging
- **Simple restart policies**: `restart: unless-stopped` for all services
- **Minimal logging by default**: Quiet console, use `docker-compose logs -f [service]` when debugging
- **No automatic rollback**: Development mode - see errors immediately and fix
- **Production resilience**: Phase 13 adds health checks, monitoring, rollback automation

### Windows Environment Considerations
- **Docker Desktop confirmed installed**: User ready to go
- **File path handling**: Use relative paths in docker-compose.yml (avoid Windows absolute paths)
- **Line endings**: Add .gitattributes to prevent CRLF issues in shell scripts
- **Performance awareness**: Windows → Docker → Linux may be slower for file I/O (acceptable for dev)

### Codebase Structure
- **Containerize existing layout**: Keep src/ structure from Phase 1 cleanup
- **Minimal restructuring**: Only move files if necessary for container efficiency
- **Update references**: If files move, update all imports/paths (learned from Phase 1.1)
- **Flask status**: Some Flask code exists but may be partial/experimental
- **SQLite context**: Currently stores Pentart catalog (CSV → SQLite), not user auth yet

### Claude's Discretion
- Exact docker-compose.yml structure and service naming
- Dockerfile optimization (layer caching, image size)
- Environment variable naming conventions
- Network configuration details (bridge vs host)
- Volume mount paths and permissions
- Exact logging format and verbosity levels

</decisions>

<specifics>
## Specific Ideas

- **Windows WSL2 requirement**: Ensure documentation mentions WSL2 dependency for Docker Desktop
- **Test store context**: 10-30 products, different niche from main store (bastelschachtel), will be connected in Phase 4
- **Main store**: ~6000 products (bastelschachtel) - NOT used for testing due to risk
- **Phase 1 completion**: Scripts archived, tests organized, ARCHITECTURE.md exists, scraper strategy documented
- **Learning priority**: User is beginner with Docker - favor clarity and good documentation over advanced features
- **Ports analogy**: "Apartment building" explanation resonated - use similar clear analogies in docs

</specifics>

<deferred>
## Deferred Ideas

- **Automatic rollback on container failure** - Production feature, belongs in Phase 13
- **SSL/TLS certificate setup** - Production deployment, Phase 13
- **Domain configuration** - Production deployment, Phase 13
- **Health check endpoints with automatic recovery** - Production monitoring, Phase 13
- **Resource limits (CPU/memory constraints)** - Performance optimization, Phase 13
- **Multi-stage Docker builds** - If needed for optimization, address in Phase 13
- **Container orchestration (Kubernetes)** - Beyond MVP scope, future scaling consideration
- **Optional user-provided API keys (BYOK)** - Phase 12+ feature for power users

</deferred>

---

*Phase: 02-docker-infrastructure-foundation*
*Context gathered: 2026-02-04*
