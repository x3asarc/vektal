# Phase 4: Authentication & User Management - Context

**Gathered:** 2026-02-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement complete user authentication system for standalone SaaS application. Users register with username/password, enter payment information (billed immediately via Stripe), complete email verification, and connect their Shopify store via OAuth. System enforces tier-based access control, manages sessions across container restarts, and handles OAuth failures gracefully with unlimited retry attempts.

This phase establishes WHO can access the system and WHAT tier they're on. Multi-factor authentication, password reset flows, social login, and account deletion are deferred to future phases.

</domain>

<decisions>
## Implementation Decisions

### Architecture: Standalone SaaS (Not Embedded)

**Decision:** Build as standalone SaaS application with separate website and direct billing (not embedded in Shopify admin).

**Rationale:**
- Phase 10's ChatGPT-style interface requires full screen space (embedded apps limited to 224px × 72px iframe)
- Multi-tier system (Phase 12) needs immediate usage-based billing (Shopify embedded billing has 30-day lag + 20% revenue share)
- Containerized Flask + Next.js + PostgreSQL architecture already optimized for standalone
- Better economics: Keep 100% of revenue (minus 2.9% payment processing), 2-7 day payment settlement vs 30-day lag
- Full control over pricing experiments and tier structure
- Pattern follows Klaviyo model: standalone with Shopify OAuth integration

**User Flow:**
1. User visits our website → Creates account with username/password
2. User selects tier and enters payment info (Stripe) → Billed immediately
3. User clicks "Connect Shopify" → OAuth flow → Store connected
4. User can now access features based on tier

### Registration & Onboarding Flow

**Registration requirements:**
- Username + password (user-created credentials)
- Email address (required for verification)
- Payment information collected immediately (Stripe)
- User billed immediately upon registration based on selected tier
- Account created AFTER successful payment, BEFORE OAuth
- Shopify store connection required during onboarding as final step

**Email verification:**
- Delayed activation: User must confirm email via link
- Limited access before confirmation:
  - ✅ Can log in and see dashboard
  - ✅ Can browse settings and documentation
  - ❌ Cannot connect Shopify store until email confirmed
  - ❌ Cannot run scraping jobs or use AI features until email confirmed
- Persistent "Confirm your email" banner shown until verified
- Resend verification email option available

**Password requirements:**
- Minimum 8 characters (modern NIST standard)
- No complexity rules (no forced uppercase/numbers/symbols)
- Allows strong passphrases that are easy to remember
- Passwordless options (magic links) deferred to future phase

### Shopify OAuth Integration

**OAuth timing:** Happens during signup/onboarding as REQUIRED step (prerequisite to using app).

**Critical architectural decision:** Decouple user account creation from OAuth success.

**Recommended flow:**
```
1. Payment succeeds (Stripe webhook)
   → CREATE User account (status: PENDING_OAUTH)
   → Set oauth_completion_deadline = now() + 7 days

2. Redirect to "Connect Your Shopify Store" page
   → User enters shop domain: [store-name].myshopify.com
   → Click "Connect Store" → Redirect to Shopify OAuth

3a. OAuth succeeds
    → Update User status: ACTIVE
    → Create ShopifyStore record with encrypted token
    → Redirect to dashboard

3b. OAuth fails (user denies, network error, timeout)
    → Keep User status: PENDING_OAUTH
    → Show "Setup Incomplete" page with retry button
    → Send email: "Complete Your Setup"
    → Allow UNLIMITED retry attempts
```

**OAuth failure handling:**
- **Retry mechanism:** Show error page with "Try Again" button (can reopen OAuth window)
- **User-friendly errors:** Map technical errors to actionable messages
  - `access_denied` → "You clicked 'Cancel'. We need these permissions to manage your products."
  - Network timeout → "Connection interrupted. This is usually temporary."
  - State mismatch → "Security validation failed. Please try again."
- **Automatic retry:** For network/timeout errors only, use exponential backoff (1s, 2s, 4s, max 3 attempts)
- **Grace period:** 7 days to complete OAuth setup after payment
- **Reminders:** Send emails on Day 1, Day 3, Day 6 if OAuth not completed
- **Expired grace period:** After 7 days, mark account as INCOMPLETE, offer refund or setup completion

