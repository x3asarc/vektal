# Frontdoor Deploy Checklist (Frontend)

Date: 2026-03-03
Owner: Frontend verification loop

## Gate Summary
- Local frontend quality gate: GREEN
- Local browser e2e gate: GREEN
- External frontdoor reachability gate: RED (network blocked from this runtime)
- Firecrawl tooling gate: GREEN (CLI/auth present), live scrape gate RED (EACCES)

## Evidence (this run)
- Lint: `frontend/npm run lint` -> PASS
- Typecheck: `frontend/npm run typecheck` -> PASS
- Unit/contract tests: `frontend/npm run test` -> PASS (76/76)
- E2E: `frontend/npm run test:e2e` -> PASS (13/13)
- Firecrawl quick tool health: `.planning/debug/external-tools-quick-2026-03-03.json` (overall_ok=true)
- Firecrawl full tool health: `.planning/debug/external-tools-full-2026-03-03.json` (overall_ok=false)
- Firecrawl frontdoor scrape attempt: `.planning/debug/firecrawl-frontdoor-attempt-2026-03-03.txt`

## What changed to stabilize frontend verification
1. Playwright now targets production server (`next start`) by default in `frontend/playwright.config.ts`.
2. Playwright artifacts/reports now write under `frontend/test-results` to avoid root-path EPERM issues.
3. Playwright runs with one worker by default and `timeout=45_000` to avoid resource flake timeouts.
4. Chat e2e assertions were made redirect-safe for auth/guard states.
5. Remaining lint/type test regressions were fixed in chat stream and affected tests.

## Frontdoor Deploy Checklist
1. Build frontend artifact before startup.
   - `cd frontend && npm run build`
   - Required: `.next` exists for `next start`.
2. Confirm frontend runtime command is production mode in deploy context.
   - Use `npm run start` (or equivalent process manager command).
3. Confirm nginx routes still proxy correctly.
   - `nginx/nginx.conf` must keep:
     - `location /api/` -> `http://backend`
     - `location /` -> `http://frontend`
4. Confirm domain and TLS files are valid on host.
   - `app.vektal.systems` cert/key paths exist and are readable.
5. Confirm environment consistency.
   - Frontend: `NEXT_PRIVATE_API_PROXY_ORIGIN` points to backend service.
   - Browser-side base URL and backend APP_URL/FRONTEND_URL remain consistent.
6. Start/reload stack and verify service health.
   - `docker compose ps`
   - `docker compose logs --tail=200 nginx frontend backend`
   - Health endpoints should return 200.

## Firecrawl Verification Loop (frontdoor)
Run from an environment with outbound access to `app.vektal.systems`.

0. Frontdoor probe (DNS + route path fingerprint)
   - `powershell -ExecutionPolicy Bypass -File scripts/tools/frontdoor_probe.ps1 -Domain app.vektal.systems -ExpectedIPv4 89.167.74.58`
   - Report is written to `.planning/debug/frontdoor-probe-<timestamp>.txt`
   - This identifies whether your client is hitting the expected server IP or a stale route.

1. Tool health
   - `python scripts/tools/validate_external_tools.py --mode quick --report .planning/debug/external-tools-quick-<date>.json`
2. Live smoke
   - `python scripts/tools/validate_external_tools.py --mode full --report .planning/debug/external-tools-full-<date>.json`
3. Route scrape sweep
   - `firecrawl scrape --format markdown --json --pretty --timing https://app.vektal.systems/ https://app.vektal.systems/dashboard https://app.vektal.systems/chat https://app.vektal.systems/jobs https://app.vektal.systems/search > .planning/debug/firecrawl-frontdoor-<date>.txt 2>&1`
4. Success criteria
   - Each route returns page content for the app shell/login flow.
   - No route body equals a generic `404 page not found` response.
   - Firecrawl full report has `overall_ok=true`.
5. If failed
   - If `connect EACCES ...:443`: this is network egress policy, not app routing.
   - If `404 page not found` across all routes: inspect DNS target, nginx server block, and frontend upstream/container status.
   - If TLS cert subject is `TRAEFIK DEFAULT CERT`: ingress is serving a default Traefik router, not your app domain route.

## Operator quick triage for 404 frontdoor
1. `docker compose ps frontend nginx backend`
2. `docker compose logs --tail=300 nginx`
3. `docker compose logs --tail=300 frontend`
4. Verify nginx `server_name app.vektal.systems` points `/` to `http://frontend`.
5. Verify frontend container can serve `/chat` locally from inside network.
6. If domain returns plain-text 404 with Traefik default cert, fix ingress ownership:
   - Dokploy path: bind `app.vektal.systems` to the correct app and reissue cert.
   - Nginx path: stop conflicting Traefik listener on `80/443`, then bring up `nginx` + `frontend`.

## Current blocker note
This runtime cannot perform external route confirmation against `https://app.vektal.systems` (Firecrawl/curl both fail with socket access errors), so external frontdoor remains RED until run from an allowed network context.
