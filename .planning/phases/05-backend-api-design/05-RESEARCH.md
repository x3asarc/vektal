# Phase 5: Backend API Design - Research

**Researched:** 2026-02-09
**Domain:** Flask RESTful API design with OpenAPI documentation, validation, and real-time capabilities
**Confidence:** HIGH

## Summary

Flask Backend API Design research focused on establishing RESTful API structure for a multi-supplier Shopify platform with 22+ existing endpoints (auth, billing, OAuth) requiring standardization and formal documentation. The phase boundary excludes business logic implementation and frontend components, focusing solely on API contracts, validation infrastructure, and documentation.

**Current State Analysis:** The project uses Flask 3.0+ with blueprints (auth, billing, webhooks), Pydantic (from Phase 2.1), PostgreSQL, Redis sessions, and Docker containerization. Existing endpoints follow mixed conventions without OpenAPI documentation or standardized error handling.

**Standard Approach:** Flask-OpenAPI3 4.3.1 enables automatic OpenAPI documentation generation from Pydantic schemas (single source of truth). Flask-Limiter handles tier-based rate limiting with Redis backend. Server-Sent Events (SSE) provide one-way real-time updates for job progress tracking. RFC 7807 Problem Details format standardizes error responses with field-level validation details.

**Key Trade-offs Evaluated:**
- **Documentation generation:** Flask-OpenAPI3 vs flask-pydantic-spec vs SpecTree → Flask-OpenAPI3 wins (most active, Pydantic v2 support, multiple UI options)
- **Real-time:** SSE vs WebSocket → SSE recommended (simpler, one-way job updates, HTTP-based, automatic reconnection)
- **Pagination:** Cursor-based vs offset-based → Cursor-based for large datasets (products/jobs), offset for admin views
- **Error format:** RFC 7807 vs custom → Hybrid approach (RFC 7807 for standards compliance, simplified format for field errors)

**Primary recommendation:** Use Flask-OpenAPI3 4.3.1 with Pydantic for auto-generated documentation, Flask-Limiter for tier-based rate limiting, SSE for job progress tracking with polling fallback, and hybrid error format (RFC 7807 + field-level details) for developer-friendly debugging.

## Standard Stack

The established libraries/tools for Flask RESTful API design with OpenAPI documentation:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Flask | 3.0+ | Web framework | Already in use, mature, well-documented |
| Pydantic | 2.x | Request/response validation | Already in use (Phase 2.1), type-safe, auto-validation |
| flask-openapi3 | 4.3.1 | OpenAPI documentation generation | Most active library, Pydantic v2 support, multiple UI options (Swagger/Redoc/RapiDoc) |
| Flask-Limiter | 4.1.1+ | Rate limiting | Industry standard, Redis integration, tier-based limits, header support |
| Flask-Compress | 1.15+ | Response compression | Standard solution for gzip/brotli/zstd compression |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Flask-CORS | 4.0.0 | CORS configuration | Already in use, production security headers |
| pytest-flask | 1.3+ | API testing | Flask-specific test fixtures, client simulation |
| OpenTelemetry Python SDK | Latest | Performance monitoring | Vendor-neutral APM, auto-instrumentation for Flask/Redis |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| flask-openapi3 | flask-pydantic-spec | Less active maintenance, fewer UI options |
| flask-openapi3 | SpecTree | Framework-agnostic but smaller community |
| SSE | WebSocket | Bidirectional complexity unnecessary for one-way job updates |
| Cursor pagination | Offset pagination | Simpler but poor performance for large datasets (products 10k+) |
| RFC 7807 | Custom JSON | Non-standard format, reinventing wheel |

**Installation:**
```bash
pip install flask-openapi3==4.3.1
pip install flask-limiter==4.1.1
pip install flask-compress==1.15.0
pip install opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation-flask
pip install pytest-flask pytest-cov requests-mock  # Testing
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── api/                      # API blueprints by domain
│   ├── __init__.py          # Blueprint registration
│   ├── products/
│   │   ├── __init__.py      # Blueprint definition
│   │   ├── routes.py        # OpenAPI route handlers
│   │   ├── schemas.py       # Pydantic request/response models
│   │   └── services.py      # Business logic (delegated)
│   ├── jobs/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   ├── schemas.py
│   │   ├── services.py
│   │   └── events.py        # SSE implementation
│   ├── vendors/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── schemas.py
│   ├── auth/                # Existing, refactor to domain pattern
│   └── billing/             # Existing, refactor to domain pattern
├── core/                     # Shared utilities
│   ├── errors.py            # RFC 7807 error handlers
│   ├── pagination.py        # Cursor/offset pagination helpers
│   └── rate_limit.py        # Tier-based limit definitions
└── app.py                   # OpenAPI app initialization
```

**Key Principles:**
- **Domain-driven organization:** Blueprints by business domain (products, jobs, vendors), NOT technical concern
- **Separation of concerns:** Routes define API contracts, services contain business logic
- **Co-location:** Schemas live next to routes they validate (single source of truth)
- **Flat hierarchy:** Avoid deep nesting, max 3 levels

### Pattern 1: OpenAPI Route Handler with Pydantic Validation
**What:** Flask-OpenAPI3 decorates route handlers with request/response schemas for automatic validation and documentation generation.

**When to use:** Every API endpoint requiring validation, documentation, and type safety.

