---
status: monitoring
trigger: "its been reinstalled already. make it work now."
created: 2026-02-18T13:45:00Z
updated: 2026-02-18T21:05:00Z
---

## Current Focus

hypothesis: Infrastructure is healthy on the new host, but stale IPv6 cache paths still route some clients to the old host (`2a01:4f8:d0a:52be::2`), causing TLS/CN mismatch and wrong backend responses.
test: Compare Playwright default routing vs forced-IP routing and capture verbose TLS endpoint details.
expecting: Default route can still fail if IPv6 cache persists; forced-IP route to `89.167.74.58` should pass.
next_action: Wait for stale Google DNS AAAA cache expiry, then re-run public Playwright without host mapping.

## Symptoms

expected: `app.vektal.systems` should load the deployed app and Shopify install should work with the new app URL.
actual: App remains unreachable after reinstall; callbacks and app access fail.
errors: External health checks return connection failure (`000`).
reproduction: Reinstall app in Shopify using `https://app.vektal.systems` and open app URL.
started: During domain cutover from tunnel/old host to new Hetzner server.

## Eliminated

- hypothesis: Backend stack is down on the new server.
  evidence: Docker Compose services are running; backend shows healthy state in `docker compose ps --format json`.
  timestamp: 2026-02-18

- hypothesis: Assistant queue topology missing prevents app startup.
  evidence: `celery_worker` includes `assistant.t1/t2/t3` queues and service starts; app-level reachability issue persists independently.
  timestamp: 2026-02-18

## Evidence

- timestamp: 2026-02-18
  checked: DNS A record for `app.vektal.systems` after user update
  found: Resolves to `89.167.74.58` (new host), TTL `60`.
  implication: IPv4 cutover is correct.

- timestamp: 2026-02-18
  checked: DNS AAAA record for `app.vektal.systems` after user update
  found: Still resolves to `2a01:4f8:d0a:52be::2` (old host), not new server `2a01:4f9:c014:78ac::1`.
  implication: IPv6 traffic continues to route to the wrong machine.

- timestamp: 2026-02-18
  checked: New Hetzner server deployment state
  found: `/opt/vektal` stack built and running; backend is healthy; nginx published on `0.0.0.0:80`.
  implication: Runtime on new server is up; cutover issue is upstream routing.

- timestamp: 2026-02-18
  checked: Protocol and IP-family behavior from server
  found: `curl -4 http://app.vektal.systems/health` returns `200`; `curl -6 http://app.vektal.systems/health` returns `404`.
  implication: IPv4 reaches new app, IPv6 hits old endpoint.

- timestamp: 2026-02-18
  checked: HTTPS status
  found: `https://app.vektal.systems/health` returns `000`; nginx only listening on `80`.
  implication: TLS on `443` is not configured yet, blocking Shopify-required HTTPS flow.

- timestamp: 2026-02-18
  checked: DNS propagation
  found: `A app.vektal.systems -> 89.167.74.58` and `AAAA app.vektal.systems -> 2a01:4f9:c014:78ac::1` (TTL `60`).
  implication: Domain now routes to the new server on both IPv4 and IPv6.

- timestamp: 2026-02-18
  checked: TLS certificate on new server IP
  found: `openssl s_client -connect 89.167.74.58:443 -servername app.vektal.systems` shows subject `CN=app.vektal.systems`, issuer `Let's Encrypt`, and HTTPS `/health` returns `200`.
  implication: HTTPS termination is active and valid for Shopify callback requirements.

- timestamp: 2026-02-18
  checked: certificate renewal behavior
  found: `certbot renew --dry-run` succeeded with compose hooks stopping/starting nginx.
  implication: automatic renewal path is working.

- timestamp: 2026-02-18
  checked: Playwright smoke against public hostname (default resolver path)
  found: `3/3` tests failed with `ERR_CERT_COMMON_NAME_INVALID`; runtime indicated certificate alt names `*.your-server.de`/`your-server.de`.
  implication: Some routes still hit stale endpoint/cached path instead of new `app.vektal.systems` certificate.

- timestamp: 2026-02-18
  checked: Resolver state during failed Playwright run
  found: `A app.vektal.systems -> 89.167.74.58` (new), but `AAAA app.vektal.systems -> 2a01:4f8:d0a:52be::2` (old, TTL still in cache window).
  implication: Mixed resolver state explains client inconsistency.

- timestamp: 2026-02-18
  checked: Verbose HTTPS probe on failing path
  found: `curl -vk https://app.vektal.systems/health` connected to IPv6 `2a01:4f8:d0a:52be::2` and returned `Server: Apache` with `404`.
  implication: Requests are still reaching old host over IPv6 in some environments.

- timestamp: 2026-02-18
  checked: DNS after user removed `AAAA`
  found: Local resolver now returns SOA/no AAAA answer; however `8.8.8.8` still returns stale `AAAA -> 2a01:4f8:d0a:52be::2` with remaining TTL.
  implication: Chromium paths using Google DNS can still hit old IPv6 host.

- timestamp: 2026-02-18
  checked: Playwright public run after AAAA removal
  found: `2/3` pass (`/health`, `/`), `/chat` fails with `ERR_CERT_COMMON_NAME_INVALID`.
  implication: Intermittent stale-DNS path remains for some browser lookups.

- timestamp: 2026-02-18
  checked: Playwright `/chat` diagnostic with `ignoreHTTPSErrors=true`
  found: `/chat` resolves to direct `404` at `https://app.vektal.systems/chat` (no app redirect chain), consistent with old-host Apache behavior.
  implication: `/chat` failures are still explained by stale destination routing, not app logic on the new host.

- timestamp: 2026-02-18
  checked: Playwright smoke with forced host mapping to new IPv4 (`89.167.74.58`)
  found: `3/3` tests passed: `/health` `200`, landing page loads, `/chat` resolves/redirects as expected.
  implication: Application and TLS on the new host are functional; remaining issue is DNS cache convergence across resolvers/clients.

- timestamp: 2026-02-18
  checked: Local/internal server health (previous probe)
  found: `http://localhost/health` and `http://localhost:5000/health` return `200`.
  implication: App runtime is functional internally.

## Resolution

root_cause: Initial cutover + TLS gap is fixed, but residual resolver/cache behavior still prefers stale IPv6 destination in some paths.
fix: Completed server-side HTTPS + renewal and validated app with Playwright forced-IP run (`3/3` pass). Public default path is partially improved but still cache-sensitive where stale Google DNS AAAA remains.
verification: `GREEN` for new host infrastructure and forced-IP browser checks; `MONITORING` for full public DNS cache convergence.
files_changed:
  - .planning/debug/vektal-domain-cutover-not-reachable.md
