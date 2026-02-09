# Phase 4: Authentication & User Management - Research

**Researched:** 2026-02-09
**Domain:** Flask SaaS authentication with Shopify OAuth integration
**Confidence:** HIGH

## Summary

This research covers authentication implementation for a standalone Flask SaaS application with Shopify OAuth integration, Redis session management, Stripe billing, and tier-based access control. The technical domain is well-established with mature libraries (Flask-Login 0.7.0, Flask-Session, Flask-Bcrypt) and clear architectural patterns documented across multiple authoritative sources.

The recommended approach uses Flask-Login + Flask-Session with Redis for full control over the authentication flow, avoiding external dependencies like Supabase that introduce service coupling for a production SaaS. The codebase already has critical infrastructure in place: User and ShopifyStore models (Phase 3), Fernet encryption for OAuth tokens, Redis and PostgreSQL containers, and basic OAuth flow at lines 74-185 in src/app.py.

Key findings: OAuth 2.1 now mandates PKCE for all clients (not optional), bcrypt work factor 12 is standard (0.25-0.5s target), Flask-Session with Redis survives container restarts (session data in Redis container, not backend container), Stripe prorations are automatic for upgrades but should be disabled (`proration_behavior='none'`) for downgrades to prevent refund credits.

**Primary recommendation:** Use Flask-Login + Flask-Session with Redis backend for authentication, extend existing User model with account status states and tier change fields, implement decorator-based tier access control (`@requires_tier(UserTier.TIER_2)`), and use itsdangerous URLSafeTimedSerializer for email verification tokens (1-hour expiration standard).

## Standard Stack

The established libraries/tools for Flask SaaS authentication:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Flask-Login | 0.7.0 | User session management | De facto Flask auth standard, handles login state, session cookies, route protection with @login_required |
| Flask-Session | 1.0.1 | Server-side session storage | Industry standard for Redis session backend, prevents client-side session tampering |
| Flask-Bcrypt | 1.0.1 | Password hashing | Timing-safe bcrypt wrapper, work factor 12 default (OWASP recommended) |
| Redis | 7-alpine | Session and Celery broker | Fast ephemeral storage, survives backend container restarts, built-in expiration |
| itsdangerous | 2.1+ | Email verification tokens | Flask's built-in token library, URLSafeTimedSerializer for time-limited tokens |
| Stripe Python SDK | 11.x | Subscription billing | Official Stripe library, webhook handling, proration support |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Flask-Mail | 0.10.0 | Email sending | Verification emails, OAuth reminders, password reset (Phase 4.1) |
| Flask-Limiter | 3.x | Rate limiting | Login attempt throttling (5 failed → 15 min lockout), OAuth retry limits |
| cryptography | 42.x | Fernet encryption | Already in codebase (src/core/encryption.py), OAuth token storage |
| python-jose | 3.3+ | JWT tokens (optional) | If implementing API keys for programmatic access (deferred to Phase 5) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Flask-Login + Flask-Session | Supabase Auth | Supabase: Managed service with 50k MAU free tier, auto-pauses after 7 days inactivity (production killer), adds external dependency. Flask-Login: Full control, no external service, integrates with existing PostgreSQL, more code to maintain. **Verdict: Flask-Login** for production SaaS. |
| Redis session storage | PostgreSQL session storage | PostgreSQL: Slower for high-frequency session reads, requires cleanup job for expired sessions. Redis: 10-100x faster, built-in expiration, already in stack. **Verdict: Redis** is industry standard. |
| Bcrypt | Argon2 | Argon2: 2015 password hashing competition winner, memory-hard (ASIC-resistant), overkill for web apps. Bcrypt: 1999 algorithm, CPU-hard, battle-tested, Flask ecosystem standard. **Verdict: Bcrypt** unless high-security requirements demand Argon2. |

**Installation:**
```bash
# Core auth stack (add to requirements.txt)
flask-login==0.7.0
flask-session[redis]==1.0.1
flask-bcrypt==1.0.1
redis==5.0.1

# Email verification
flask-mail==0.10.0
itsdangerous==2.1.2

# Stripe billing
stripe==11.1.0

# Rate limiting (optional, recommended)
flask-limiter==3.5.0
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── models/
│   ├── user.py              # EXTEND: Add account_status, pending_tier, email_verified fields
│   └── oauth_attempt.py     # NEW: Log OAuth attempts for debugging/security
├── auth/
│   ├── __init__.py
│   ├── login.py             # Login/logout routes, session management
│   ├── registration.py      # User signup, email verification
│   ├── oauth.py             # REFACTOR: Move OAuth logic from app.py (lines 74-185)
│   ├── decorators.py        # @requires_tier, @email_verified_required
│   └── email_verification.py # Token generation, verification, resend
├── billing/
│   ├── __init__.py
│   ├── stripe_client.py     # Stripe API wrapper
│   └── webhooks.py          # Stripe webhook handlers (payment success, subscription changes)
├── tasks/
│   └── auth_tasks.py        # Celery tasks: send_verification_email, send_oauth_reminder
└── config/
    └── session_config.py    # Flask-Session Redis configuration
```

### Pattern 1: Flask-Login User Loader
**What:** Flask-Login requires a user_loader callback to reload User object from session ID.
**When to use:** Every Flask-Login integration (mandatory).
**Example:**
```python
# Source: https://flask-login.readthedocs.io/en/latest/
from flask_login import LoginManager, UserMixin

login_manager = LoginManager()
login_manager.login_view = 'auth.login'  # Redirect unauthenticated users

# User model must inherit UserMixin or implement 4 methods:
# is_authenticated, is_active, is_anonymous, get_id()
class User(db.Model, UserMixin):
    # ... existing fields ...

    @property
    def is_active(self):
        """Flask-Login calls this to check if account is active."""
        return self.account_status == AccountStatus.ACTIVE

@login_manager.user_loader
def load_user(user_id):
    """Reload user object from user ID stored in session."""
    return User.query.get(int(user_id))
```