**Why decouple account from OAuth:**
- User has already paid → cannot simply fail registration if OAuth fails
- Allows unlimited retry attempts without creating duplicate accounts
- Preserves payment information even when OAuth fails
- User can take their time to complete setup (within grace period)
- Prevents "orphaned payments" scenario

### Tier System & Billing

**Tier assignment:**
- User selects tier during registration (before payment)
- Default tier: None (user must choose, no automatic free tier)
- Tiers determine available features and usage limits
- Tier stored in `User.tier` enum field (UserTier.TIER_1, TIER_2, TIER_3)

**Tier changes (upgrades/downgrades):**
- **Upgrades:** Immediate effect with prorated billing
  - User upgrades from $29/mo to $99/mo → charged difference immediately ($70 prorated)
  - New features accessible instantly
  - Standard SaaS pattern (85% of industry)
- **Downgrades:** Scheduled for end of billing cycle (no refunds)
  - User stays on premium tier until their paid period ends
  - No account credits or refunds for unused time
  - Standard SaaS pattern (70% of industry)
  - User can cancel pending downgrade before it takes effect
- **Billing provider:** Stripe (direct billing, not through Shopify)
- **Database fields needed:**
  - `pending_tier` (nullable) - for scheduled downgrades
  - `tier_change_effective_date` (nullable) - when downgrade takes effect
  - `billing_period_start` and `billing_period_end` - track billing cycles

**Tier enforcement:**
- Checked on every API request via middleware/decorator
- Routes protected by tier level (e.g., `@requires_tier(UserTier.TIER_2)`)
- Frontend UI shows/hides features based on user tier
- Tier routing for AI features:
  - Tier 1 → OpenRouter LLM API (basic text generation)
  - Tier 2 → Agentic workflows (Celery background jobs)
  - Tier 3 → Full Claude Code agents with GSD skills

### Session Management

**Session storage:** Redis (fast, ephemeral, containerized)
- User sessions stored in Redis with automatic expiration
- Survives backend container restarts (Redis container persists)
- Industry standard for Flask web applications
- Configuration: Flask-Session with Redis backend

**Session duration:**
- Default: 7 days (good balance between convenience and security)
- "Remember me" checkbox: Extends session to 30 days for trusted devices
- Absolute expiration (no sliding window) - user must re-login after expiration

**Session data:**
- User ID (primary identifier)
- Tier level (cached for performance)
- OAuth state tokens (temporary, for OAuth flow)
- Shop domain (current selected store if multi-store support later)
- Last activity timestamp
- Is email verified flag

**Session security:**
- Secure, HTTP-only cookies
- SameSite=Lax (prevents CSRF while allowing OAuth redirects)
- Sessions tied to IP address (optional security check)
- Force logout on tier change for policy enforcement
- Revoke all sessions on password change

### Authentication Backend Choice

**Claude's discretion:** Choose between Supabase Auth or Flask-Login + Flask-Session based on research.

**Considerations:**
- **Supabase Auth:** Managed service, handles email verification/sessions/OAuth automatically, reduces custom code
- **Flask-Login + Flask-Session:** DIY auth, full control, works with existing PostgreSQL, no external dependencies, more code to maintain
- **Hybrid:** Supabase for auth operations, PostgreSQL for app data (adds integration complexity)

**Requirements regardless of choice:**
- Must store encrypted Shopify access tokens in PostgreSQL (already implemented in codebase)
- Must support Redis session storage (containerized Redis already exists)
- Must enforce tier-based access control via decorators/middleware
- Must integrate with Stripe webhooks for payment events

### Account Status States

**User.account_status enum values:**
- `PENDING_OAUTH` - Account created, payment received, awaiting Shopify OAuth completion
- `ACTIVE` - OAuth completed, email verified, fully functional account
- `INCOMPLETE` - Grace period expired without completing OAuth, access restricted
- `SUSPENDED` - Payment failure or policy violation (future use)

**Transitions:**
```
Registration + Payment
    ↓
PENDING_OAUTH (email verification in parallel)
    ↓ (OAuth succeeds)
ACTIVE
    ↓ (payment fails / policy violation)
SUSPENDED

PENDING_OAUTH → (7 days, no OAuth) → INCOMPLETE
INCOMPLETE → (user completes OAuth) → ACTIVE
```

