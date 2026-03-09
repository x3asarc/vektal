# Phase 18 — SaaS Production Readiness

**Status:** PLANNING  
**Created:** 2026-03-09  
**Input:** Commander codebase audit + SaaS/Shopify research (see research-input.md)  
**Goal:** Transform Vektal from a localhost-capable app into a shippable, commercially viable SaaS product accessible via the Shopify App Store.

---

## Success Criteria

- [ ] Zero critical security blockers (B1–B6 all resolved)
- [ ] A new user can self-register, connect a Shopify store, and subscribe — without human intervention
- [ ] Shopify App Store review passes (GDPR webhooks, App Bridge session tokens, privacy policy)
- [ ] Email system is live (Resend, verified domain, SPF/DKIM/DMARC)
- [ ] Billing is end-to-end testable (Stripe + Shopify Billing API)
- [ ] agnix: 0 errors across all agent/skill configs

---

## Sub-Plans

| ID | Title | Priority | Status | Effort |
|---|---|---|---|---|
| 18.0 | Security hardening (secrets rotation, FLASK_DEBUG, Fernet fallback) | P0 | TODO | 3h |
| 18.1 | Stripe billing fix (price IDs, webhook idempotency, Customer Portal) | P1 | TODO | 1 day |
| 18.2 | Email system (Resend wiring, verified domain, templates) | P1 | TODO | 1 day |
| 18.3 | Registration + pricing page (frontend → Stripe/Shopify checkout) | P1 | TODO | 2 days |
| 18.4 | Shopify compliance (GDPR webhooks, GraphQL API migration, App Bridge session tokens) | P1 | TODO | 2-3 days |
| 18.5 | Password reset flow | P2 | TODO | 1 day |
| 18.6 | Frontend billing UI (plan display, upgrade/downgrade, invoice) | P2 | TODO | 1 day |
| 18.7 | Security hardening round 2 (CSRF, Flower proxy, /doctor auth, login rate limit) | P2 | TODO | 1 day |
| 18.8 | Onboarding wizard (4-step: supplier connect → field map → test sync → billing) | P2 | TODO | 2-3 days |
| 18.9 | Production infrastructure (Certbot auto-renewal, Dockerfile pip bake, pgBouncer) | P3 | TODO | 1 day |
| 18.10 | PostgreSQL RLS + tenant isolation test suite | P3 | TODO | 2 days |
| 18.11 | Admin operator dashboard (tenant list, impersonation, kill-switch UI, billing overview) | P3 | TODO | 3-5 days |
| 18.12 | Observability (Sentry PII scrubbing, sample rates, structured logs, uptime monitoring) | P3 | TODO | 1 day |
| 18.13 | GDPR compliance UI (data export, account deletion, privacy policy, DPA) | P3 | TODO | 2 days |
| 18.14 | Audit log system (append-only, B2B read-only UI) | P4 | TODO | 2 days |
| 18.15 | Feature flags (Flagsmith/Unleash self-hosted, per-tenant rollout) | P4 | TODO | 1 day |

---

## Ordering Rationale

**18.0 before everything** — secrets are a live security risk right now.  
**18.1–18.4 as a block** — without billing + email + registration + Shopify compliance, the app cannot acquire a single real user.  
**18.5–18.8 as a block** — required for retention and self-service (users who can't reset passwords churn immediately).  
**18.9–18.13 as a block** — production hardening before any marketing/App Store traffic.  
**18.14–18.15** — growth features, build once B2B momentum starts.

---

## Key Files (from audit)

| File | Issue |
|---|---|
| `.env` lines 12-158 | Real secrets — rotate everything |
| `.env` line 18 | Placeholder `FLASK_SECRET_KEY` |
| `docker-compose.yml` line 63 | `FLASK_DEBUG:-1` default |
| `docker-compose.yml` lines 67,138,197,249 | Hardcoded Fernet fallback |
| `src/billing/webhooks.py` line 75 | Idempotency TODO |
| `src/billing/stripe_client.py` lines 36-38 | Price ID fallbacks to invalid strings |
| `src/config/email_config.py` lines 30,33 | Wrong env var + `noreply@example.com` |
| `docker-compose.yml` lines 292,298 | Flower default creds, exposed port |
| `src/api/app.py` line 252 | `/doctor` unauthenticated |

---

## Research References

- `research-input.md` (this directory) — full Commander audit + SaaS research findings
- Shopify: GraphQL mandatory since April 1 2025, GDPR webhooks via `shopify.app.toml`
- Billing: Shopify Billing API for App Store + Stripe for direct installs
- Compliance: GDPR mandatory (EU merchants), SOC 2 Type I before enterprise sales