**Example:**
```python
# Source: https://pypi.org/project/flask-openapi3/ (verified 2026-02-09)
from flask_openapi3 import OpenAPI, Tag
from pydantic import BaseModel, Field

# Define Pydantic schemas
class ProductQuery(BaseModel):
    vendor: str = Field(description="Filter by vendor code")
    page: int = Field(default=1, ge=1, description="Page number")
    limit: int = Field(default=50, ge=1, le=100, description="Items per page")

class ProductResponse(BaseModel):
    id: int
    sku: str
    title: str
    vendor: str
    price: float | None
    created_at: str

class ProductListResponse(BaseModel):
    products: list[ProductResponse]
    total: int
    page: int
    has_next: bool

# Initialize OpenAPI app
app = OpenAPI(__name__)
products_tag = Tag(name="Products", description="Product management")

# Route with automatic validation and documentation
@app.get(
    "/api/v1/products",
    tags=[products_tag],
    summary="List products",
    responses={"200": ProductListResponse}
)
def list_products(query: ProductQuery):
    """
    Get paginated product list with optional vendor filter.

    Returns products created in job processing, sorted by creation date.
    """
    # query is already validated Pydantic object
    # Business logic delegated to service layer
    result = product_service.list_products(
        vendor=query.vendor,
        page=query.page,
        limit=query.limit
    )
    return result.model_dump(), 200
```

**Benefits:**
- Single source of truth: Pydantic schema defines validation AND documentation
- Automatic OpenAPI spec generation at `/openapi.json`
- Interactive UI at `/api/docs` (Swagger UI, Redoc, or RapiDoc)
- Type hints enable IDE autocomplete

### Pattern 2: Tier-Based Rate Limiting
**What:** Flask-Limiter applies different rate limits per user tier using custom key functions.

**When to use:** All authenticated endpoints requiring abuse prevention and tier enforcement.

**Example:**
```python
# Source: https://flask-limiter.readthedocs.io/ (verified 2026-02-09)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import current_user

# Initialize with Redis backend
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    storage_uri="redis://redis:6379",
    storage_options={"socket_keepalive": True},
    default_limits=["200 per day", "50 per hour"]
)

# Tier-based limit function
def get_user_tier_limit():
    """Dynamic rate limit based on user tier."""
    if not current_user.is_authenticated:
        return "10 per hour"

    tier_limits = {
        "TIER_1": "100 per day",    # $29/mo
        "TIER_2": "500 per day",    # $99/mo
        "TIER_3": "2000 per day"    # $299/mo
    }
    return tier_limits.get(current_user.tier.name, "10 per hour")

# Apply to specific endpoint
@app.post("/api/v1/jobs")
@login_required
@limiter.limit(get_user_tier_limit)
def create_job():
    """Create scraping job with tier-based rate limiting."""
    # Tier limit enforced automatically
    # Headers include: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
    pass
```

**Benefits:**
- Enforces tier limits server-side (not relying on client cooperation)
- Rate limit headers inform clients of remaining quota
- Redis backend ensures limits persist across container restarts
- Shared limits across related endpoints via `@limiter.shared_limit()`

### Pattern 3: Server-Sent Events for Job Progress
**What:** SSE streams real-time job progress updates from server to client over HTTP.

**When to use:** One-way server-to-client updates (job progress, notifications) without bidirectional communication.

**Example:**
```python
# Source: https://maxhalford.github.io/blog/flask-sse-no-deps/ (verified 2026-02-09)
import queue
from flask import Response
from flask_login import login_required, current_user

class JobProgressAnnouncer:
    """Thread-safe SSE broadcaster for job progress."""
    def __init__(self):
        self.listeners = []

    def listen(self):
        """Subscribe new client to job updates."""
        q = queue.Queue(maxsize=5)
        self.listeners.append(q)
        return q

    def announce(self, job_id, progress_data):
        """Broadcast progress to all listeners."""
        msg = self.format_sse(data=progress_data, event=f"job_{job_id}")
        for i in reversed(range(len(self.listeners))):
            try:
                self.listeners[i].put_nowait(msg)
            except queue.Full:
                del self.listeners[i]  # Remove slow clients

    @staticmethod
    def format_sse(data: str, event=None) -> str:
        """Format message per SSE spec."""
        msg = f'data: {data}\n\n'
        if event:
            msg = f'event: {event}\n{msg}'
        return msg

job_announcer = JobProgressAnnouncer()

@app.get("/api/v1/jobs/<int:job_id>/stream")
@login_required
def stream_job_progress(job_id):
    """
    Stream real-time job progress via SSE.

    Client usage:
    const eventSource = new EventSource('/api/v1/jobs/123/stream');
    eventSource.addEventListener('job_123', (e) => {
        const progress = JSON.parse(e.data);
        console.log(`Progress: ${progress.processed}/${progress.total}`);
    });
    """
    # Verify user owns this job
    job = Job.query.filter_by(id=job_id, user_id=current_user.id).first_or_404()

    def stream():
        messages = job_announcer.listen()
        while True:
            msg = messages.get()  # Blocks until message available
            yield msg

    return Response(stream(), mimetype='text/event-stream')

# In background job processor (separate thread)
def process_job(job_id):
    # ... processing logic ...
    job_announcer.announce(job_id, json.dumps({
        "status": "running",
        "processed": processed_count,
        "total": total_items,
        "successful": successful_count,
        "failed": failed_count
    }))
```

**Polling Fallback:**
```python
@app.get("/api/v1/jobs/<int:job_id>/status")
@login_required
def get_job_status(job_id):
    """Polling fallback for environments blocking SSE."""
    job = Job.query.filter_by(id=job_id, user_id=current_user.id).first_or_404()
    return {
        "status": job.status.value,
        "processed": job.processed_items,
        "total": job.total_items,
        "successful": job.successful_items,
        "failed": job.failed_items
    }, 200
```

