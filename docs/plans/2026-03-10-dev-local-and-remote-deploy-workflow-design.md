# Dev + Deploy Workflow Design (Local Fast Iteration + Dokploy Validation)

**Date:** 2026-03-10
**Owner:** Codex

## Goal
Enable instant frontend changes during development while keeping the Hetzner/Dokploy deployment stable and reliable. Use local dev for speed, and deploy to the server only when ready for validation.

## Requirements
- Instant feedback loop while editing frontend.
- Stable server environment without dev-server 504s.
- Simple, repeatable deploy path to Dokploy.
- No secrets committed to git.

## Proposed Workflow

### Local Development (Primary)
- Run `npm run dev` locally for instant HMR updates.
- Use local API base URL (or proxy) to hit backend when testing.
- Iterate rapidly without touching the server.

### Server Validation (Secondary)
- When ready to validate on Hetzner:
  1. Commit and push changes to GitHub.
  2. Trigger Dokploy redeploy (manual or on-push).
  3. Validate via `http://<server-ip>:8080` (nginx) or `http://<server-ip>:3001` (frontend).

## Deployment Strategy
- Keep Dokploy stack stable and production-lean.
- Avoid running `next dev` in production for long sessions.
- Use Dockerfile/compose for server builds only when validating.

## Constraints / Guardrails
- Do not commit secrets (use Dokploy Environment for secrets).
- Maintain consistent API base URL settings between local and server.
- DNS cutover to `vektal.systems` happens later.

## Success Criteria
- Local edits visible instantly.
- Server deployment stable and reachable on every redeploy.
- No recurring nginx 504s during validation.

## Open Questions
- None.