### Pattern 2: Redis Session Configuration
**What:** Flask-Session with Redis backend for session persistence across container restarts.
**When to use:** Production Flask apps with multiple workers or containerized deployments.
**Example:**
```python
# Source: https://testdriven.io/blog/flask-server-side-sessions/
from flask import Flask
from flask_session import Session

app = Flask(__name__)

# Session configuration
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = redis.from_url('redis://redis:6379/0')
app.config['SESSION_PERMANENT'] = False  # Session expires on browser close (unless remember_me)
app.config['SESSION_USE_SIGNER'] = True  # Sign session cookie with SECRET_KEY
app.config['SESSION_KEY_PREFIX'] = 'session:'  # Redis key prefix

# Security settings (CRITICAL for production)
app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS only (disable in dev)
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Not accessible via JavaScript
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection, allows OAuth redirects
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)  # Default expiration

Session(app)
```

### Pattern 3: Tier-Based Access Control Decorator
**What:** Custom decorator to enforce tier requirements on routes (e.g., AI features for Tier 2+).
**When to use:** Every route that has tier restrictions.
**Example:**
```python
# Source: https://leapcell.io/blog/empowering-flask-and-fastapi-with-custom-decorators-for-access-control-and-logging
from functools import wraps
from flask import abort, jsonify
from flask_login import current_user

def requires_tier(minimum_tier: UserTier):
    """
    Decorator to enforce minimum tier requirement.

    Usage:
        @app.route('/ai/chat')
        @login_required  # ALWAYS apply @login_required BEFORE @requires_tier
        @requires_tier(UserTier.TIER_2)
        def ai_chat():
            return jsonify({'response': 'AI chat'})
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check authentication first (should be handled by @login_required)
            if not current_user.is_authenticated:
                return jsonify({'error': 'Authentication required'}), 401

            # Tier comparison (enum values: TIER_1=1, TIER_2=2, TIER_3=3)
            tier_levels = {UserTier.TIER_1: 1, UserTier.TIER_2: 2, UserTier.TIER_3: 3}
            user_level = tier_levels.get(current_user.tier, 0)
            required_level = tier_levels.get(minimum_tier, 0)

            if user_level < required_level:
                return jsonify({
                    'error': 'Insufficient tier',
                    'required': minimum_tier.value,
                    'current': current_user.tier.value,
                    'upgrade_url': '/billing/upgrade'
                }), 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator
```

### Pattern 4: Email Verification with itsdangerous
**What:** Generate time-limited tokens for email verification links (prevents replay attacks).
**When to use:** User registration, email verification, password reset flows.
**Example:**
```python
# Source: https://mailtrap.io/blog/flask-email-verification/
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

def get_serializer():
    """Create serializer with app SECRET_KEY."""
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])

def generate_verification_token(email: str) -> str:
    """Generate email verification token (1 hour expiration)."""
    serializer = get_serializer()
    return serializer.dumps(email, salt='email-verification')

def verify_token(token: str, max_age: int = 3600) -> tuple[bool, str]:
    """
    Verify email verification token.

    Args:
        token: Token from email link
        max_age: Max age in seconds (3600 = 1 hour)

    Returns:
        (success: bool, email: str or error_message: str)
    """
    serializer = get_serializer()
    try:
        email = serializer.loads(token, salt='email-verification', max_age=max_age)
        return True, email
    except SignatureExpired:
        return False, 'Token expired. Request a new verification email.'
    except BadSignature:
        return False, 'Invalid token. Check your email for the correct link.'
```

### Pattern 5: Stripe Subscription Upgrades (Immediate with Proration)
**What:** Upgrade subscription immediately and charge prorated difference.
**When to use:** User clicks "Upgrade to Tier 2" button.
**Example:**
```python
# Source: https://docs.stripe.com/billing/subscriptions/change
import stripe

def upgrade_subscription(user_id: int, new_tier: UserTier):
    """
    Upgrade user subscription with immediate billing.

    Stripe automatically calculates proration:
    - Credit for unused time on old plan
    - Charge for remaining time on new plan
    """
    user = User.query.get(user_id)

    # Map tiers to Stripe price IDs (set in Stripe dashboard)
    tier_prices = {
        UserTier.TIER_1: 'price_tier1_monthly',
        UserTier.TIER_2: 'price_tier2_monthly',
        UserTier.TIER_3: 'price_tier3_monthly',
    }

    try:
        # Update subscription (Stripe automatically prorates)
        subscription = stripe.Subscription.modify(
            user.stripe_subscription_id,
            items=[{
                'id': user.stripe_subscription_item_id,
                'price': tier_prices[new_tier],
            }],
            proration_behavior='create_prorations',  # DEFAULT: Auto-prorate
            billing_cycle_anchor='unchanged',  # Keep existing billing date
        )

        # Update user tier immediately
        user.tier = new_tier
        db.session.commit()

        return {'success': True, 'subscription': subscription}
    except stripe.error.StripeError as e:
        return {'success': False, 'error': str(e)}
```