**Critical Requirements:**
- Flask must run with threaded mode: `app.run(threaded=True)` or use Gunicorn with `--worker-class=gthread`
- MIME type: `text/event-stream`
- Message format: `data: {json}\n\n` (double newline delimiter)
- Queue size: 5 prevents memory exhaustion from slow clients

### Pattern 4: Hybrid Error Response Format
**What:** Combines RFC 7807 Problem Details structure with field-level validation errors for developer-friendly debugging.

**When to use:** All error responses requiring standards compliance and detailed debugging information.

**Example:**
```python
# Source: https://datatracker.ietf.org/doc/html/rfc7807 (verified 2026-02-09)
from flask import jsonify
from pydantic import ValidationError

class ProblemDetails:
    """RFC 7807 Problem Details with field-level extensions."""

    @staticmethod
    def validation_error(error: ValidationError, status=400):
        """Convert Pydantic validation error to Problem Details."""
        # Extract field-level errors
        field_errors = {}
        for err in error.errors():
            field = ".".join(str(loc) for loc in err["loc"])
            field_errors[field] = err["msg"]

        return jsonify({
            "type": "https://api.yourapp.com/errors/validation-error",
            "title": "Validation Failed",
            "status": status,
            "detail": "Request validation failed on one or more fields",
            "fields": field_errors  # Extension member
        }), status

    @staticmethod
    def business_error(error_type: str, title: str, detail: str, status=400, **extensions):
        """Generic business logic error."""
        response = {
            "type": f"https://api.yourapp.com/errors/{error_type}",
            "title": title,
            "status": status,
            "detail": detail
        }
        response.update(extensions)  # Custom fields (balance, limit, etc.)
        return jsonify(response), status

# Register global error handlers
@app.errorhandler(ValidationError)
def handle_validation_error(e):
    return ProblemDetails.validation_error(e)

@app.errorhandler(404)
def handle_not_found(e):
    return ProblemDetails.business_error(
        error_type="not-found",
        title="Resource Not Found",
        detail=str(e),
        status=404
    )

@app.errorhandler(429)
def handle_rate_limit(e):
    return ProblemDetails.business_error(
        error_type="rate-limit-exceeded",
        title="Rate Limit Exceeded",
        detail="You have exceeded your tier rate limit",
        status=429,
        retry_after=e.description  # Extension field
    )
```

**Example Error Response:**
```json
{
  "type": "https://api.yourapp.com/errors/validation-error",
  "title": "Validation Failed",
  "status": 400,
  "detail": "Request validation failed on one or more fields",
  "fields": {
    "email": "Invalid email format",
    "password": "Must be at least 8 characters"
  }
}
```

**Benefits:**
- Standards-compliant: RFC 7807 structure for interoperability
- Developer-friendly: Field-level errors for precise debugging
- Extensible: Custom fields (balance, retry_after) without breaking standard
- Consistent: All errors follow same format

### Pattern 5: Cursor-Based Pagination for Large Datasets
**What:** Cursor pagination uses encoded pointers (typically ID + timestamp) for efficient navigation of large datasets.

**When to use:** Product lists, job results, vendor catalogs (datasets >10k records or frequently changing)

**Example:**
```python
# Sources: https://medium.com/@kuipasta1121/api-pagination-us-flask-offset-vs-cursor-based-approaches-b2e5327b0056
# https://engineeringatscale.substack.com/p/api-pagination-limit-offset-vs-cursor (verified 2026-02-09)
import base64
import json
from pydantic import BaseModel

class CursorPagination(BaseModel):
    """Cursor pagination parameters."""
    cursor: str | None = None
    limit: int = Field(default=50, ge=1, le=100)

def encode_cursor(last_id: int, last_timestamp: str) -> str:
    """Encode cursor for opaque pagination."""
    cursor_data = {"id": last_id, "ts": last_timestamp}
    return base64.urlsafe_b64encode(
        json.dumps(cursor_data).encode()
    ).decode()

def decode_cursor(cursor: str) -> tuple[int, str]:
    """Decode cursor to extract position."""
    cursor_data = json.loads(
        base64.urlsafe_b64decode(cursor.encode()).decode()
    )
    return cursor_data["id"], cursor_data["ts"]

@app.get("/api/v1/products")
def list_products(query: CursorPagination):
    """List products with cursor pagination."""
    if query.cursor:
        last_id, last_ts = decode_cursor(query.cursor)
        products = Product.query.filter(
            Product.created_at < last_ts,
            Product.id < last_id  # Tie-breaker for same timestamp
        ).order_by(
            Product.created_at.desc(),
            Product.id.desc()
        ).limit(query.limit + 1).all()
    else:
        products = Product.query.order_by(
            Product.created_at.desc(),
            Product.id.desc()
        ).limit(query.limit + 1).all()

    has_next = len(products) > query.limit
    if has_next:
        products = products[:query.limit]

    next_cursor = None
    if has_next and products:
        last_product = products[-1]
        next_cursor = encode_cursor(
            last_product.id,
            last_product.created_at.isoformat()
        )

    return {
        "products": [p.to_dict() for p in products],
        "pagination": {
            "next_cursor": next_cursor,
            "has_next": has_next,
            "limit": query.limit
        }
    }, 200
```

**Offset Pagination for Admin Views:**
```python
# Use offset for small, static datasets (admin dashboards)
@app.get("/admin/users")
@requires_tier("admin")
def list_users(page: int = 1, limit: int = 50):
    """Admin user list with offset pagination."""
    offset = (page - 1) * limit
    users = User.query.offset(offset).limit(limit).all()
    total = User.query.count()

    return {
        "users": [u.to_dict() for u in users],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }, 200
```

