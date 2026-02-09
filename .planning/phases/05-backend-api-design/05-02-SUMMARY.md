---
phase: 05-backend-api-design
plan: 02
type: summary
completed: 2026-02-09
duration: 14 minutes

dependencies:
  requires:
    - 05-01  # API Core Infrastructure (errors, pagination, rate limiting)
  provides:
    - OpenAPI-enabled Flask app with Swagger UI
    - Versioned API routes under /api/v1/
    - Backward-compatible legacy routes
  affects:
    - 05-03  # SSE Infrastructure (will use OpenAPI app)
    - 05-04  # Domain API Routes (will register under /api/v1/)

tech_stack:
  added:
    - flask-openapi3==4.3.1  # Automatic OpenAPI schema generation
    - flask-compress==1.23    # Response compression (gzip)
    - flask-limiter==4.1.1    # Rate limiting (already in requirements.txt)
  patterns:
    - App factory pattern for testability
    - Blueprint registration with versioned URL prefixes
    - Session-based authentication (SessionAuth security scheme)
    - CORS configuration for cross-origin requests

key_files:
  created:
    - src/api/app.py          # OpenAPI app factory with Swagger UI
  modified:
    - src/api/__init__.py     # Blueprint registration function
    - src/app.py              # Refactored to use OpenAPI factory

decisions:
  - id: openapi-documentation
    what: Use Flask-OpenAPI3 for automatic API documentation
    why: Interactive Swagger UI enables developers to explore and test all endpoints without manual documentation
    alternatives: Manual Swagger YAML, Flasgger, Connexion
    trade_offs: Flask-OpenAPI3 chosen for Pydantic integration and modern OpenAPI 3.0 support

  - id: versioned-api-routes
    what: All API routes under /api/v1/ prefix
    why: Enables future API versioning (v2, v3) without breaking existing clients
    alternatives: Versioning via headers, subdomain-based versioning
    trade_offs: URL-based versioning chosen for simplicity and RESTful conventions

  - id: legacy-route-preservation
    what: Maintain backward-compatible routes (/auth, /billing, /oauth, /webhooks)
    why: Existing frontend and webhooks expect these routes; breaking changes avoided
    alternatives: Immediate migration to /api/v1/, deprecation warnings
    trade_offs: Dual registration increases routes but ensures zero downtime migration

  - id: session-auth-openapi
    what: SessionAuth security scheme in OpenAPI spec
    why: Aligns with existing Flask-Login implementation (session cookie authentication)
    alternatives: JWT tokens, API keys
    trade_offs: Session cookies work for embedded Shopify app, JWT would require token refresh logic

metrics:
  tasks_completed: 3/3
  commits: 3
  files_created: 1
  files_modified: 2
  routes_added: 21  # V1 API routes (auth, billing, oauth, webhooks)
  routes_preserved: 24  # Legacy routes for backward compatibility
---

# Phase 05 Plan 02: API Routes and OpenAPI Documentation Summary

**One-liner:** Integrated Flask-OpenAPI3 with Swagger UI at /api/docs, versioned API routes under /api/v1/, and backward-compatible legacy routes

## What Was Built

### 1. OpenAPI App Factory (src/api/app.py)
Created Flask application factory with OpenAPI 3.0 specification:
- **Swagger UI at /api/docs:** Interactive documentation for all endpoints
- **OpenAPI JSON at /api/docs/openapi.json:** Machine-readable API specification
- **Security schemes:** SessionAuth (cookie-based authentication)
- **Tag definitions:** 6 tags for endpoint grouping (auth, billing, jobs, products, vendors, oauth)
- **Response compression:** gzip compression for JSON responses >500 bytes (level 6)
- **Rate limiting:** Redis-backed tier-based rate limiting (100/500/2000 per day)
- **Error handling:** RFC 7807 Problem Details for all errors

### 2. Blueprint Registration (src/api/__init__.py)
Centralized blueprint registration with versioning:
- **V1 API routes:** /api/v1/auth, /api/v1/oauth, /api/v1/billing, /api/v1/webhooks
- **Legacy routes:** /auth, /oauth, /billing, /webhooks (backward compatibility)
- **CORS configuration:** localhost:3000 (Next.js), localhost:5000 (Flask)
- **21 V1 routes registered:** 13 auth, 4 OAuth, 4 billing/webhooks

### 3. Main App Refactor (src/app.py)
Migrated from `create_app()` to `create_openapi_app()`:
- **Removed redundant code:** Blueprint registration, CORS, email config (now in factory)
- **Preserved all routes:** Jobs API, pipeline endpoints, Shopify webhooks, helper functions
- **Added SSE support:** threaded=True for Server-Sent Events
- **Configuration centralized:** Database, session, login manager, mail all in factory

