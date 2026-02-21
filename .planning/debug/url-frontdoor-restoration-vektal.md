---
status: in_progress
trigger: "URL should point directly to frontend; currently inaccessible"
created: 2026-02-18T22:00:00Z
updated: 2026-02-18T22:12:00Z
---

## Current Focus

hypothesis: Frontdoor instability is caused by DNS drift between root/www/app and unresolved external routing to the new host.
test: Validate A/AAAA records and local frontend availability behind nginx, then execute highest-impact cutover corrections.
expecting: All public hostnames resolve consistently to the active host and app login route responds.
next_action: Fix DNS record drift first (`@`, `www`, `app`) and re-check access.

## Evidence

- timestamp: 2026-02-18
  checked: DNS A records
  found: `app.vektal.systems -> 89.167.74.58`, but `vektal.systems` and `www.vektal.systems` still point to `78.46.117.109`.
  implication: Root/www are still on old host; split routing remains.

- timestamp: 2026-02-18
  checked: DNS AAAA records
  found: `vektal.systems` and `www.vektal.systems` still resolve to old IPv6 `2a01:4f8:d0a:52be::2`; `app` AAAA absent (SOA only).
  implication: Root/www can still route to stale infrastructure over IPv6.

- timestamp: 2026-02-18
  checked: local frontend stack health
  found: Docker services are up; nginx on `:80`, frontend on `:3000`, backend healthy.
  implication: Application stack itself is healthy locally; frontdoor issue is routing/cutover.

- timestamp: 2026-02-18
  checked: nginx host routing config
  found: `server_name` expanded to include `app.vektal.systems`, `vektal.systems`, and `www.vektal.systems`; nginx restarted successfully.
  implication: Reverse proxy now explicitly matches production hostnames.

- timestamp: 2026-02-18
  checked: Hetzner Cloud API token validity
  found: Provided token works for `api.hetzner.cloud` and reveals one running server (`89.167.74.58`) with firewall attached.
  implication: Cloud API access is available for server/firewall inspection.

- timestamp: 2026-02-18
  checked: Firewall rules attached to active server
  found: Inbound `22/tcp`, `80/tcp`, `443/tcp`, and `icmp` are present and applied (`firewall-1`).
  implication: Firewall policy itself is not blocking HTTP/HTTPS.

- timestamp: 2026-02-18
  checked: Resolver convergence on hostnames
  found: `app.vektal.systems` resolves to `89.167.74.58` (A only; AAAA absent), while `vektal.systems` and `www.vektal.systems` still resolve to old `A=78.46.117.109` and `AAAA=2a01:4f8:d0a:52be::2`.
  implication: Root/www are still cut over to stale host; landing-page domain remains misrouted.

## Resolution Target

root_cause: DNS records are not yet fully converged to the active server for all hostnames.
fix: Set `@`, `www`, and `app` A records to `89.167.74.58`; remove stale AAAA for `@` and `www` until IPv6 is intentionally configured.
verification: Pending.
files_changed:
  - .planning/debug/url-frontdoor-restoration-vektal.md
