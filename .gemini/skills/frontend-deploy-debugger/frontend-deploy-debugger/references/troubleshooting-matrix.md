# Troubleshooting Matrix

## Port conflicts

Symptoms:
- App starts then exits with EADDRINUSE
- Container runs but host port is unavailable

Checks:
- Running listeners on target port
- Duplicate mappings in `docker-compose*.yml`
- Reverse proxy and app both trying to bind `80/443`

Fix direction:
- Pick one canonical app port (for example `3000`)
- Map proxy public `80/443` to internal app port
- Remove duplicate port mappings

## Headless and browser issues

Symptoms:
- App works in build but automation/smoke tests fail
- Browser-based checks fail in container

Checks:
- Headless flags and browser dependencies
- CI/container runtime has required libraries

Fix direction:
- Keep browser tooling optional for deployment gates
- Use HTTP-level checks as primary deployment gate

## Docker missing packages

Symptoms:
- Build fails with missing module
- Runtime fails after successful build

Checks:
- Lockfile is present and copied before install
- `npm ci`/equivalent runs in image build stage
- Production image contains runtime deps

Fix direction:
- Align Dockerfile install flow with lockfile/package manager
- Use multi-stage build with explicit artifact copy

## Bundler mode confusion (Webpack/Turbopack)

Symptoms:
- Dev command works only sometimes
- Different behavior between local and container

Checks:
- `package.json` scripts for conflicting startup modes
- Framework version compatibility for chosen mode

Fix direction:
- Choose one mode and pin command path explicitly
- Avoid mixed fallback scripts during debugging

## Domain/proxy deployment failures

Symptoms:
- `localhost` works but domain fails
- 502/504 from reverse proxy

Checks:
- DNS A/AAAA target correctness
- Upstream host/port in proxy config
- Firewall/security group allows `80/443`
- App listens on `0.0.0.0`, not loopback-only

Fix direction:
- Fix upstream mapping and listener bind
- Validate with `curl` from server and from external client