### Pattern 6: Stripe Subscription Downgrades (End of Billing Cycle)
**What:** Schedule downgrade for end of billing cycle (no refunds/credits).
**When to use:** User clicks "Downgrade to Tier 1" button.
**Example:**
```python
# Source: https://docs.stripe.com/billing/subscriptions/prorations
def downgrade_subscription(user_id: int, new_tier: UserTier):
    """
    Schedule downgrade for end of billing cycle.

    User keeps current tier until billing_period_end,
    then downgrade takes effect on renewal.
    """
    user = User.query.get(user_id)

    # Store pending tier change in database
    user.pending_tier = new_tier
    user.tier_change_effective_date = user.billing_period_end
    db.session.commit()

    # Update subscription to change on renewal (no immediate charge)
    tier_prices = {
        UserTier.TIER_1: 'price_tier1_monthly',
        UserTier.TIER_2: 'price_tier2_monthly',
        UserTier.TIER_3: 'price_tier3_monthly',
    }

    try:
        subscription = stripe.Subscription.modify(
            user.stripe_subscription_id,
            items=[{
                'id': user.stripe_subscription_item_id,
                'price': tier_prices[new_tier],
            }],
            proration_behavior='none',  # NO prorations (no refunds)
            billing_cycle_anchor='unchanged',  # Change on next renewal
        )

        return {
            'success': True,
            'effective_date': user.billing_period_end,
            'message': f'Downgrade scheduled for {user.billing_period_end.strftime("%Y-%m-%d")}'
        }
    except stripe.error.StripeError as e:
        return {'success': False, 'error': str(e)}
```

### Pattern 7: Shopify OAuth with Retry Logic
**What:** Decouple user account creation from OAuth success, allow unlimited retries with exponential backoff.
**When to use:** Shopify OAuth callback handler (refactor existing app.py lines 129-185).
**Example:**
```python
# Source: https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens/authorization-code-grant
import time
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),  # 1s, 2s, 4s
    reraise=True
)
def exchange_code_for_token(shop: str, code: str) -> str:
    """
    Exchange OAuth code for access token with retry logic.

    Retries network/timeout errors automatically (3 attempts with exponential backoff).
    Does NOT retry access_denied errors (user clicked Cancel).
    """
    token_url = f"https://{shop}/admin/oauth/access_token"
    payload = {
        'client_id': SHOPIFY_API_KEY,
        'client_secret': SHOPIFY_API_SECRET,
        'code': code
    }

    response = requests.post(token_url, json=payload, timeout=10)
    response.raise_for_status()
    return response.json()['access_token']

@app.route('/auth/callback')
def shopify_callback():
    """Handle Shopify OAuth callback with error handling."""
    code = request.args.get('code')
    error = request.args.get('error')
    state = request.args.get('state')
    shop = request.args.get('shop')

    # CRITICAL: Verify state parameter (CSRF protection)
    if state != session.get('oauth_state'):
        return render_template('oauth_error.html',
                               error='Security validation failed. Please try again.'), 400

    # Handle access_denied error (user clicked Cancel)
    if error == 'access_denied':
        return render_template('oauth_error.html',
                               error='You clicked Cancel. We need these permissions to manage your products.',
                               retry_url=url_for('shopify_auth', shop=shop))

    # Get user (must already exist from registration flow)
    user = User.query.filter_by(email=session.get('user_email')).first()
    if not user:
        return jsonify({'error': 'User not found. Complete registration first.'}), 400

    try:
        # Exchange code for token (with retry logic)
        access_token = exchange_code_for_token(shop, code)

        # Create or update ShopifyStore
        store = ShopifyStore.query.filter_by(user_id=user.id).first()
        if not store:
            store = ShopifyStore(user_id=user.id, shop_domain=shop, shop_name=shop.split('.')[0])
            db.session.add(store)

        store.set_access_token(access_token)  # Fernet encryption (already implemented)
        user.account_status = AccountStatus.ACTIVE  # Mark OAuth complete
        db.session.commit()

        # Log successful OAuth attempt
        log_oauth_attempt(user.id, shop, 'success')

        return redirect('/dashboard')

    except requests.exceptions.RequestException as e:
        # Network/timeout error - show retry button
        log_oauth_attempt(user.id, shop, f'network_error: {str(e)}')
        return render_template('oauth_error.html',
                               error='Connection interrupted. This is usually temporary.',
                               retry_url=url_for('shopify_auth', shop=shop))
```

### Pattern 8: Stripe Webhook Handler
**What:** Handle Stripe webhook events for payment success, subscription changes, payment failures.
**When to use:** Every Stripe integration (webhooks are authoritative source of truth).
**Example:**
```python
# Source: https://docs.stripe.com/webhooks
import stripe
from flask import request

@app.route('/webhooks/stripe', methods=['POST'])
def stripe_webhook():
    """
    Handle Stripe webhook events.

    CRITICAL: Verify webhook signature to prevent spoofing.
    """
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    webhook_secret = current_app.config['STRIPE_WEBHOOK_SECRET']

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError:
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError:
        return jsonify({'error': 'Invalid signature'}), 400

    # Handle different event types
    if event['type'] == 'checkout.session.completed':
        # Payment succeeded - create user account
        session_obj = event['data']['object']
        handle_payment_success(session_obj)

    elif event['type'] == 'customer.subscription.updated':
        # Subscription tier changed
        subscription = event['data']['object']
        handle_subscription_change(subscription)

    elif event['type'] == 'invoice.payment_failed':
        # Payment failed - suspend account
        invoice = event['data']['object']
        handle_payment_failure(invoice)

    return jsonify({'status': 'success'}), 200
```