## Technical Achievements

### OpenAPI 3.0 Integration
```python
info = Info(
    title="Shopify Multi-Supplier API",
    version="1.0.0",
    description="RESTful API for multi-supplier Shopify product management with AI-powered enrichment"
)

security_schemes = {
    "SessionAuth": {
        "type": "apiKey",
        "in": "cookie",
        "name": "session",
        "description": "Flask session cookie authentication (set after /api/v1/auth/login)"
    }
}
```

### Versioned URL Structure
- **/api/v1/auth/login** → Login endpoint (v1)
- **/api/v1/auth/logout** → Logout endpoint (v1)
- **/api/v1/billing/plans** → Billing plans (v1)
- **/api/v1/oauth/initiate** → Shopify OAuth (v1)
- **/auth/login** → Legacy login (backward compatibility)
- **/billing/plans** → Legacy billing (backward compatibility)

### Response Compression
```python
app.config.setdefault("COMPRESS_MIMETYPES", [
    "text/html", "text/css", "text/xml",
    "application/json", "application/javascript",
    "application/problem+json"  # RFC 7807 error responses
])
app.config.setdefault("COMPRESS_LEVEL", 6)  # Balance speed vs compression
app.config.setdefault("COMPRESS_MIN_SIZE", 500)  # Only compress >500 bytes
```

## Deviations from Plan

None - plan executed exactly as written.

## Testing & Verification

### Verification Results
✅ **1. Application starts successfully**
- App name: `src.api.app`
- Flask-OpenAPI3 initialization successful

✅ **2. Swagger UI route exists at /api/docs**
- Interactive documentation accessible
- All endpoints grouped by tags

✅ **3. OpenAPI JSON available at /api/docs/openapi.json**
- Machine-readable specification
- Compatible with code generation tools

✅ **4. All existing routes still functional**
- 21 V1 API routes registered
- 24 legacy routes preserved
- 4 jobs routes operational
- 2 pipeline routes operational

