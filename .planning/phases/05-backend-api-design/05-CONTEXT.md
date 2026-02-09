# Phase 5: Backend API Design - Context

**Gathered:** 2026-02-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Define RESTful API structure with validation, documentation, and real-time capabilities for the Shopify multi-supplier platform. This phase establishes API contracts and infrastructure that connect frontend to backend services - NOT implementing business logic or frontend components.

</domain>

<decisions>
## Implementation Decisions

### API Structure & Versioning
- **URL pattern**: `/api/v1/resources` (e.g., `/api/v1/products`)
- **Resource naming**: Plural resources (`/products`, `/jobs`, `/vendors`)
- **Blueprint organization**: By domain (blueprints: auth, products, jobs, vendors, billing)
  - Example structure: `src/api/products/routes.py`, `src/api/auth/routes.py`
- **Versioning strategy**: Per-user gradual migration
  - Both v1 and v2 run in parallel
  - User table includes `api_version` field
  - When v2 launches: user gets upgrade popup
  - Backend runs migration script for user's data
  - User switches to v2 only after successful migration
  - No forced migrations - prevents data loss
  - Sunset v1 after 6-12 months when 95%+ migrated

### Validation & Error Handling
- **Validation library**: Pydantic (already used in Phase 2.1, type hints, auto-validation)
- **Error response format**: Context-dependent
  - RFC 7807 Problem Details for standards compliance
  - Custom simple format for readability where appropriate
  - Research will determine best fit per endpoint type
- **Error detail level**: Detailed field-level errors + structured logging
  - Frontend gets: `{"fields": {"email": "Invalid format", "password": "Min 8 characters"}}`
  - Backend logs: Full request payload (sanitized), validation errors, user_id, timestamp
  - Same errors for all tiers (helpful errors don't reveal security holes)
  - Exception: Sensitive endpoints use generic errors (e.g., `/auth/login` says "Invalid credentials", not "Email not found")
- **Goal**: "Helpful for debugging, balanced for security"

### Real-Time Communication
- **Technology**: Research will determine SSE vs WebSocket
  - SSE recommended for one-way progress updates (simpler, HTTP-based)
  - WebSocket if two-way communication needed
  - Research Context7 patterns for best practice
- **Authentication**: Session cookie (simplest)
  - Use existing Flask session
  - Real-time connections inherit authentication automatically
  - Same-origin only, works without additional setup
- **Fallback strategy**: Research-based decision
  - Polling fallback likely (GET `/api/v1/jobs/123/status` every 2 seconds)
  - Research will validate approach for old browsers/corporate firewalls

### Documentation & Developer Experience
- **Documentation generation**: Research-based approach
  - Auto-generate from Pydantic schemas (single source of truth)
  - Investigate flask-pydantic or similar tools
  - Schemas define validation AND docs automatically
- **Docs location**: `/api/docs` (Swagger UI), `/api/openapi.json` (spec)
- **Docs access**: Local-only during development, auth-required in production
  - Development: `/api/docs` accessible on localhost without login (fast iteration)
  - Production: `/api/docs` requires authentication
  - OpenAPI spec can be committed to GitHub for versioning
- **Purpose**: Internal tooling for rapid API testing (replaces Postman/curl)

### Claude's Discretion
- Rate limiting strategy (different limits per tier, abuse prevention)
- CORS configuration and security headers
- API testing strategy (unit, integration, contract tests)
- HTTP status code conventions
- Response pagination patterns
- Request/response compression
- API performance monitoring

</decisions>

<specifics>
## Specific Ideas

**Context7 Skills Available:**
- `/alirezarezvani/claude-skills senior-backend` — Senior backend patterns and best practices
- `/wshobson/agents architecture-patterns` — Architecture patterns knowledge
- `/shipshitdev/library api-design-expert` — API design expertise
- `/wshobson/agents api-design-principles` — API design principles

Research phase should leverage these skills for industry best practices.

**Per-User Migration Pattern (v1 → v2):**
- User-controlled upgrade via popup (not forced)
- Migration script runs per user (data transformation if needed)
- User.api_version field tracks which version user is on
- Rollback capability per user if migration fails
- Similar to app update flow but preserves user data

**Interactive Swagger UI Clarification:**
- OpenAPI spec (YAML/JSON) → GitHub repo (static file, version controlled)
- Swagger UI → Running at `/api/docs` on Docker backend (interactive testing with "Try it out")
- Optional: Static copy on GitHub Pages for public reference (without testing functionality)

</specifics>

<context7_integration>
## Context7 Integration Strategy

Research phase should install and leverage these Context7 skills:

```bash
npx ctx7 skills install /alirezarezvani/claude-skills senior-backend
npx ctx7 skills install /wshobson/agents architecture-patterns
npx ctx7 skills install /shipshitdev/library api-design-expert
npx ctx7 skills install /wshobson/agents api-design-principles
```

These skills should inform:
- RFC 7807 vs custom error format decision
- SSE vs WebSocket for real-time communication
- Rate limiting patterns and tier-based strategy
- Security headers and CORS best practices
- API testing pyramid approach
- Documentation generation tooling
- Blueprint organization patterns
- Validation error handling conventions

</context7_integration>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope. Rate limiting, CORS, and testing strategy will be addressed during research/planning based on standard patterns.

</deferred>

---

*Phase: 05-backend-api-design*
*Context gathered: 2026-02-09*