### Anti-Patterns to Avoid
- **Storing sessions in client-side cookies:** Flask's default session uses signed cookies (4KB limit, visible to client). Use Flask-Session with Redis for server-side storage.
- **Coupling user creation to OAuth success:** If OAuth fails after payment, user has paid but has no account. Create user after payment, BEFORE OAuth.
- **Not using timing-safe password comparison:** `password == user.password_hash` is vulnerable to timing attacks. Use `bcrypt.check_password_hash()` (constant-time comparison).
- **Hardcoding tier levels in routes:** Don't check `if user.tier == UserTier.TIER_2` in every route. Use `@requires_tier()` decorator for DRY code.
- **Ignoring Stripe webhook signatures:** Anyone can POST to `/webhooks/stripe`. Always verify `Stripe-Signature` header to prevent fake events.
- **Regenerating session ID on every request:** Only regenerate on login/logout to prevent session fixation. Don't regenerate on every request (breaks "remember me").
- **Using OAuth state token as session identifier:** State parameter is for CSRF protection only (single-use, expires in 1 hour). Use separate session cookie for persistent login.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Password hashing | Custom bcrypt wrapper with work factor management | Flask-Bcrypt | Handles salting automatically, timing-safe comparison, configurable work factor via `BCRYPT_LOG_ROUNDS`, battle-tested by millions of Flask apps |
| Email verification tokens | UUID stored in database with expiration timestamp | itsdangerous.URLSafeTimedSerializer | Token contains email and expiration (no DB lookup), cryptographically signed (can't be forged), URL-safe base64 encoding, built into Flask ecosystem |
| Session management | Custom Redis key management, expiration logic, serialization | Flask-Session | Handles session serialization/deserialization, automatic expiration, key prefixing, secure cookie signing, transparent Redis integration |
| OAuth state parameter | Random string stored in database or client cookie | os.urandom(16).hex() in server-side session | Cryptographically secure random, stored in server-side Redis session (can't be tampered), automatic cleanup on session expiration |
| Subscription proration math | Calculate prorated amounts based on days remaining | Stripe API automatic proration | Stripe calculates second-by-second proration (more accurate than daily), handles timezone edge cases, accounts for billing cycle anchor, tested against millions of subscriptions |
| Rate limiting | Counter in Redis with expiration, IP tracking | Flask-Limiter | Handles distributed rate limiting (multiple workers), supports per-user and per-IP limits, configurable strategies (fixed window, sliding window), integrates with Redis |
| JWT token generation | Manual JWT signing with PyJWT | python-jose or Flask-JWT-Extended | Handles token expiration, refresh tokens, blacklisting, CSRF protection for JWTs in cookies, integrates with Flask-Login |

**Key insight:** Authentication is security-critical. Off-by-one errors in token expiration, timing attacks in password comparison, and race conditions in session management have led to major breaches (LinkedIn 2012, Yahoo 2013). Use battle-tested libraries that have been audited by security researchers. The 10 hours saved by "rolling your own" bcrypt wrapper is not worth the 10 years of breach liability.

## Common Pitfalls

### Pitfall 1: Session Data Lost on Backend Container Restart
**What goes wrong:** User logs in, backend container restarts (deploy, crash, scale), user is logged out.
**Why it happens:** Flask's default session stores data in signed cookies (client-side). If backend container restarts, SECRET_KEY might change (if generated at runtime), invalidating all sessions. Even if SECRET_KEY is stable, large session data (>4KB) doesn't fit in cookies.
**How to avoid:** Use Flask-Session with Redis backend. Session data lives in Redis container (separate from backend), survives backend restarts. Redis container data persists via Docker named volume (`redis_data` in docker-compose.yml).
**Warning signs:**
- Users report being logged out after deployments
- Session cookie size >4KB (browser rejects cookie)
- `BadSignature` errors in logs after SECRET_KEY rotation

### Pitfall 2: OAuth Fails but User Already Paid
**What goes wrong:** User completes Stripe payment, then OAuth fails (network timeout, user clicks Cancel), resulting in "orphaned payment" - user paid but has no account.
**Why it happens:** Traditional OAuth flow creates account AFTER successful token exchange. If token exchange fails, account creation never happens.
**How to avoid:** Decouple account creation from OAuth success. Flow: Payment → Create User (status=PENDING_OAUTH) → OAuth → Update User (status=ACTIVE). If OAuth fails, user account exists with PENDING_OAUTH status, can retry unlimited times.
**Warning signs:**
- Stripe charges succeed but no corresponding user in database
- Users contact support: "I paid but can't log in"
- Manual refund requests for failed OAuth

### Pitfall 3: Tier Change Race Condition
**What goes wrong:** User is on Tier 1, requests upgrade to Tier 2, but between checking tier and processing job, they downgrade back to Tier 1. Job processes with Tier 2 permissions when user is now Tier 1.
**Why it happens:** Tier check happens at request time, job processes minutes/hours later. User's tier changed in between.
**How to avoid:** Store user_tier snapshot in Job model at job creation time. Check `job.user_tier` not `job.user.tier` when processing. If tiers mismatch, reject job or bill for higher tier.
**Warning signs:**
- Users get features from higher tier after downgrading
- Billing disputes: "I was charged for Tier 3 but I'm on Tier 2"
- Celery task logs show tier mismatches

### Pitfall 4: Email Verification Bypass via Session Injection
**What goes wrong:** User registers, never verifies email, but can still access protected routes by manipulating session data.
**Why it happens:** `@login_required` only checks if user is authenticated, not if email is verified. Developer assumes "logged in = verified email" but registration creates session before verification.
**How to avoid:** Add separate `@email_verified_required` decorator that checks `current_user.email_verified`. Apply AFTER `@login_required` on routes that require verification.
**Warning signs:**
- Users with `email_verified=False` accessing scraping jobs
- Spam signups creating accounts without verifying
- Support tickets: "I never verified email but I can use the app"

### Pitfall 5: Stripe Webhook Replay Attack
**What goes wrong:** Attacker captures legitimate `checkout.session.completed` webhook, replays it 100 times, creating 100 user accounts from 1 payment.
**Why it happens:** Webhook handler creates user account on every `checkout.session.completed` event, doesn't check if event was already processed.
**How to avoid:** Store `event.id` (Stripe event ID) in database, check for duplicates before processing. Stripe sends same event multiple times if webhook fails (retry logic), idempotent processing is mandatory.
**Warning signs:**
- Multiple users with same `stripe_customer_id`
- Database shows 10 users created within 1 second
- Stripe dashboard shows 1 payment, database shows 10 accounts

### Pitfall 6: Bcrypt Work Factor Too Low or Too High
**What goes wrong:** Work factor 4 (fast hashing) makes brute force attacks feasible. Work factor 16 (slow hashing) causes login to take 5+ seconds, terrible UX.
**Why it happens:** Developer copies config from tutorial without benchmarking on production hardware. Work factor 12 is standard but might be too slow on weak hardware (Raspberry Pi) or too fast on beefy servers (128-core).
**How to avoid:** Benchmark on production hardware. Target: 0.25-0.5 seconds per hash. Adjust `BCRYPT_LOG_ROUNDS` config. Work factor 12 is good starting point for modern servers (2-4 vCPU).
**Warning signs:**
- Login takes >1 second (user sees spinner, bad UX)
- CPU spikes to 100% on login endpoint
- Security audit flags weak password hashing

### Pitfall 7: OAuth State Reuse Attack
**What goes wrong:** Attacker captures OAuth callback URL with valid state parameter, reuses it to authenticate as victim.
**Why it happens:** State parameter is validated but not invalidated after use. Attacker can replay same state token multiple times.
**How to avoid:** Store state in Redis with 1-hour expiration, delete state from Redis after first use. Check state exists in Redis before validating OAuth callback.
**Warning signs:**
- Same state token used in multiple OAuth attempts (check logs)
- Security audit flags CSRF vulnerability
- Penetration test shows OAuth replay attack succeeds

### Pitfall 8: Tier Downgrade Credits User's Account
**What goes wrong:** User on Tier 3 ($99/mo) downgrades to Tier 1 ($29/mo) with 15 days left in billing cycle. Stripe automatically credits $35 to user's account. User can immediately upgrade back to Tier 3, getting 15 days free.
**Why it happens:** Stripe's default `proration_behavior='create_prorations'` generates credits for unused time. This is correct for upgrades (user pays prorated amount) but wrong for downgrades (no refunds policy).
**How to avoid:** Set `proration_behavior='none'` for downgrades. User stays on current tier until billing period ends, then downgrade takes effect. No credits, no refunds.
**Warning signs:**
- Stripe balance shows negative amounts (credits)
- Users exploit upgrade/downgrade loop for free days
- Revenue loss from unexpected refunds

## Code Examples

Verified patterns from official sources:

### User Model Extension (Add Authentication Fields)
```python
# Source: Phase 3 models + CONTEXT.md requirements
from sqlalchemy import String, Enum as SQLEnum, Integer, Boolean, DateTime
from sqlalchemy.orm import relationship
from flask_login import UserMixin
from datetime import datetime, timedelta
import enum

class AccountStatus(enum.Enum):
    """User account status for OAuth flow."""
    PENDING_OAUTH = "pending_oauth"  # Payment received, awaiting Shopify OAuth
    ACTIVE = "active"                # OAuth complete, email verified, fully functional
    INCOMPLETE = "incomplete"        # Grace period expired without OAuth completion
    SUSPENDED = "suspended"          # Payment failure or policy violation

class UserTier(enum.Enum):
    """User subscription tiers (already exists in codebase)."""
    TIER_1 = "tier_1"
    TIER_2 = "tier_2"
    TIER_3 = "tier_3"

class User(db.Model, UserMixin, TimestampMixin):
    """
    User model with authentication and billing fields.

    EXTENDS existing model in src/models/user.py
    """
    __tablename__ = 'users'

    # Existing fields (from Phase 3)
    id = db.Column(Integer, primary_key=True)
    email = db.Column(String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(String(255), nullable=False)
    tier = db.Column(SQLEnum(UserTier), default=UserTier.TIER_1, nullable=False, index=True)

    # NEW: Authentication fields
    account_status = db.Column(
        SQLEnum(AccountStatus),
        default=AccountStatus.PENDING_OAUTH,
        nullable=False,
        index=True
    )
    email_verified = db.Column(Boolean, default=False, nullable=False)
    email_verification_token = db.Column(String(255), nullable=True)  # itsdangerous token

    # NEW: OAuth tracking
    oauth_attempts = db.Column(Integer, default=0, nullable=False)
    last_oauth_attempt = db.Column(DateTime, nullable=True)
    oauth_completion_deadline = db.Column(DateTime, nullable=True)  # 7-day grace period

    # NEW: Tier change tracking
    pending_tier = db.Column(SQLEnum(UserTier), nullable=True)  # For scheduled downgrades
    tier_change_effective_date = db.Column(DateTime, nullable=True)

    # NEW: Billing cycle tracking
    billing_period_start = db.Column(DateTime, nullable=True)
    billing_period_end = db.Column(DateTime, nullable=True)

    # NEW: Stripe integration
    stripe_customer_id = db.Column(String(255), unique=True, nullable=True, index=True)
    stripe_subscription_id = db.Column(String(255), unique=True, nullable=True)
    stripe_subscription_item_id = db.Column(String(255), nullable=True)  # For subscription updates

    # Existing relationships (from Phase 3)
    shopify_store = relationship('ShopifyStore', back_populates='user', uselist=False)
    vendors = relationship('Vendor', back_populates='user', cascade='all, delete-orphan', lazy='dynamic')
    jobs = relationship('Job', back_populates='user', cascade='all, delete-orphan', lazy='dynamic')

    @property
    def is_active(self):
        """Flask-Login checks this to allow/deny login."""
        return self.account_status == AccountStatus.ACTIVE

    def set_password(self, plaintext_password: str):
        """Hash password with bcrypt before storing."""
        from flask_bcrypt import Bcrypt
        bcrypt = Bcrypt()
        self.password_hash = bcrypt.generate_password_hash(plaintext_password).decode('utf-8')

    def check_password(self, plaintext_password: str) -> bool:
        """Verify password against hash (timing-safe comparison)."""
        from flask_bcrypt import Bcrypt
        bcrypt = Bcrypt()
        return bcrypt.check_password_hash(self.password_hash, plaintext_password)

    def __repr__(self):
        return f'<User {self.email} tier={self.tier.value} status={self.account_status.value}>'
```

### OAuth Attempt Logging Model
```python
# Source: CONTEXT.md requirements + security best practices
from sqlalchemy import String, Integer, ForeignKey, Text, DateTime
from datetime import datetime, timedelta

class OAuthAttempt(db.Model, TimestampMixin):
    """
    Log OAuth attempts for debugging and security monitoring.

    NEW MODEL - add to src/models/oauth_attempt.py
    """
    __tablename__ = 'oauth_attempts'

    id = db.Column(Integer, primary_key=True)
    user_id = db.Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    # OAuth details
    shop_domain = db.Column(String(255), nullable=False)
    state_token = db.Column(String(64), unique=True, nullable=False, index=True)  # For deduplication

    # Result tracking
    result = db.Column(String(50), nullable=False)  # success, access_denied, network_error, timeout, etc.
    error_details = db.Column(Text, nullable=True)  # Full error message for debugging

    # Security monitoring
    ip_address = db.Column(String(45), nullable=True)  # IPv6-compatible length
    user_agent = db.Column(String(255), nullable=True)

    # State expiration (CSRF tokens expire in 1 hour)
    expires_at = db.Column(DateTime, nullable=False, index=True)

    user = relationship('User', backref='oauth_attempts')

    def __repr__(self):
        return f'<OAuthAttempt user_id={self.user_id} result={self.result}>'

    @classmethod
    def cleanup_expired(cls):
        """Delete expired state tokens (run daily via Celery)."""
        cutoff = datetime.utcnow()
        expired = cls.query.filter(cls.expires_at < cutoff).delete()
        db.session.commit()
        return expired
```

### Flask-Session Configuration
```python
# Source: https://testdriven.io/blog/flask-server-side-sessions/
# Location: src/config/session_config.py

from flask_session import Session
import redis
from datetime import timedelta

def configure_session(app):
    """Configure Flask-Session with Redis backend."""

    # Redis connection (reuse connection pool)
    redis_client = redis.from_url(
        app.config['REDIS_URL'],
        decode_responses=False  # Keep bytes for session serialization
    )

    # Session configuration
    app.config['SESSION_TYPE'] = 'redis'
    app.config['SESSION_REDIS'] = redis_client
    app.config['SESSION_PERMANENT'] = False  # Expires on browser close (unless remember_me)
    app.config['SESSION_USE_SIGNER'] = True  # Sign session cookie with SECRET_KEY
    app.config['SESSION_KEY_PREFIX'] = 'session:'  # Redis key: session:abc123

    # Security settings
    app.config['SESSION_COOKIE_SECURE'] = app.config.get('ENV') == 'production'  # HTTPS only in prod
    app.config['SESSION_COOKIE_HTTPONLY'] = True  # Not accessible via JavaScript
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection, allows OAuth redirects
    app.config['SESSION_COOKIE_NAME'] = 'shopify_session'  # Custom name

    # Session lifetime
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)  # Default: 7 days
    # "Remember me" extends to 30 days (set SESSION_PERMANENT=True on login)

    # Initialize Flask-Session
    Session(app)
```

### Registration Route with Email Verification
```python
# Source: https://mailtrap.io/blog/flask-email-verification/
# Location: src/auth/registration.py

from flask import Blueprint, request, jsonify, render_template, url_for
from flask_login import login_user
from src.models.user import User, AccountStatus, UserTier
from src.auth.email_verification import generate_verification_token, send_verification_email
from datetime import datetime, timedelta

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    User registration endpoint.

    Flow: Validate input → Check Stripe payment → Create user → Send verification email

    IMPORTANT: This runs AFTER successful Stripe payment (from webhook).
    User has already selected tier and entered payment info.
    """
    data = request.get_json()

    # Validate required fields
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    tier = data.get('tier')  # From Stripe checkout session metadata
    stripe_customer_id = data.get('stripe_customer_id')  # From Stripe webhook
    stripe_subscription_id = data.get('stripe_subscription_id')

    if not all([email, password, tier, stripe_customer_id]):
        return jsonify({'error': 'Missing required fields'}), 400

    # Check if user already exists
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 400

    # Create user (account_status=PENDING_OAUTH until Shopify OAuth completes)
    user = User(
        email=email,
        tier=UserTier[tier.upper()],  # tier='TIER_2' from Stripe metadata
        account_status=AccountStatus.PENDING_OAUTH,
        email_verified=False,
        stripe_customer_id=stripe_customer_id,
        stripe_subscription_id=stripe_subscription_id,
        oauth_completion_deadline=datetime.utcnow() + timedelta(days=7),  # 7-day grace period
        billing_period_start=datetime.utcnow(),
        billing_period_end=datetime.utcnow() + timedelta(days=30)  # Monthly billing
    )
    user.set_password(password)  # Bcrypt hashing

    db.session.add(user)
    db.session.commit()

    # Generate email verification token (1 hour expiration)
    token = generate_verification_token(user.email)
    user.email_verification_token = token
    db.session.commit()

    # Send verification email (async via Celery)
    verification_url = url_for('auth.verify_email', token=token, _external=True)
    send_verification_email.delay(user.email, verification_url)

    # Log user in (create session)
    login_user(user, remember=False)

    # Return success with next step (Shopify OAuth)
    return jsonify({
        'success': True,
        'message': 'Account created. Check your email for verification link.',
        'next_step': 'connect_shopify',
        'oauth_url': url_for('oauth.shopify_auth', _external=True)
    }), 201
```

### Email Verification Celery Task
```python
# Source: https://testdriven.io/blog/flask-and-celery/
# Location: src/tasks/auth_tasks.py

from src.celery_app import celery
from flask_mail import Message, Mail

@celery.task(name='auth.send_verification_email')
def send_verification_email(email: str, verification_url: str):
    """
    Send email verification link.

    Runs asynchronously via Celery (doesn't block registration request).
    """
    from src.app import app  # Import inside task to avoid circular dependency
    mail = Mail(app)

    msg = Message(
        subject='Verify Your Email - Shopify Multi-Supplier Platform',
        recipients=[email],
        html=f"""
        <h2>Welcome to Shopify Multi-Supplier Platform!</h2>
        <p>Click the link below to verify your email address:</p>
        <p><a href="{verification_url}">Verify Email</a></p>
        <p>This link expires in 1 hour.</p>
        <p>If you didn't create an account, please ignore this email.</p>
        """
    )

    mail.send(msg)
    return {'email': email, 'status': 'sent'}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| OAuth 2.0 (PKCE optional) | OAuth 2.1 (PKCE mandatory) | 2023 RFC 9700 | PKCE now required for ALL clients (not just SPAs). Prevents authorization code interception attacks. Use S256 code challenge method. |
| Client-side sessions (signed cookies) | Server-side sessions (Redis) | 2018+ (industry shift) | Redis session storage is now standard for production SaaS. Client-side sessions leak data (visible in browser), have 4KB limit, vulnerable to replay attacks. |
| Argon2id for password hashing | Bcrypt still dominant | 2023 (no clear winner) | Argon2id won 2015 password hashing competition, but bcrypt still preferred in Flask ecosystem (better library support, Flask-Bcrypt). Use bcrypt unless high-security requirements demand Argon2. |
| Supabase Auth free tier permanent | Supabase free tier auto-pauses | 2025 policy change | Supabase now pauses free tier projects after 7 days inactivity. Makes free tier unsuitable for production SaaS. Use Flask-Login for full control. |
| Stripe creates prorations for all changes | Manual proration_behavior control | 2022 Stripe API update | Stripe added `proration_behavior` parameter. Set to 'none' for downgrades to prevent refund credits. Default 'create_prorations' is correct for upgrades. |
| Flask session cookies with SECRET_KEY | Flask-Session with Redis + SECRET_KEY | 2020+ (best practice) | Flask's default sessions are client-side (data in cookie). Flask-Session moves data to Redis, cookie only contains session ID. More secure, no size limit. |

**Deprecated/outdated:**
- **Flask-Security:** Monolithic auth library (includes login, registration, password reset, 2FA). Deprecated in favor of modular approach (Flask-Login + Flask-Session + custom routes). Too opinionated, hard to customize.
- **OAuth 2.0 without PKCE:** OAuth 2.1 mandates PKCE for authorization code flow. Don't skip PKCE even for server-side apps (protects against authorization code interception).
- **itsdangerous.Signer (plain signatures):** Use `URLSafeTimedSerializer` instead. Adds timestamp for automatic expiration, URL-safe encoding for links.
- **JWT in HTTP-only cookies without CSRF protection:** JWTs in cookies are vulnerable to CSRF. Use Flask-JWT-Extended with CSRF protection or stick with Flask-Login sessions.

## Open Questions

Things that couldn't be fully resolved:

1. **Flask-Login current version and latest features**
   - What we know: Flask-Login 0.7.0 is widely referenced in 2025-2026 documentation, provides UserMixin and @login_required decorator
   - What's unclear: Official documentation was not accessible via WebFetch (404 error), couldn't verify if 0.7.0 is absolute latest or if newer version exists
   - Recommendation: Verify Flask-Login version during implementation with `pip show flask-login`, check GitHub releases for latest

2. **Supabase Auth integration complexity with existing PostgreSQL**
   - What we know: Supabase provides managed auth with 50k MAU free tier, flask-supabase extension exists for integration
   - What's unclear: How Supabase Auth integrates with existing PostgreSQL User model - does it require separate Supabase database or can it authenticate against existing users table?
   - Recommendation: If choosing Supabase (not recommended), prototype integration first to understand data sync requirements. Likely requires webhook-based sync between Supabase auth users and PostgreSQL app users.

3. **Shopify OAuth scopes for product management**
   - What we know: Shopify OAuth requires scope parameter (e.g., 'read_products,write_products'), user can deny specific scopes during authorization
   - What's unclear: Exact scope string needed for this app's product management features - does it need write_inventory, write_price_rules, write_orders?
   - Recommendation: Start with minimal scopes ('read_products,write_products'), add additional scopes as features require. Document scope requirements in Shopify OAuth initiation route.

4. **Stripe subscription schedule API vs immediate subscription updates**
   - What we know: Stripe has two APIs for changing subscriptions - `Subscription.modify()` (immediate) and `SubscriptionSchedule` (scheduled changes)
   - What's unclear: Which API is better for scheduled downgrades - does `SubscriptionSchedule` provide better audit trail or UX for "Your downgrade takes effect on [date]"?
   - Recommendation: Start with `Subscription.modify()` + `pending_tier` in database (simpler, well-documented). Evaluate `SubscriptionSchedule` API if downgrades become complex (e.g., multiple scheduled changes).

5. **Rate limiting strategy for OAuth retries**
   - What we know: Unlimited OAuth retry attempts are user-friendly, but could be abused for DDoS against Shopify
   - What's unclear: Should rate limiting be per-user (5 attempts per hour) or per-IP (20 attempts per hour from same IP)? What if legitimate user has network issues and needs 10+ retries?
   - Recommendation: Implement generous per-user rate limit (10 OAuth attempts per hour), track in `oauth_attempts` counter. If abuse detected, add per-IP rate limiting with Flask-Limiter.

6. **Email verification required before OAuth or after?**
   - What we know: CONTEXT.md says "Cannot connect Shopify store until email confirmed", but also shows OAuth happening during signup flow
   - What's unclear: Exact order of operations - does email verification block OAuth initiation, or can user start OAuth before verifying email (but block token storage)?
   - Recommendation: Allow OAuth to start immediately after payment (better conversion), but block storing access token until email verified. Show "Verify your email to complete setup" banner during OAuth flow.

## Sources

### Primary (HIGH confidence)
- Flask-Bcrypt official documentation - https://flask-bcrypt.readthedocs.io/ - Password hashing configuration, work factor recommendations
- Shopify OAuth documentation - https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens/authorization-code-grant - Authorization code grant flow, security validations, error handling
- Stripe Subscriptions documentation - https://docs.stripe.com/billing/subscriptions/change and https://docs.stripe.com/billing/subscriptions/prorations - Subscription modification, proration behavior, webhook events
- OAuth 2.1 specification - RFC 9700, https://oauth.net/2.1/, https://datatracker.ietf.org/doc/rfc9700/ - PKCE requirements, state parameter validation, security best practices
- Existing codebase analysis - src/models/user.py (UserTier enum), src/models/shopify.py (ShopifyStore with encryption), src/core/encryption.py (Fernet implementation), docker-compose.yml (Redis configuration)

### Secondary (MEDIUM confidence)
- [Flask Security Best Practices 2025](https://hub.corgea.com/articles/flask-security-best-practices-2025) - CSRF protection, HttpOnly cookies, bcrypt recommendations
- [Flask Email Verification Tutorial 2026](https://mailtrap.io/blog/flask-email-verification/) - itsdangerous URLSafeTimedSerializer pattern, token expiration best practices
- [Session Management in Multi-Container Environments Using Redis](https://medium.com/@ssksreehari/session-management-in-multi-container-environments-using-redis-50d507e893e9) - Redis session persistence across containers
- [Flask + Celery Background Tasks](https://oneuptime.com/blog/post/2026-02-02-flask-celery-background-tasks/view) - Celery task patterns for email sending
- [OAuth 2.1 Features You Can't Ignore in 2026](https://rgutierrez2004.medium.com/oauth-2-1-features-you-cant-ignore-in-2026-a15f852cb723) - PKCE mandate, state validation, redirect URI matching
- [Supabase Pricing 2026 Breakdown](https://www.metacto.com/blogs/the-true-cost-of-supabase-a-comprehensive-guide-to-pricing-integration-and-maintenance) - Free tier limits (50k MAU, 7-day auto-pause), pricing model

### Tertiary (LOW confidence)
- [Flask Role-Based Access Control](https://www.geeksforgeeks.org/python/flask-role-based-access-control/) - Decorator pattern examples (not verified against official Flask documentation)
- [Supabase vs Flask: Choosing Backend Solution](https://supalaunch.com/about/supabase-vs-flask) - Comparison article (vendor perspective, may be biased)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Flask-Login, Flask-Session, Flask-Bcrypt are documented in official sources, versions verified via multiple WebSearch results, existing codebase analysis confirms PostgreSQL + Redis architecture
- Architecture: HIGH - Patterns verified against official Shopify, Stripe, and OAuth documentation, code examples from authoritative sources (Flask docs, Stripe docs, Shopify dev portal)
- Pitfalls: MEDIUM - Based on WebSearch results and security best practices articles, not all verified against official security audits, but consistent across multiple sources
- Supabase integration: LOW - Supabase documentation not deeply researched (decision leans toward Flask-Login), integration complexity with existing PostgreSQL unclear

**Research date:** 2026-02-09
**Valid until:** 2026-03-11 (30 days for stable technologies - Flask, Redis, bcrypt patterns are mature and slow-moving)