✅ **5. CORS headers present on /api/* responses**
- localhost:3000 and localhost:5000 allowed
- Credentials supported for session cookies

### Import Verification
```bash
$ python -c "from src.api.app import create_openapi_app, auth_tag, billing_tag"
# Imports successful

$ python -c "from src.api import register_v1_blueprints"
# Import successful

$ python -c "from src.app import app; print(app.name)"
# App created: src.api.app

$ python -c "from src.app import app; print(list(app.blueprints.keys()))"
# Blueprints: ['openapi', 'auth', 'oauth', 'checkout_v1', 'billing_v1',
#              'webhooks', 'auth_legacy', 'oauth_legacy', 'checkout_legacy',
#              'billing_legacy', 'webhooks_legacy']
```

## Decisions Made

### 1. Flask-OpenAPI3 over alternatives
**Decision:** Use Flask-OpenAPI3 for automatic API documentation

**Rationale:**
- Pydantic v2 integration (already used in Phase 2.1 for vendor configs)
- Modern OpenAPI 3.0 support (not just Swagger 2.0)
- Automatic schema generation from type hints
- Interactive Swagger UI out of the box

**Alternatives considered:**
- Manual Swagger YAML (high maintenance burden)
- Flasgger (Swagger 2.0 only, less Pydantic support)
- Connexion (opinionated, requires spec-first design)

### 2. URL-based API versioning
**Decision:** Version APIs via URL prefix (/api/v1/)

**Rationale:**
- RESTful convention (most widely adopted)
- Simple to implement and understand
- Clear separation in logs and monitoring
- Enables parallel v1/v2 support during migrations

**Alternatives considered:**
- Header-based versioning (Accept: application/vnd.api.v1+json) - harder for browser testing
- Subdomain-based (v1.api.example.com) - requires DNS/SSL configuration

### 3. Dual registration for backward compatibility
**Decision:** Register blueprints twice (v1 + legacy)

**Rationale:**
- Zero downtime migration (no breaking changes)
- Existing Stripe webhooks expect /webhooks/stripe
- Frontend can migrate gradually to /api/v1/
- Legacy routes can be deprecated later with warnings

**Trade-offs:**
- Increases route count (45 total vs 21 v1-only)
- More complexity in URL routing
- Benefits outweigh costs: production stability maintained

### 4. Session-based authentication in OpenAPI
**Decision:** Use SessionAuth security scheme (cookie authentication)

**Rationale:**
- Aligns with existing Flask-Login implementation
- Session cookies already set by /auth/login
- Works for embedded Shopify app (no CORS issues)
- No need for token refresh logic

**Alternatives considered:**
- JWT Bearer tokens (requires token refresh, more complex)
- API keys (less secure for embedded apps)
- OAuth2 implicit flow (overkill for single-tenant app)

## Integration Points

### Upstream Dependencies (requires)
- **05-01 (API Core Infrastructure):**
  - `src.api.core.errors.register_error_handlers()` - RFC 7807 error handling
  - `src.api.core.rate_limit.create_limiter()` - Tier-based rate limiting
  - Both integrated into `create_openapi_app()` factory

### Downstream Consumers (provides)
- **05-03 (SSE Infrastructure):**
  - Will use `create_openapi_app()` for consistent app initialization
  - SSE endpoints will be documented in Swagger UI

- **05-04 (Domain API Routes):**
  - Will register products/jobs/vendors blueprints under /api/v1/
  - Will use OpenAPI decorators for automatic schema generation

### Cross-Phase Integration
- **Phase 04 (Authentication):** All auth/billing/oauth routes now accessible at /api/v1/
- **Phase 06 (Frontend):** Next.js frontend will use /api/v1/ routes + Swagger UI for API reference

## Performance Characteristics

### Response Compression
- **Compression level:** 6 (balance speed vs size)
- **Minimum size:** 500 bytes (avoid overhead for small responses)
- **Mimetypes:** JSON, HTML, CSS, JavaScript, RFC 7807 errors
- **Expected savings:** 60-80% reduction in response size for JSON

### Rate Limiting
- **Storage:** Redis (distributed across containers)
- **Strategy:** Fixed-window (simple, predictable)
- **Key function:** User ID for authenticated, IP for anonymous
- **Limits:** Tier-based (100/500/2000 per day)

### Blueprint Registration
- **Total routes:** 45 (21 v1 + 24 legacy)
- **Blueprint overhead:** Negligible (registration happens once at startup)
- **CORS overhead:** Minimal (preflight requests cached by browser)

## Lessons Learned

### What Went Well
1. **Flask-OpenAPI3 integration:** Straightforward migration from standard Flask app
2. **Backward compatibility:** Legacy routes preserve existing functionality with zero downtime
3. **Centralized configuration:** App factory pattern eliminates code duplication
4. **Verification:** Import tests and route inspection caught issues early

### What Could Be Improved
1. **Dependency installation:** flask-openapi3, flask-compress, flask-limiter not in local venv initially (had to install manually)
2. **Database configuration:** create_openapi_app() calls configure_app() from database.py - slightly circular dependency

### Future Enhancements
1. **Deprecation warnings:** Add warnings to legacy routes after frontend migration complete
2. **API versioning headers:** Add X-API-Version response header for monitoring
3. **OpenAPI extensions:** Add x-code-samples for curl/Python/JavaScript examples
4. **Rate limit headers:** Add X-RateLimit-Limit, X-RateLimit-Remaining to responses

## Next Phase Readiness

### Blockers
None.

### Prerequisites for Phase 05-03 (SSE Infrastructure)
✅ **OpenAPI app factory available:** `create_openapi_app()` ready for use
✅ **Rate limiting configured:** SSE endpoints will inherit tier-based limits
✅ **Error handling configured:** SSE errors will use RFC 7807 format
✅ **CORS configured:** SSE connections from localhost:3000 allowed

### Prerequisites for Phase 05-04 (Domain API Routes)
✅ **Blueprint registration ready:** `register_v1_blueprints()` can be extended for products/jobs/vendors
✅ **OpenAPI tags defined:** products_tag, jobs_tag, vendors_tag ready for use
✅ **Swagger UI operational:** New routes will auto-appear in /api/docs
✅ **Pagination available:** Cursor and offset pagination from 05-01 ready for use

## Artifacts

### Commits
1. **7e3bf5d** - `feat(05-02): create OpenAPI app factory with Swagger UI`
   - src/api/app.py created (146 lines)
   - OpenAPI metadata, security schemes, tag definitions
   - Compression, rate limiting, error handler registration

2. **fc5e7dd** - `feat(05-02): add v1 blueprint registration with CORS`
   - src/api/__init__.py updated (76 lines)
   - register_v1_blueprints() function
   - V1 + legacy route registration
   - CORS configuration

3. **47eb42a** - `refactor(05-02): migrate app.py to use OpenAPI factory`
   - src/app.py refactored (91 lines removed, preserves all routes)
   - Remove redundant blueprint registration
   - Remove CORS import (handled by factory)
   - Add threaded=True for SSE support

### Documentation
- **Swagger UI:** http://localhost:5000/api/docs
- **OpenAPI JSON:** http://localhost:5000/api/docs/openapi.json

### Dependencies Added
- flask-openapi3==4.3.1
- flask-compress==1.23
- flask-limiter==4.1.1 (already in requirements.txt)

---

**Status:** ✅ Complete
**Duration:** 14 minutes
**Tasks:** 3/3 completed
**Commits:** 3
**Tests:** All verification checks passed
