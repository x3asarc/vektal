# Phase 18 Research Input — SaaS Production Readiness

*Source: Commander codebase audit + web research, 2026-03-09*

## Commander Codebase Audit Summary

### Critical Blockers Found (file-referenced)

**B1 — Secrets in .env:**
Real credentials committed: Shopify API key/secret (lines 12-13), Stripe keys (lines 73-75), Google Gemini key (line 86), OpenRouter keys (lines 90, 98), PostgreSQL password (line 104), Firecrawl key (line 132), Hetzner token (line 133), Neo4j Aura password (line 144), Dokploy admin in comment (line 156), ENCRYPTION_KEY Fernet key (line 158), Sentry DSNs/token (lines 29-32).

**B2 — FLASK_SECRET_KEY:**
`.env` line 18: `FLASK_SECRET_KEY=change-this-to-a-random-secret-key-in-production`
All sessions are forgeable. Every authenticated endpoint is compromised.

**B3 — FLASK_DEBUG default:**
`docker-compose.yml` line 63: `FLASK_DEBUG=${FLASK_DEBUG:-1}`
Werkzeug interactive debugger active by default. Arbitrary code execution via PIN brute-force.

**B4 — Fernet key hardcoded fallback:**
`docker-compose.yml` lines 67, 138, 197, 249: `ENCRYPTION_KEY=${ENCRYPTION_KEY:-QJhl0AK...}`
All four containers use a public Fernet key if env var not set. All Shopify OAuth tokens decryptable.

**B5 — Stripe webhook idempotency TODO:**
`src/billing/webhooks.py` line 75: `# TODO: Store processed event IDs in Redis with TTL`
`handle_checkout_completed` creates user accounts. Stripe retries → duplicate users.

**B6 — Stripe price IDs:**
`src/billing/stripe_client.py` lines 36-38: fallback to `'price_tier1_monthly'` (invalid Stripe ID).
`STRIPE_PRICE_TIER_1/2/3` absent from `.env`. Entire checkout flow returns Stripe error.

### Missing Features (file-referenced)

- Password reset: `src/auth/email_sender.py` line 9 explicitly defers to Phase 4.1 (never done)
- Frontend registration: only `/login` and `/verify` pages exist. No `/signup` or `/pricing`
- Frontend billing UI: 9 billing files in `frontend/src` but none are management pages
- Stripe Customer Portal: no `stripe.billing_portal.Session.create()` anywhere
- Dunning emails: `webhooks.py` lines 260, 284, 287 — three TODOs
- CSRF: no Flask-WTF or CSRF middleware in `src/api/app.py`
- Custom domain: `nginx/nginx.conf` hardcoded to `app.vektal.systems`
- SSL auto-renewal: certs mounted read-only, no Certbot container

### Partial Issues (file-referenced)

- Email: `email_config.py` line 30 reads `MAIL_PASSWORD` but `.env` has `RESEND_API_KEY`. Line 33: `MAIL_DEFAULT_SENDER=noreply@example.com`
- Rate limiting: login endpoint has no `@limiter.limit` decorator (TODO in `src/auth/login.py` line 213)
- Flower: `docker-compose.yml` lines 292, 298 — `admin:admin` default, port 5555 directly exposed
- `/doctor` endpoint: `src/api/app.py` line 252 — no `@login_required`, leaks full service topology
- Tenant isolation: all models have `store_id` FKs but PostgreSQL RLS not enabled
- Docker startup: `docker-compose.yml` lines 105-108 — `pip install` at every container start
- Sentry: sample rates all `1.0` (`.env` lines 40-43)
- Dev auth bypass: `frontend/src/app/(auth)/auth/login/page.tsx` line 10 — `NEXT_PUBLIC_DEV_AUTH_BYPASS`

---

## External Research — Shopify Requirements (2025/2026)