**Benefits:**
- **Performance:** Direct index lookup (O(1)) vs full scan (O(n)) for offset
- **Consistency:** No phantom records from concurrent inserts/deletes
- **Scalability:** Constant performance regardless of dataset size
- **Trade-off:** Cannot jump to arbitrary page (no "page 5" button)

### Pattern 6: Per-User API Versioning
**What:** Users control their API version via database field, enabling gradual migration without forced upgrades.

**When to use:** Major API changes requiring data transformation or breaking contract changes.

**Example:**
```python
# User model already has tier field, add api_version
class User(db.Model):
    # ... existing fields ...
    tier = db.Column(db.Enum(UserTier), default=UserTier.TIER_1)
    api_version = db.Column(db.String(10), default="v1")  # NEW FIELD
    api_version_locked_until = db.Column(db.DateTime, nullable=True)  # Rollback protection

# Version-aware blueprint registration
def register_versioned_blueprints(app):
    """Register both v1 and v2 endpoints."""
    from src.api.v1 import products_bp as products_v1
    from src.api.v2 import products_bp as products_v2

    app.register_blueprint(products_v1, url_prefix="/api/v1/products")
    app.register_blueprint(products_v2, url_prefix="/api/v2/products")

# Middleware to route users to correct version
@app.before_request
def route_to_user_version():
    """Redirect users to their API version."""
    if not current_user.is_authenticated:
        return None

    if request.path.startswith("/api/"):
        # Extract requested version from URL
        requested_version = request.path.split("/")[2]  # "v1" or "v2"
        user_version = current_user.api_version

        # If user requests wrong version, redirect to correct one
        if requested_version != user_version:
            new_path = request.path.replace(
                f"/api/{requested_version}",
                f"/api/{user_version}"
            )
            return redirect(new_path)

# Migration endpoint
@app.post("/api/v1/user/migrate-to-v2")
@login_required
def migrate_to_v2():
    """Opt-in migration to v2 API."""
    # Run user-specific data transformation
    migration_result = run_user_migration(current_user.id)

    if migration_result["success"]:
        current_user.api_version = "v2"
        current_user.api_version_locked_until = datetime.now() + timedelta(hours=24)
        db.session.commit()

        return {
            "message": "Migration successful",
            "new_version": "v2",
            "rollback_available_until": current_user.api_version_locked_until.isoformat()
        }, 200
    else:
        return ProblemDetails.business_error(
            error_type="migration-failed",
            title="Migration Failed",
            detail=migration_result["error"],
            status=500
        )
```

**Benefits:**
- User-controlled: No forced migrations, users choose when to upgrade
- Safe: Rollback capability during lock period
- Gradual: Backend supports both versions simultaneously
- Data-preserving: Migration script transforms user data before switch

### Anti-Patterns to Avoid

- **Tunneling through POST:** Using POST for all operations (GET, UPDATE, DELETE) forces developers to guess intent instead of following HTTP conventions. Use proper HTTP methods (GET, POST, PUT, DELETE, PATCH).

- **Mirroring database structure:** Exposing internal database schema as API structure creates tight coupling and makes schema changes break API contracts. Design resource-oriented endpoints independent of database tables.

- **Chatty APIs:** Requiring multiple requests to fetch related data (e.g., separate calls for product, variants, images) increases latency. Use nested resources or include query parameters (`?include=variants,images`).

- **Wildcard CORS in production:** `Access-Control-Allow-Origin: *` exposes sensitive endpoints to any domain. Explicitly list allowed origins for production.

- **Ignoring HTTP status codes:** Returning 200 OK with error payload in body violates HTTP semantics. Use proper status codes (400 for validation, 404 for not found, 429 for rate limit, 500 for server error).

- **No API versioning from start:** Adding versioning later requires complex migration. Include `/api/v1/` prefix from first endpoint.

- **Exposing stack traces in production:** Detailed error messages leak implementation details and security vulnerabilities. Use generic messages in production, log details server-side.

- **Inconsistent response formats:** Different error structures per endpoint confuse clients. Standardize on RFC 7807 or consistent custom format.

- **Missing rate limit headers:** Clients can't implement retry logic without `X-RateLimit-Remaining` and `X-RateLimit-Reset` headers.

- **Synchronous long-running operations:** Blocking requests for scraping jobs (30+ seconds) times out. Use async jobs with SSE progress updates.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OpenAPI documentation generation | Custom Swagger JSON builder | flask-openapi3 | Handles complex schemas, nested models, multiple response types, version compatibility |
| Rate limiting | Custom request counter | Flask-Limiter | Distributed counting (Redis), sliding windows, burst handling, rate limit headers |
| API pagination | Manual offset calculation | Cursor pagination library | Handles edge cases (concurrent updates, deleted records, timezone issues) |
| Request validation | Manual dict checking | Pydantic | Type coercion, nested validation, clear error messages, reusable schemas |
| Error response format | Custom error JSON | RFC 7807 Problem Details | Standard format, client library support, extension mechanism |
| Response compression | Manual gzip | Flask-Compress | Content negotiation, compression level tuning, multiple algorithms (gzip/brotli/zstd) |
| SSE message formatting | String concatenation | Structured SSE formatter | Handles event types, IDs, retry logic, multi-line data |
| CORS configuration | Custom headers | Flask-CORS | Preflight handling, credential support, per-route configuration |
| API versioning middleware | URL rewrite logic | Blueprint prefixes + version routing | Handles version negotiation, deprecation warnings, migration tracking |

**Key insight:** API infrastructure has subtle edge cases discovered over years of production use. RFC standards (7807 for errors), proven libraries (Flask-Limiter, flask-openapi3), and established patterns (cursor pagination, SSE formatting) prevent reinventing wheels with square corners. Custom solutions trade initial simplicity for long-term maintenance burden and missing features discovered too late.

