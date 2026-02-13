# 07-01 Current State

## Scope
Phase 7 frontend onboarding/auth flow diagnostics, focused on why onboarding Step 3 fails.

## Confirmed Current State
- Route/UI state observed: `/onboarding` -> `Step 3: Preview and Start Import`.
- Error observed on submit: `Connect a Shopify store before launching ingest jobs. (HTTP 409)`.
- This is expected by backend guard in `src/api/v1/jobs/routes.py` when `current_user.shopify_store` is missing.

## Backend Reality (verified)
- User: `dev@local.test`
- `email_verified`: `true`
- `account_status`: `pending_oauth`
- `has_shopify_store`: `false`
- Result: job creation is blocked until OAuth callback completes and store is attached.

## OAuth Diagnostics
- OAuth initiation endpoint works and returns an auth URL for `e68099-e4.myshopify.com`.
- OAuth attempts table shows multiple attempts, all still `pending`.
- Interpretation: callback completion has not happened successfully for this user/session yet.

## Infrastructure Notes
- Backend health endpoint returns DB connected (`/health` OK).
- Rate limiting temporarily blocked API probing (`429`) during diagnostics; limiter keys were identified and cleared for local IP to continue debugging.

## Why We Still See 409
Frontend can reach Step 3, but backend account state is still `pending_oauth` with no connected Shopify store. Until backend flips to active/connected, Step 3 will continue returning 409.

## Resume Steps
1. Log in through backend login UI (`/auth/login`) as `dev@local.test`.
2. Start Shopify connect for `e68099-e4.myshopify.com` from the same browser session.
3. Complete Shopify approval and allow redirect back to `http://localhost:5000/oauth/callback`.
4. Verify `/api/v1/auth/me` shows connected/active status.
5. Retry onboarding Step 3 (`Preview and Start Import`).

## Next Verification On Resume
- Re-check DB user state and `shopify_store` relation.
- Confirm `/api/v1/jobs` accepts request (202) instead of 409.
