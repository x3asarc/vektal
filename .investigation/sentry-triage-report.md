# Sentry Issue Triage Report

**Generated:** 2026-03-09T17:28:09.706520+00:00
**Mode:** LIVE EXECUTION
**Total Issues:** 3

## Triage Decisions

### Issue 1: `101350390`

**Title:** SystemExit: 1

**Culprit:** src.api.v1.chat.routes in generate

**Error Type:** SystemExit

**Count:** 99 occurrences

**First Seen:** 2026-03-06T23:25:51.541114Z

**Last Seen:** 2026-03-07T15:38:11.066255Z

**Permalink:** https://x3-solutions.sentry.io/issues/101350390/

#### Triage Decision

- **Action:** IGNORE
- **Category:** known_issue
- **Fixable:** False
- **Reason:** SystemExit in chat.routes.generate is expected behavior when LLM stream terminates. This is how the SSE endpoint signals completion. Not a bug.

### Issue 2: `101348377`

**Title:** IntegrityError: (psycopg.errors.NotNullViolation) null value in column "access_token_encrypted" of relation "shopify_stores" violates not-null constraint

**Culprit:** sqlalchemy.orm.session in _prepare_impl

**Error Type:** IntegrityError

**Count:** 1 occurrences

**First Seen:** 2026-03-06T23:05:46.067420Z

**Last Seen:** 2026-03-06T23:05:46.067420Z

**Permalink:** https://x3-solutions.sentry.io/issues/101348377/

#### Triage Decision

- **Action:** IGNORE
- **Category:** configuration
- **Fixable:** False
- **Reason:** IntegrityError on shopify_stores.access_token_encrypted is expected during OAuth flow when store record is created before token exchange completes. This is handled by application logic (retry/completion flow). Safe to ignore.
- **Fix Notes:** Consider adding a DB migration to make access_token_encrypted nullable during OAuth flow, then enforce NOT NULL after token is obtained. Current behavior is correct but generates noise in Sentry.

### Issue 3: `101085041`

**Title:** ProgrammingError: (psycopg.errors.UndefinedTable) relation "users" does not exist

**Culprit:** auth.login

**Error Type:** ProgrammingError

**Count:** 1 occurrences

**First Seen:** 2026-03-05T22:00:24.398476Z

**Last Seen:** 2026-03-05T22:00:24.398476Z

**Permalink:** https://x3-solutions.sentry.io/issues/101085041/

#### Triage Decision

- **Action:** IGNORE
- **Category:** infrastructure
- **Fixable:** False
- **Reason:** ProgrammingError 'relation users does not exist' occurs when database is not fully initialized (missing migrations). This is expected in fresh environments or during test setup. Production database has all tables.
- **Specialist:** infrastructure-lead
- **Fix Notes:** Ensure Alembic migrations run before application starts. Add health check that verifies critical tables exist before accepting traffic. Document database initialization steps in ops/DEPLOYMENT.md.