## Common Pitfalls

### Pitfall 1: Development Server for SSE in Production
**What goes wrong:** Flask's built-in development server (`flask run`) blocks on first SSE connection, preventing other requests from processing. New connections hang indefinitely.

**Why it happens:** Development server uses single-threaded blocking I/O. SSE streams hold connection open, starving other endpoints.

**How to avoid:**
- Development: Use `flask run --with-threads` or `app.run(threaded=True)`
- Production: Use Gunicorn with `--worker-class=gthread --threads=4` or async workers (gevent, eventlet)
- Never use Flask development server in production

**Warning signs:**
- First SSE connection works, subsequent connections timeout
- Other API endpoints stop responding after SSE client connects
- Gunicorn logs show "worker timeout" errors

### Pitfall 2: Pagination Without Index on Sort Column
**What goes wrong:** Cursor pagination queries with `ORDER BY created_at` without index cause full table scans on large datasets (products >10k). Response time degrades from 50ms to 5+ seconds.

**Why it happens:** Database must scan entire table to sort results without index on `(created_at, id)` compound column.

**How to avoid:**
```sql
-- Create compound index for cursor pagination
CREATE INDEX idx_products_cursor ON products (created_at DESC, id DESC);

-- For filtered queries
CREATE INDEX idx_products_vendor_cursor ON products (vendor, created_at DESC, id DESC);
```

**Warning signs:**
- Slow query logs show full table scans on `ORDER BY` queries
- Pagination response time increases with dataset size
- Database CPU spikes during pagination requests

### Pitfall 3: Rate Limiting Without Shared State
**What goes wrong:** In-memory rate limiting (`storage_uri="memory://"`) resets on container restart and doesn't share state across multiple backend instances (horizontal scaling). Users can bypass limits by hitting different containers.

**Why it happens:** Each container maintains separate rate limit counters. Load balancer distributes requests across instances, each unaware of others' counts.

**How to avoid:**
```python
# WRONG: In-memory storage (development only)
limiter = Limiter(storage_uri="memory://")

# CORRECT: Redis storage (shared across instances)
limiter = Limiter(
    storage_uri="redis://redis:6379/1",
    storage_options={"socket_keepalive": True}
)
```

**Warning signs:**
- Rate limit enforcement inconsistent across requests
- Users report different limits on different attempts
- Rate limit counters reset after container restarts

### Pitfall 4: Exposing Pydantic ValidationError Details in Production
**What goes wrong:** Default Pydantic error messages expose internal field names, model structure, and validation logic that leak implementation details. Example: `"Input should be a valid email address: 'user@domain' does not match expected format"` reveals email validation regex.

**Why it happens:** Pydantic's detailed error messages are designed for developers, not end users. Raw errors contain type hints and model structure.

**How to avoid:**
```python
@app.errorhandler(ValidationError)
def handle_validation_error(e):
    # WRONG: Expose raw Pydantic error
    # return {"error": str(e)}, 400

    # CORRECT: Sanitize error messages
    field_errors = {}
    for err in e.errors():
        field = ".".join(str(loc) for loc in err["loc"])
        # Map internal error types to user-friendly messages
        user_message = {
            "value_error.email": "Invalid email format",
            "value_error.number.not_ge": f"Must be at least {err['ctx']['limit_value']}",
            "type_error.integer": "Must be a whole number"
        }.get(err["type"], "Invalid value")

        field_errors[field] = user_message

    return ProblemDetails.validation_error_from_dict(field_errors), 400
```

**Warning signs:**
- Error messages contain Python type names (`<class 'int'>`)
- Field names match database columns instead of API contract names
- Error messages reference internal validation logic

### Pitfall 5: Missing Content-Type Validation
**What goes wrong:** Endpoints accept any Content-Type and attempt JSON parsing, leading to confusing errors when clients send form data or plain text. Example: `POST /api/v1/jobs` with `Content-Type: application/x-www-form-urlencoded` returns "Expecting value: line 1 column 1 (char 0)" instead of clear error.

**Why it happens:** Flask's `request.get_json()` attempts parsing regardless of Content-Type header.

**How to avoid:**
```python
@app.before_request
def validate_content_type():
    """Enforce JSON content type for POST/PUT/PATCH."""
    if request.method in ["POST", "PUT", "PATCH"]:
        content_type = request.headers.get("Content-Type", "")
        if not content_type.startswith("application/json"):
            return ProblemDetails.business_error(
                error_type="invalid-content-type",
                title="Invalid Content-Type",
                detail=f"Expected 'application/json', got '{content_type}'",
                status=415  # Unsupported Media Type
            )
```

**Warning signs:**
- Generic JSON parsing errors in logs
- Users report "unexpected token" errors
- Errors don't clearly indicate Content-Type mismatch

### Pitfall 6: No API Version in URL from Start
**What goes wrong:** Starting with `/api/products` without version prefix requires URL migration when adding versioning later. Breaking changes affect all clients simultaneously.

**Why it happens:** "We'll add versioning when we need it" mentality. Retrofitting versioning requires redirects or proxy rules.

**How to avoid:**
- Include `/api/v1/` prefix from first endpoint
- Reserve `/api/` prefix for version negotiation/redirects
- Never deploy versionless endpoints to production

**Warning signs:**
- URLs don't include version identifier
- No plan for handling breaking changes
- Single codebase must support all clients

### Pitfall 7: Synchronous Job Creation
**What goes wrong:** Synchronous job processing blocks request for entire job duration (30+ seconds for large CSV uploads). Client timeouts, users retry, creating duplicate jobs.

**Why it happens:** Processing logic embedded directly in route handler instead of background worker.

