---
name: frontend-deploy-debugger
description: Diagnose and fix frontend deployment failures across localhost, Docker, and Linux servers, then prepare clean cutover to public URL. Use when deployment is failing, when runtime ports/proxy are broken, or immediately after `frontend-design` implementation to run a quick regression check before validation. Use Neo4j/Graphiti (Graffiti) graph context to trace impacted files and blast radius before edits. Make sure to use this skill on each loop iteration between `frontend-design` and `deployment-validator`.
---

# Frontend Deploy Debugger

Turn deployment uncertainty into a deterministic, evidence-based flow.

---

## Pipeline position

- Previous skill: `frontend-design`
- Current skill: `frontend-deploy-debugger`
- Next skill: `deployment-validator`

---

## Required input handoff

Accept these fields if provided by `frontend-design`:

- `local_target_url`
- `public_target_url`
- `run_commands`
- framework/runtime hints
- `changed_files`
- `iteration`

If missing, infer from repo and mark unknown values as `N/A`.

---

## What this skill does

1. Build a deployment fact sheet from code and runtime.
2. Classify the primary failing layer (`app`, `container`, `network`, `proxy/domain`).
3. Use Neo4j/Graphiti graph context to identify connected files and blast radius.
4. Apply minimal fixes one layer at a time.
5. Run a quick regression check to ensure prior passing behavior still passes.
6. Verify each gate with commands and objective results.
7. Produce clean handoff for validation.

---

## Operating rules

- Evidence before edits.
- One failing layer at a time.
- No multi-layer blind changes.
- Keep runtime ports canonical and documented.
- Treat localhost success and public URL success as separate gates.
- Use graph-assisted impact analysis before editing files whenever graph data is available.
- Keep blast radius explicit and as small as possible.

---

## Required output format

```markdown
# Frontend Deployment Debug Report

## 1) Deployment Fact Sheet
- Frontend stack:
- Package manager:
- App dev/prod ports:
- Docker services and mapped ports:
- Reverse proxy + domain config:
- Runtime environment:

## 2) Failure Classification
- Primary failing layer: app | container | network | proxy/domain
- Symptoms:
- Root cause hypothesis:
- Confidence: high | medium | low

## 3) Fix Plan (ordered, minimal)
1. ...
2. ...
3. ...

## 4) Dependency Impact and Blast Radius
- Entry files under debug:
- Connected files from graph:
- High-risk downstream components:
- Blast radius: low | medium | high
- Context strategy: quick-narrow | balanced | deep-narrow

## 5) Verification Evidence
- Local checks:
- Container/process checks:
- HTTP checks (local/public):
- Remaining risks:

## 6) Handoff
- Final run commands:
- Required env vars/secrets (names only):
- Rollback steps:
```

---

## Workflow

### Step 1: Build fact sheet

Collect from:

- `package.json` scripts and framework deps
- Docker files and compose config
- proxy/domain config (Nginx/Caddy/Traefik/etc.)
- `.env*` keys related to host, port, base URL, API URL

Optional deep reference: [`references/troubleshooting-matrix.md`](references/troubleshooting-matrix.md)

### Step 2: Classify failure

Choose one primary layer:

- `app`
- `container`
- `network`
- `proxy/domain`

Do not fix until layer classification is explicit.

### Step 3: Graph-assisted impact analysis (Neo4j/Graphiti)

Before edits, trace file dependencies and runtime relationships for files under debug.

- Identify directly connected files.
- Identify likely downstream UI routes/components/services.
- Label blast radius (`low`, `medium`, `high`).

If graph tooling is unavailable, fall back to local import/reference tracing (`rg`) and mark confidence as lower.

### Step 4: Context/time strategy

Select one strategy per iteration:

- `quick-narrow`: low time, smallest context slice, fastest verification loop
- `balanced`: moderate time/context for normal remediation
- `deep-narrow`: more time on a very small context slice for hard failures

When stuck, reduce context scope first, then increase analysis depth only for the narrowed slice.

### Step 5: Apply minimal fixes

- app: command/build/tooling mismatch
- container: image/dependency/runtime binding issues
- network: port collisions/mapping/firewall
- proxy/domain: DNS/upstream/TLS/host routing

### Step 6: Verify deployment gates

Mandatory:

1. local URL responds as expected
2. container/process health is valid
3. public URL responds as expected

If a gate fails, reclassify and iterate.

### Step 7: Quick regression check

When `changed_files` are provided by `frontend-design`, verify:

- the changed areas render and function
- core app shell and routes still load
- no obvious port/proxy regressions were introduced

Keep this check fast and evidence-based.

---

## Mandatory pipeline handoff

After debugging is complete, immediately continue with `deployment-validator`.

Include this payload:

```json
{
  "next_skill": "deployment-validator",
  "handoff_reason": "Deployment debug complete; objective validation required.",
  "local_url": "http://localhost:<port-or-N/A>",
  "public_url": "https://<domain-or-N/A>",
  "expected_service": "<service-name-or-N/A>",
  "debug_summary": "Concise summary of what changed and what still risks failure.",
  "impacted_files": ["path/one", "path/two"],
  "blast_radius": "low|medium|high",
  "context_strategy": "quick-narrow|balanced|deep-narrow",
  "iteration": "<n>"
}
```