### Mandatory Technical Requirements
- **GraphQL Admin API only** — REST deprecated for new public apps (effective April 1, 2025)
- **Session tokens, not cookies** — Shopify blocks third-party cookies in embedded app iframe
- **App Bridge latest version** — mandatory by July 1, 2025
- **Three GDPR webhooks** — `customers/data_request`, `customers/redact`, `shop/redact`
  - Register via `shopify.app.toml` (Partner Dashboard option removed)
  - Must respond before App Store review will pass
- **HMAC validation on every webhook** — constant-time comparison
- **`app/uninstalled` webhook** — must clear access_token + stop billing
- **OAuth `state` parameter** — prevents CSRF in OAuth flow
- **Scopes**: minimum required; adding scopes later requires merchant re-authorization
- **API version pinning**: deprecated quarterly — upgrade every 12 months

### "Built for Shopify" Certification
- Dashboard load < 500ms
- Lighthouse drop < 10pts when app script runs on storefront
- Handles 1,000+ install requests per 28 days without degradation
- Dramatically increases App Store conversion

### Billing — Shopify Billing API
- Required for App Store listing (merchants pay through Shopify invoice)
- Types: time-based (monthly/annual), usage-based (capped), hybrid
- Subscription flow: AppSubscriptionCreate mutation → confirmationUrl → merchant approves → webhook
- Use `trialDays: 14` (Shopify tracks 180-day window to prevent gaming)
- Handle: `ACTIVE`, `CANCELLED`, `FROZEN` (merchant account on hold), `DECLINED`
- App uninstall ≠ cancellation — must handle both independently

---

## External Research — SaaS Best Practices (2025/2026)

### Multi-Tenant Data Isolation
- Shared DB + `tenant_id` recommended for early-stage (<500 tenants)
- PostgreSQL RLS as safety net: `CREATE POLICY tenant_isolation ON products USING (shop_id = current_setting('app.current_shop_id')::UUID)`
- **Most common failure**: `shop_id` missing from background job context → cross-tenant data leak
- Every DB query in async workers must include explicit tenant context

### Authentication
- Multi-user support per shop: track `(shop_id, user_id)` pairs
- Enterprise SSO (WorkOS, Auth0, Clerk) — B2B buyers increasingly require SAML 2.0/OIDC
- Rate limiting: per-tenant, sliding window in Redis, return `429` with `Retry-After`

### Billing Best Practices
- Shopify Billing API for App Store + Stripe for direct/custom installs
- Graceful downgrade on payment failure (don't hard-lock immediately)
- 7-day grace period on cancellation
- Proration logic for mid-cycle upgrades
- Handle `FROZEN` status (Shopify merchant account on hold)

### Email Infrastructure
- Custom domain required: `noreply@yourapp.com`
- DNS: SPF + DKIM + DMARC (non-negotiable for deliverability in 2025)
- Resend recommended (best DX, React Email) + Postmark for critical flows
- Required templates: welcome, email verification, password reset, magic link, trial expiring (3 days before), payment failed, plan changed, sync completed/failed, Shopify disconnected

### GDPR
- Account deletion: cascade to Stripe, Resend, all sub-processors
- Data export: JSON/CSV download within 30 days
- Cookie consent for EU visitors to marketing site
- Privacy policy + DPA (Data Processing Agreement) required for B2B
- Sub-processor registry published publicly
- Sentry PII scrubbing: `beforeSend` hook to strip emails/tokens

### Onboarding (B2B SaaS)
- Users who complete onboarding checklist: 3x more likely to convert
- Time to first value: < 2 minutes
- 4-step wizard: connect supplier → map fields → sync 10 products → billing
- Drip email days 1, 3, 7
- Empty state on first login: show "Get Started" immediately (no blank dashboard)

### Recommended Tool Additions
- pgBouncer (connection pooling)
- Certbot container with `--deploy-hook "nginx -s reload"`
- Flagsmith or Unleash (feature flags, self-hostable)
- AdminJS (auto-generates CRUD admin from DB schema)
- Crisp (free support chat) → Intercom at scale
- BetterStack / Checkly (uptime monitoring every 1min, multi-region)
- Instatus (public status page, free tier)
- Axiom / BetterStack Logs (structured log centralization)