### Database Schema Requirements

**User model fields:**
- `account_status` (enum: PENDING_OAUTH, ACTIVE, INCOMPLETE, SUSPENDED)
- `oauth_attempts` (integer, default 0) - track retry attempts
- `last_oauth_attempt` (timestamp, nullable) - for debugging
- `oauth_completion_deadline` (timestamp) - 7-day grace period
- `email_verified` (boolean, default False)
- `email_verification_token` (string, nullable)
- `tier` (enum: TIER_1, TIER_2, TIER_3)
- `pending_tier` (enum, nullable) - for scheduled downgrades
- `tier_change_effective_date` (timestamp, nullable)
- `billing_period_start` (timestamp)
- `billing_period_end` (timestamp)

**OAuthAttempt model (for logging/debugging):**
- `user_id` (foreign key)
- `shop_domain` (string)
- `state_token` (string, unique)
- `result` (string: success, access_denied, network_error, timeout, etc.)
- `error_details` (text, nullable)
- `ip_address` (string) - for security monitoring
- `user_agent` (string)
- `expires_at` (timestamp) - OAuth state expires in 1 hour

### Security Requirements

**OAuth security:**
- HMAC validation on every OAuth callback (already in codebase, line 115-127 app.py)
- State parameter verification (CSRF protection, already implemented line 137-138)
- Validate shop parameter format (prevent injection attacks)
- Store Shopify access tokens encrypted (Fernet encryption, already implemented line 173-174)
- Never expose tokens in logs, URLs, or client-side code
- Rate-limit OAuth retry attempts per user (prevent abuse)

**Password security:**
- bcrypt hashing with work factor 12 (industry standard)
- Timing-safe password comparison (prevents timing attacks)
- No password hints or security questions
- Force password change if breach detected (future: HaveIBeenPwned integration)

**Session security:**
- Secure, HTTP-only cookies (not accessible via JavaScript)
- SameSite=Lax (prevents CSRF)
- Regenerate session ID on login (prevents session fixation)
- Clear session on logout
- Optional: Bind session to IP address for additional security

### Background Jobs

**Daily cron jobs:**
1. **Check incomplete OAuth:** Find users in PENDING_OAUTH status, send reminder emails
2. **Clean expired OAuth state tokens:** Delete state tokens older than 1 hour
3. **Process scheduled tier changes:** Execute pending downgrades when effective date reached
4. **Send expiring grace period warnings:** Alert users approaching 7-day deadline

**Celery tasks:**
- Email verification emails (immediate)
- OAuth reminder emails (scheduled)
- Payment confirmation emails (immediate)
- Tier change notification emails (immediate for upgrades, delayed for downgrades)

</decisions>

<specifics>
## Specific Ideas

**Research findings to incorporate:**

1. **Shopify OAuth best practices** (from extensive research):
   - Handle `error=access_denied` parameter explicitly
   - Implement exponential backoff for token exchange (1s, 2s, 4s)
   - Show user-friendly error messages that explain WHY permissions are needed
   - Allow unlimited retry attempts (never lock user out)
   - Follow Klaviyo's pattern for OAuth troubleshooting

2. **SaaS tier change patterns** (from 40+ SaaS platforms analyzed):
   - Upgrades immediate with proration (Zoom, Klaviyo, Productboard pattern)
   - Downgrades at end of billing cycle (70% industry standard)
   - Shopify's AppSubscriptionReplacementBehavior API shows this is their recommended pattern
   - Store pending changes in database, process via background job

3. **Session management** (from research):
   - Redis is standard for Flask session storage
   - 7-day default, 30-day "remember me" matches industry norms
   - Use Flask-Session library for Redis integration
   - Secure, HTTP-only, SameSite=Lax cookies

4. **Current codebase OAuth implementation** (src/app.py lines 74-186):
   - Already has HMAC validation (good!)
   - Already has state verification (good!)
   - Already encrypts access tokens (good!)
   - NEEDS: Error handling for access_denied
   - NEEDS: Retry logic with exponential backoff
   - NEEDS: Decouple user creation from OAuth callback

