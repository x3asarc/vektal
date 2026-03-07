---
status: monitoring
trigger: "app.vektal.systems still returns plain '404 page not found'"
created: 2026-03-03T20:20:00Z
updated: 2026-03-04T18:12:00Z
---

## Current Focus

hypothesis: DNS now points to the correct IPv4 host, but ingress on that host is not routing `app.vektal.systems` to the Shopify stack; default Traefik route is serving 404.
test: Probe live domain and direct host IP over 80/443, then inspect live certificate identity.
expecting: If Traefik default ingress is active, cert subject should be Traefik default and response should be plain-text 404.
next_action: Rebind ingress route for `app.vektal.systems` (Dokploy/Traefik) or stop conflicting ingress and restore nginx frontdoor ownership.

## Evidence

- timestamp: 2026-03-03
  checked: live HTTPS probes
  found: `https://app.vektal.systems/`, `/health`, and `/chat` all return `HTTP/1.1 404 Not Found` with body `404 page not found`.
  implication: Frontdoor is reachable but routing to app stack is not configured.

- timestamp: 2026-03-03
  checked: route target IP
  found: `app.vektal.systems` resolves to `89.167.74.58` and curl connects to that IPv4.
  implication: This is not stale DNS to the old Apache host.

- timestamp: 2026-03-03
  checked: response fingerprint
  found: headers include `Alt-Svc: h3=":443"`, `Content-Type: text/plain; charset=utf-8`, `X-Content-Type-Options: nosniff`.
  implication: Response profile matches reverse-proxy default handler, not the expected nginx app server block.

- timestamp: 2026-03-03
  checked: TLS certificate served on `app.vektal.systems:443`
  found: certificate subject and issuer are both `CN=TRAEFIK DEFAULT CERT`, SAN `*.traefik.default`.
  implication: Live traffic is hitting Traefik default certificate/router, not app-specific TLS config.

- timestamp: 2026-03-03
  checked: old host comparison
  found: old host `78.46.117.109` responds with `Server: Apache`; current domain response does not.
  implication: Current failure mode differs from previous stale-IPv6/old-host incident.

- timestamp: 2026-03-04
  checked: production runtime state via SSH (`89.167.74.58`)
  found: `dokploy-traefik` owned ports `80/443`; `/opt/vektal` compose services were not running; Traefik dynamic config contained only `dokploy.docker.localhost` route.
  implication: The app had no active frontdoor router/service binding.

- timestamp: 2026-03-04
  checked: host-side remediation
  found: started `/opt/vektal` stack with frontend on `3001` (`NEXTJS_PORT=3001`) and backend on `5000`; added `/etc/dokploy/traefik/dynamic/vektal-app.yml` routers/services for `app.vektal.systems`.
  implication: Traefik now routes domain traffic to live app services without replacing ingress ownership.

- timestamp: 2026-03-04
  checked: post-fix external probes
  found: `https://app.vektal.systems/health -> 200` (`Server: gunicorn`), `https://app.vektal.systems/ -> 307` (`X-Powered-By: Next.js`), `https://app.vektal.systems/chat -> 200`, `https://app.vektal.systems/api/v1/chat/sessions -> 401` (expected unauthenticated API).
  implication: default Traefik 404 is resolved; frontend and backend routing are both active.

## Resolution Target

root_cause: `app.vektal.systems` currently lands on Traefik default ingress with no matching route/service binding.
fix:
  1. Kept Traefik as ingress owner for `80/443`.
  2. Started app services under `/opt/vektal` (`frontend:3001`, `backend:5000`, plus worker/db/redis stack).
  3. Added explicit Traefik dynamic routers/services for `app.vektal.systems` and backend path families.
verification: `GREEN` for frontdoor restoration; `MONITORING` for stability under real user traffic.
files_changed:
  - .planning/debug/frontdoor-traefik-default-404.md