**How to avoid:**
```python
# WRONG: Synchronous processing
@app.post("/api/v1/jobs")
def create_job():
    file = request.files['file']
    df = pd.read_csv(file)

    # This blocks for 30+ seconds
    for row in df.iterrows():
        process_row(row)  # Network calls, database writes

    return {"status": "completed"}, 200

# CORRECT: Async job with background processing
@app.post("/api/v1/jobs")
def create_job():
    file = request.files['file']

    # Create job record immediately
    job = Job(status=JobStatus.PENDING, ...)
    db.session.add(job)
    db.session.commit()

    # Queue background processing
    thread = Thread(target=process_job_async, args=(job.id,))
    thread.daemon = True
    thread.start()

    # Return immediately with job ID
    return {
        "job_id": job.id,
        "status": "pending",
        "stream_url": f"/api/v1/jobs/{job.id}/stream"
    }, 202  # Accepted
```

**Warning signs:**
- Request timeouts on job creation
- Duplicate jobs from client retries
- Route handler has long-running loops

## Code Examples

Verified patterns from official sources:

### Complete OpenAPI App Initialization
```python
# Source: https://pypi.org/project/flask-openapi3/ (verified 2026-02-09)
from flask_openapi3 import OpenAPI, Info, Tag
from flask_limiter import Limiter
from flask_compress import Compress
from src.database import db
from src.config.session_config import configure_session, configure_login_manager

# OpenAPI metadata
info = Info(
    title="Shopify Multi-Supplier API",
    version="1.0.0",
    description="RESTful API for multi-supplier Shopify product management"
)

# Security scheme for Flask-Login session auth
security_schemes = {
    "SessionAuth": {
        "type": "apiKey",
        "in": "cookie",
        "name": "session"
    }
}

# Initialize OpenAPI app (replaces Flask())
app = OpenAPI(
    __name__,
    info=info,
    security_schemes=security_schemes,
    doc_ui=True,  # Enable Swagger UI
    doc_prefix="/api/docs"
)

# Configure database and session
app.config.from_object("src.config.Config")
db.init_app(app)
configure_session(app)
configure_login_manager(app)

# Initialize extensions
limiter = Limiter(
    key_func=lambda: current_user.id if current_user.is_authenticated else request.remote_addr,
    app=app,
    storage_uri=os.getenv("REDIS_URL", "redis://redis:6379/1"),
    default_limits=["200 per day", "50 per hour"]
)

compress = Compress(app)
compress.init_app(app)

# Register versioned blueprints
from src.api.v1 import register_v1_blueprints
register_v1_blueprints(app)

# Global error handlers
from src.core.errors import register_error_handlers
register_error_handlers(app)

if __name__ == "__main__":
    # Production: use Gunicorn
    # Development: threaded mode for SSE
    app.run(debug=True, threaded=True)
```

### Complete Error Handler Setup
```python
# Source: https://datatracker.ietf.org/doc/html/rfc7807 (verified 2026-02-09)
# Source: https://docs.pydantic.dev/latest/errors/errors/ (verified 2026-02-09)
from flask import jsonify
from pydantic import ValidationError
from werkzeug.exceptions import HTTPException
from flask_limiter.errors import RateLimitExceeded

def register_error_handlers(app):
    """Register global error handlers for consistent error format."""

    @app.errorhandler(ValidationError)
    def handle_validation_error(e: ValidationError):
        """Pydantic validation errors -> RFC 7807 with field details."""
        field_errors = {}
        for err in e.errors():
            field = ".".join(str(loc) for loc in err["loc"])
            field_errors[field] = err["msg"]

        return jsonify({
            "type": "https://api.yourapp.com/errors/validation-error",
            "title": "Validation Failed",
            "status": 400,
            "detail": "Request validation failed on one or more fields",
            "fields": field_errors
        }), 400

    @app.errorhandler(RateLimitExceeded)
    def handle_rate_limit(e: RateLimitExceeded):
        """Rate limit errors with retry information."""
        return jsonify({
            "type": "https://api.yourapp.com/errors/rate-limit-exceeded",
            "title": "Rate Limit Exceeded",
            "status": 429,
            "detail": f"You have exceeded your rate limit. Try again in {e.description}",
            "retry_after": e.description
        }), 429

    @app.errorhandler(404)
    def handle_not_found(e):
        """404 errors."""
        return jsonify({
            "type": "https://api.yourapp.com/errors/not-found",
            "title": "Resource Not Found",
            "status": 404,
            "detail": str(e)
        }), 404

    @app.errorhandler(HTTPException)
    def handle_http_exception(e: HTTPException):
        """Generic HTTP exceptions."""
        return jsonify({
            "type": f"https://api.yourapp.com/errors/http-{e.code}",
            "title": e.name,
            "status": e.code,
            "detail": e.description
        }), e.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(e: Exception):
        """Catch-all for unexpected errors."""
        app.logger.exception("Unexpected error", exc_info=e)

        # Don't expose internal errors in production
        if app.config.get("ENV") == "production":
            detail = "An unexpected error occurred"
        else:
            detail = str(e)

        return jsonify({
            "type": "https://api.yourapp.com/errors/internal-server-error",
            "title": "Internal Server Error",
            "status": 500,
            "detail": detail
        }), 500
```