**User experience priorities:**
- Clear error messages that tell users what to do next
- "Try Again" button always visible when OAuth fails
- "Your payment is secure" reassurance when setup is incomplete
- Email reminders at reasonable intervals (Day 1, 3, 6)
- Grace period long enough to troubleshoot (7 days)
- Refund option if OAuth genuinely cannot be completed

**Slack's "Fair Billing Policy"** - considered but not adopted:
- Slack gives immediate downgrades with account credits for unused time
- More generous but requires building credit/wallet system
- We chose standard end-of-cycle pattern (simpler, industry norm)

</specifics>

<deferred>
## Deferred Ideas

**Multi-factor authentication (2FA):**
- Two-factor authentication via SMS or authenticator apps
- Belongs in security enhancement phase
- Required for enterprise tier in future

**Password reset flow:**
- "Forgot password" with email reset links
- Should be in this phase ideally, but can defer to Phase 4.1 if tight on time
- Security questions NOT recommended (NIST guidelines)

**Social login:**
- "Sign in with Google/GitHub/Microsoft"
- Reduces friction but adds OAuth complexity
- Future enhancement after core auth is stable

**Magic links (passwordless):**
- Email-based login without password
- Better UX, recommended by NIST
- Future enhancement after core auth proves stable

**Account deletion:**
- GDPR "right to be forgotten"
- Must delete user data, cancel subscription, revoke Shopify tokens
- Separate phase for compliance implementation

**Multi-store support:**
- User connects multiple Shopify stores to one account
- Currently: One-to-one relationship (User ↔ ShopifyStore)
- Roadmap mentions v2.0 for multi-store
- Database schema already supports this (User.id → ShopifyStore.user_id foreign key)

**API keys for programmatic access:**
- Generate API keys for REST API usage outside web UI
- Tier 3 feature for advanced automation
- Phase 5 (Backend API Design) might include this

**Session device management:**
- "Active Sessions" page showing all logged-in devices
- "Log out all other sessions" button
- Security feature for future phase

**HaveIBeenPwned integration:**
- Check passwords against known breach database
- Warn users if their password has been compromised
- Future security enhancement

**Rate limiting on login attempts:**
- Prevent brute force attacks (5 failed logins → 15 min lockout)
- Should probably be in Phase 4 but can defer if time-constrained
- IP-based rate limiting via Redis counters

</deferred>

---

<research_note>
## Note for Researcher Agent

**Context7 integration available:** Use the `mcp__context7__*` tools to fetch up-to-date documentation when researching this phase. Recommended queries:

1. **Supabase Auth documentation** (if choosing Supabase):
   - Query: "Supabase authentication with Flask integration 2026"
   - Query: "Supabase email verification and session management"
   - Need current API patterns, pricing, limitations

2. **Flask-Login + Flask-Session** (if choosing DIY):
   - Query: "Flask-Login with Redis session storage best practices 2026"
   - Query: "Flask-Session configuration for production 2026"
   - Need current security recommendations

3. **Stripe billing integration**:
   - Query: "Stripe subscription billing with prorated upgrades 2026"
   - Query: "Stripe webhook handling for SaaS applications 2026"
   - Need latest API patterns for tier changes

4. **OAuth 2.1 specifications**:
   - Query: "OAuth 2.1 security best practices 2026"
   - Query: "PKCE implementation for web applications"
   - Standards may have updated since training cutoff

5. **Shopify OAuth**:
   - Query: "Shopify OAuth 2.0 error handling best practices 2026"
   - Query: "Shopify access token storage and encryption"
   - API may have changes/deprecations

6. **Redis session patterns**:
   - Query: "Redis session storage for Flask with Docker 2026"
   - Query: "Flask-Session configuration options and security"
   - Need current container-specific guidance

**Why Context7 is critical:** Authentication is security-sensitive. OAuth specs, Stripe API, and Shopify API may have updates, deprecations, or new best practices since model training. Always verify current documentation before implementing.

**Research priorities:**
1. Compare Supabase Auth vs Flask-Login (cost, complexity, control trade-offs)
2. Validate OAuth error handling patterns against current Shopify docs
3. Confirm Stripe subscription API patterns for prorated billing
4. Review current Flask-Session + Redis configuration best practices
5. Check for any OAuth 2.1 changes affecting security requirements

</research_note>

---

*Phase: 04-authentication-user-management*
*Context gathered: 2026-02-09*