### Response Compression Configuration
```python
# Source: https://pypi.org/project/Flask-Compress/ (verified 2026-02-09)
from flask_compress import Compress

compress = Compress()

app.config["COMPRESS_MIMETYPES"] = [
    "text/html",
    "text/css",
    "text/xml",
    "application/json",
    "application/javascript",
    "application/problem+json"  # Include RFC 7807 media type
]

# Compression level: 1 (fast) to 9 (best compression)
# 6 = good balance for dynamic content
app.config["COMPRESS_LEVEL"] = 6

# Minimum response size to compress (bytes)
# Don't compress tiny responses (overhead exceeds benefit)
app.config["COMPRESS_MIN_SIZE"] = 500

# Compression algorithms (priority order)
# 2026 default: Zstandard > Brotli > Gzip
app.config["COMPRESS_ALGORITHM"] = ["zstd", "br", "gzip", "deflate"]

compress.init_app(app)
```

### HTTP Status Code Conventions
```python
# Sources: https://restfulapi.net/http-status-codes/ (verified 2026-02-09)
# https://www.speakeasy.com/api-design/status-codes (verified 2026-02-09)

# Success responses
200  # OK - Successful GET, PUT, PATCH (returns representation)
201  # Created - Successful POST (returns created resource)
202  # Accepted - Request accepted for async processing (returns job info)
204  # No Content - Successful DELETE or update with no body to return

# Client error responses
400  # Bad Request - Validation error, malformed request
401  # Unauthorized - Missing or invalid authentication
403  # Forbidden - Authenticated but insufficient permissions
404  # Not Found - Resource doesn't exist
409  # Conflict - Resource state conflict (e.g., duplicate SKU)
415  # Unsupported Media Type - Wrong Content-Type header
422  # Unprocessable Entity - Semantically incorrect (valid JSON, invalid business logic)
429  # Too Many Requests - Rate limit exceeded

# Server error responses
500  # Internal Server Error - Unexpected server error
502  # Bad Gateway - Upstream service (Shopify API) failed
503  # Service Unavailable - Server overloaded or maintenance
504  # Gateway Timeout - Upstream service timeout

# Example usage
@app.post("/api/v1/products")
def create_product():
    # Validation error -> 400
    if not request.json:
        return ProblemDetails.validation_error(...), 400

    # Business logic error -> 409
    if Product.query.filter_by(sku=request.json["sku"]).first():
        return ProblemDetails.business_error(
            "duplicate-sku", "Duplicate SKU", ..., status=409
        )

    # Success -> 201 with Location header
    product = Product(**request.json)
    db.session.add(product)
    db.session.commit()

    return product.to_dict(), 201, {
        "Location": f"/api/v1/products/{product.id}"
    }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual Swagger YAML | flask-openapi3 auto-generation | 2023-2024 | Single source of truth (Pydantic schemas), reduced maintenance |
| Offset pagination | Cursor pagination | 2021-2022 | Consistent results for large datasets, no phantom records |
| Custom error JSON | RFC 7807 Problem Details | 2016 (RFC), 2024+ (adoption) | Standardized error handling, client library support |
| WebSocket for all real-time | SSE for server push | 2023-2025 | Simpler implementation, HTTP-based, automatic reconnection |
| In-memory rate limiting | Redis-backed distributed limits | 2020-2021 | Multi-instance support, persistent across restarts |
| Gzip-only compression | Zstandard (2026 default) | 2024-2026 | Better compression ratio, faster than Brotli |
| Flask-RESTful/Flask-RESTX | Flask-OpenAPI3 | 2023-2025 | Better Pydantic integration, active maintenance |
| Header-based versioning | URL-based versioning | Always standard | Simpler to test, clearer in logs, browser-friendly |
| Flask development server | Gunicorn with gthread | Always standard | Production-ready, SSE support, graceful shutdown |
| Manual API testing | pytest-flask with fixtures | 2019-2020 | Faster tests, Flask-specific assertions, test client |

**Deprecated/outdated:**
- **Flask-RESTful:** Maintenance mode since 2021, lacks Pydantic integration, superseded by Flask-OpenAPI3
- **flask-pydantic-spec:** Less active than flask-openapi3, fewer UI options
- **In-memory rate limiting:** Development only, not production-safe
- **Offset pagination for large datasets:** Use cursor pagination for products/jobs (>10k records)
- **Exposing `/openapi.json` without authentication:** Security risk in production, enable auth requirement

## Open Questions

Things that couldn't be fully resolved:

1. **Per-user API versioning migration script complexity**
   - What we know: Pattern exists (user.api_version field, parallel v1/v2), migration scripts run per-user
   - What's unclear: Specific data transformations needed for v2 (depends on future API changes not yet defined)
   - Recommendation: Implement version infrastructure now, defer migration scripts until v2 requirements defined. Include rollback mechanism in design.

2. **Real-time SSE vs polling performance thresholds**
   - What we know: SSE preferred for modern browsers, polling fallback needed for corporate firewalls
   - What's unclear: Exact threshold for switching strategies (network latency? client capabilities? firewall detection?)
   - Recommendation: Implement both (SSE primary, polling fallback at `/jobs/{id}/status`). Monitor SSE connection success rate. If <90%, investigate firewall issues.

3. **OpenTelemetry instrumentation scope**
   - What we know: OpenTelemetry is 2026 standard, vendor-neutral, auto-instruments Flask/Redis
   - What's unclear: Performance overhead for high-traffic endpoints, storage requirements for trace data
   - Recommendation: Start with auto-instrumentation for Flask routes and database queries. Add custom spans for business logic (scraping, Shopify API calls) after baseline established. Use sampling (10-20%) for high-volume endpoints.

4. **Rate limit tier thresholds**
   - What we know: Tier-based limits prevent abuse (TIER_1: $29/mo, TIER_2: $99/mo, TIER_3: $299/mo)
   - What's unclear: Optimal limits per tier (100/day vs 500/day?), shared limits across related endpoints?
   - Recommendation: Start conservative (TIER_1: 100/day, TIER_2: 500/day, TIER_3: 2000/day). Monitor usage patterns. Adjust based on 95th percentile usage. Implement shared limits for job creation endpoints (prevent parallel job spam).

5. **OpenAPI documentation UI choice**
   - What we know: flask-openapi3 supports Swagger UI, Redoc, RapiDoc
   - What's unclear: Which UI best fits internal tooling use case? Swagger UI = interactive testing, Redoc = beautiful read-only, RapiDoc = performance for large specs
   - Recommendation: Default to Swagger UI (interactive "Try it out" for internal testing). Enable multiple UIs via config: `/api/docs` (Swagger), `/api/docs/redoc` (Redoc). Let team choose preferred UI.

## Sources

### Primary (HIGH confidence)
- flask-openapi3 PyPI (https://pypi.org/project/flask-openapi3/) - Current version 4.3.1, features, Pydantic integration
- Flask-Limiter documentation (https://flask-limiter.readthedocs.io/) - Rate limiting patterns, Redis backend, tier-based limits
- RFC 7807 specification (https://datatracker.ietf.org/doc/html/rfc7807) - Problem Details JSON schema, required/optional fields
- Pydantic error handling (https://docs.pydantic.dev/latest/errors/errors/) - ValidationError structure, field-level errors
- Flask SSE implementation (https://maxhalford.github.io/blog/flask-sse-no-deps/) - SSE without dependencies, message format, threading requirements
- Flask-Compress PyPI (https://pypi.org/project/Flask-Compress/) - Compression algorithms, configuration options

### Secondary (MEDIUM confidence)
- Medium: Flask Pydantic integration best practices (https://medium.com/@kuipasta1121/api-pagination-us-flask-offset-vs-cursor-based-approaches-b2e5327b0056) - Verified pagination patterns
- DigitalOcean: Flask blueprints (https://www.digitalocean.com/community/tutorials/how-to-structure-a-large-flask-application-with-flask-blueprints-and-flask-sqlalchemy) - Domain-driven structure
- Better Stack: Flask error handling (https://betterstack.com/community/guides/scaling-python/flask-error-handling/) - Common mistakes, production patterns
- Auth0: Flask API best practices (https://auth0.com/blog/best-practices-for-flask-api-development/) - Verified with official Flask docs
- Microsoft Azure: Web API design (https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design) - REST anti-patterns
- Svix: API rate limiting best practices (https://www.svix.com/resources/guides/api-rate-limiting-best-practices/) - Tier-based strategies
- Ably: WebSocket vs SSE comparison (https://ably.com/blog/websockets-vs-sse) - Protocol trade-offs, use cases
- Last9: Python APM monitoring (https://last9.io/blog/python-apm-monitoring-performance/) - OpenTelemetry 2026 adoption
- WebSocket.org: SSE comparison (https://websocket.org/comparisons/sse/) - Protocol benchmarks, decision matrix
- GitHub: RapiDoc comparison (https://github.com/rapi-doc/RapiDoc/issues/141) - OpenAPI UI trade-offs

### Tertiary (LOW confidence)
- WebSearch: "Flask API versioning per-user migration strategy" - Pattern validated but implementation details project-specific
- WebSearch: "Flask API testing pytest 2026" - General guidance, requires Flask-specific verification

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - flask-openapi3, Flask-Limiter, Pydantic verified via official PyPI and documentation
- Architecture: HIGH - Flask blueprints, domain-driven design confirmed by DigitalOcean/Better Stack tutorials and Flask official docs
- Real-time (SSE): HIGH - Implementation pattern verified via Max Halford blog (authoritative source) and Flask SSE library docs
- Error handling (RFC 7807): HIGH - IETF RFC specification is authoritative source
- Rate limiting: HIGH - Flask-Limiter official docs, tier-based patterns verified via Svix/Auth0 best practices
- Pagination: MEDIUM - Cursor pagination pattern well-documented but project-specific index requirements need validation
- API versioning: MEDIUM - Per-user versioning pattern exists but migration script complexity project-dependent
- Performance monitoring: MEDIUM - OpenTelemetry adoption trends verified but overhead/sampling strategy needs production testing
- Pitfalls: HIGH - Common mistakes verified across multiple sources (Better Stack, Flask docs, DigitalOcean)

**Research date:** 2026-02-09
**Valid until:** 2026-04-09 (60 days - Flask ecosystem stable, OpenAPI standards mature)

**Research constraints from CONTEXT.md:**
- LOCKED: Pydantic for validation (already in use Phase 2.1), SSE preferred for real-time, RFC 7807 format (with custom extensions), per-user API versioning pattern, OpenAPI auto-generation from Pydantic schemas
- CLAUDE'S DISCRETION: Rate limiting strategy (researched: Flask-Limiter with tier-based limits), CORS config (researched: Flask-CORS with explicit origins), pagination patterns (researched: cursor-based for large datasets), HTTP status conventions (researched: REST standards), compression (researched: Flask-Compress with zstd/brotli/gzip), monitoring (researched: OpenTelemetry vendor-neutral APM)
- DEFERRED: None specified

**Sequential thinking applied:**
1. **Problem understanding:** Standardize 22+ existing endpoints with documentation, validation, real-time updates
2. **Current state analysis:** Flask 3.0+, Pydantic in use, mixed conventions, no OpenAPI docs
3. **Option exploration:** Evaluated flask-openapi3 vs alternatives, SSE vs WebSocket, cursor vs offset pagination
4. **Trade-off evaluation:** Documented benefits/drawbacks of each approach with sources
5. **Synthesis:** Recommended flask-openapi3 + Flask-Limiter + SSE + RFC 7807 hybrid
6. **Implementation considerations:** Identified 7 critical pitfalls with prevention strategies
