# Phase 7: Frontend Framework Setup (Next.js) - Research

**Researched:** 2026-02-11
**Domain:** Next.js App Router frontend foundation for async job orchestration
**Confidence:** HIGH

<research_summary>
## Summary

This research focused on the Phase 7 foundation needed to move from a placeholder frontend to a production-grade App Router architecture that matches already-locked UX contracts: ack-first writes, async backend jobs as source of truth, global recovery, deterministic route guards, and strict state boundaries.

Repository evidence shows the backend is already capable of the required job orchestration model: `POST /api/v1/jobs` returns `202 Accepted` with `job_id` and `stream_url` (`src/api/v1/jobs/routes.py`), plus SSE and polling status fallback endpoints exist (`src/api/jobs/events.py`). Versioned API routes are live and legacy routes are intentionally preserved during migration (`src/api/__init__.py`). Frontend currently remains minimal and low-risk to migrate (`frontend/package.json`, `frontend/pages/index.js`).

The standard approach for this setup in 2026 is App Router + React Query + small global UI store, with routing/auth logic centralized and query keys scoped per tenant/store. The strongest recommendation is direct migration to modern App Router baseline now, with module federation kept in contract-only preparation mode for Phase 7.

**Primary recommendation:** Move straight to Next.js 16 App Router baseline with React Query v5 + Zustand v5, enforce scope-aware query keys and deterministic guard waterfall, and keep runtime MF deferred.
</research_summary>

<standard_stack>
## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js | 16.1.x | Frontend app framework + App Router | Official current baseline; first-class routing/data/error conventions; codemod-supported upgrades |
| React / React DOM | 19.x | UI runtime | Required modern baseline for latest Next.js guidance |
| TypeScript | >= 5.1 | Type safety and contracts | Next.js 16 minimum requirement; needed for guard/query/error contract reliability |
| @tanstack/react-query | 5.x | Server-state cache, mutations, retries | Canonical async server-state layer with robust invalidation and rollback patterns |
| Zustand | 5.x | Global UI state only | Minimal store with clean persist middleware for UI preferences/drafts |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| ESLint + typescript-eslint | current | Policy enforcement for strictness and escape-hatch controls | Required for `@ts-ignore` ban and `any` restrictions in feature modules |
| Zod (optional) | 3.x/4.x | Runtime parsing at API boundary | Use when backend payload drift needs client-side hardening |
| @tanstack/query-devtools (dev only) | 5.x | Query debugging | Use during rollout/debug to validate invalidation and cache scope |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| React Query | SWR | SWR is lighter, but weaker mutation orchestration for ack-first + rollback-heavy flows |
| Zustand global UI store | Redux Toolkit | RTK adds ceremony; useful only if cross-team scale requires stricter reducer workflows |
| App Router now | Keep Pages Router | Lower short-term change, but conflicts with Phase 7 route/guard architecture and increases migration debt |
| Contract-only MF prep | Runtime MF now | Runtime MF adds async remote/runtime version complexity too early for current phase goals |

**Installation:**
```bash
npm install next@latest react@latest react-dom@latest typescript@latest @types/react@latest @types/react-dom@latest @tanstack/react-query zustand
```
</standard_stack>

<architecture_patterns>
## Architecture Patterns

### Recommended Project Structure
```text
frontend/src/
|-- app/                    # App Router routes, layouts, route handlers
|-- shell/                  # Guarded layout, nav frame, global banner/toasts
|-- features/               # Domain modules (jobs, search, chat, settings)
|-- shared/                 # Design primitives, safe helpers, common contracts
|-- lib/
|   |-- api/                # API client + RFC7807/9457 normalization boundary
|   |-- query/              # Query client + scoped key factories
|   `-- auth/               # Route guard decision utilities
`-- state/                  # Zustand UI-only stores (prefs, draft metadata)
```

### Pattern 1: Deterministic Guard Waterfall (A/V/S)
**What:** Centralize redirect decision order and exemptions in one pure guard function.
**When to use:** Every protected route and server-side routing decision.
**Enforcement note:** Treat guard logic as middleware-agnostic. Enforce through App Router server redirects and use `proxy` where pre-render interception is needed; do not rely on middleware-only policy language.
**Example:**
```ts
// Guard order: A -> V -> S
export function getRedirectForRoute(route: string, state: { A: boolean; V: boolean; S: boolean }) {
  if (route.startsWith('/auth/')) return null
  if (!state.A) return '/auth/login'
  if (!state.V) return '/auth/verify'
  if (requiresStore(route) && !state.S && route !== '/onboarding') return '/onboarding'
  return null
}
```

### Pattern 2: Job Observer Transport Ladder (SSE -> Poll)
**What:** Use SSE as primary, inactivity probe as trigger to switch to polling fallback.
**When to use:** `/jobs/[id]` detail and global tracker rehydration.
**Default/tunable UX timings:** starting buffer ~2-3s, transient success ~10-15s, transient cancelled ~5s, burst collapse threshold 3+ terminal events in ~10s.
**Example:**
```ts
// UI tracks transport health; backend remains source of truth.
if (sseSilentForMs > inactivityThresholdMs) {
  closeEventSource()
  startPolling(jobId)
}
```

### Pattern 3: Scoped Query-Key Factory
**What:** Enforce key shape `[resource, scope, ...rest]` with scope in segment 2.
**When to use:** All query + mutation invalidation paths.
**Example:**
```ts
type Scope = { storeId: string; userId?: string }
export const jobKeys = {
  root: (scope: Scope) => ['jobs', scope] as const,
  list: (scope: Scope, params: { status?: string; page?: number }) => ['jobs', scope, 'list', params] as const,
  detail: (scope: Scope, id: string) => ['jobs', scope, 'detail', { id }] as const,
}
```

### Anti-Patterns to Avoid
- **Dual source of truth for jobs:** Do not treat global registry as canonical state. Re-derive from backend on rehydrate.
- **Ad-hoc per-page guards:** Route-level custom logic without waterfall precedence causes redirect loops.
- **Unscoped query keys:** Missing `storeId/userId` in key segment 2 risks cache pollution across tenants.
- **Runtime MF in Phase 7:** Adds operational complexity with no immediate business gain.
- **Unapproved seam growth (`core/`):** Phase 7 seam contract is `shell/`, `features/`, `shared/` only unless explicitly locked in a later phase.
</architecture_patterns>

<decision_matrix>
## Decision Matrix (Holistic)

Compare viable implementation approaches before locking the recommendation:

| Option | Strengths | Weaknesses | Operational Risk | Chosen? Why/Why Not |
|--------|-----------|------------|------------------|---------------------|
| **A. Direct to Next 16 + App Router now** | Aligns with locked architecture; lowest long-term debt; modern routing conventions | Requires React/TS baseline uplift in same move | Medium: upgrade coordination needed | **Chosen**. Frontend is currently minimal, so migration surface is small and risk is controlled. |
| **B. App Router on current Next 14 first, then upgrade** | Smaller immediate dependency jump | Two-step migration; duplicate effort on config and edge cases | Medium-High: more churn and regression windows | Not chosen. Current frontend footprint is too small to justify staged framework debt. |
| **C. Keep Pages Router for Phase 7** | Minimal immediate technical change | Conflicts with locked App Router decision; more guard/layout debt | High: architecture divergence from agreed contracts | Not chosen. Violates locked Phase 7 posture. |
| **D. Runtime Module Federation now** | Early microfrontend runtime | High complexity (async remotes, shared deps, deploy topology) | High: unstable integration path with App Router | Not chosen. Keep contract-only MF preparedness per phase scope. |

**Decision rule:** Prefer approaches that minimize migration risk, maximize observability, and allow incremental rollout with rollback.
</decision_matrix>

<sequential_thinking_trace>
## Sequential Thinking Trace

1. **Problem framing:**
   Phase 7 needs a resilient frontend foundation for async backend-driven workflows, not a cosmetic UI rewrite.

2. **Evidence baseline:**
   - Frontend is still placeholder (`frontend/pages/index.js`) and currently on Next 14/React 18 (`frontend/package.json`).
   - Backend already provides async job primitives and status transports (`src/api/v1/jobs/routes.py`, `src/api/jobs/events.py`).
   - Versioned API migration path exists with legacy compatibility (`src/api/__init__.py`).

3. **Branches explored:**
   - Upgrade path: Next 16 now vs staged upgrade later.
   - State model: React Query-centric vs mixed ad-hoc fetch state.
   - MF strategy: contract-only preparedness vs runtime federation now.

4. **Stress tests:**
   - Ack-first UX under request failures/timeouts.
   - SSE silence and network degradation fallback behavior.
   - Redirect loop and `returnTo` abuse risk.
   - Rehydration correctness after refresh/reopen.

5. **Chosen approach:**
   Direct App Router baseline on modern Next, with strict query key scoping and API boundary normalization, while deferring runtime MF.

6. **Confidence:**
   - Framework baseline: **HIGH** (official Next 16 docs + minimal current frontend surface)
   - Data/state patterns: **HIGH** (TanStack and Zustand primary docs)
   - MF deferral decision: **HIGH** (Next MF support limitations documented)

7. **Unknowns:**
   - Deployment runtime readiness for Node.js >= 20.9 and React 19 toolchain.
   - Exact server-side bootstrap payload shape for active jobs during rehydrate.
</sequential_thinking_trace>

<implementation_strategy>
## Incremental Implementation Strategy

### Phase Ordering
1. **Foundation (non-breaking):**
   - Establish App Router shell structure and typed API/query boundaries.
   - Add guard decision utilities and query key factories.
2. **Integration (compatible):**
   - Implement onboarding/jobs/search/settings routes using canonical route ownership.
   - Wire SSE observer + inactivity fallback + global tracker.
3. **Cutover (controlled):**
   - Switch default post-activation landing to `/dashboard` jobs-health hub.
   - Enforce ack-first write surfaces and terminal-state handling contracts.
4. **Hardening:**
   - Tighten lint/TS gates, telemetry tuning, transport and retry edge cases.

### Compatibility Plan
- Preserve existing backend endpoints and use `/api/v1/*` as preferred contract.
- Keep legacy backend routes untouched during frontend cutover (`/auth`, `/billing`, `/oauth`) until deprecation plan.
- Keep runtime MF out of phase scope; use static feature manifests only.

### Rollback Plan
- **Triggers:** elevated 5xx on core pages, auth redirect loops, job tracking desync, unrecoverable SSE/poll failures.
- **Fast rollback:** revert frontend route switch/default landing and disable new feature flags while keeping backend contracts unchanged.
</implementation_strategy>

<dont_hand_roll>
## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Server-state caching/invalidation | Custom fetch cache + manual retry logic | TanStack Query v5 | Handles stale data, retries, invalidation, and mutation lifecycle safely |
| Global UI persistence | Custom localStorage wrapper in many components | Zustand `persist` middleware | Centralizes persistence, supports partialize/version/migration |
| Redirect orchestration | Scattered per-page redirect code | Central guard decision function + Next redirect/proxy | Prevents inconsistent precedence and loops |
| Error payload handling | Per-component ad-hoc error parsing | Single API-client normalization boundary | Keeps RFC7807/9457 mapping deterministic across UI surfaces |
| Runtime microfrontend loading (now) | Custom remote bootstrap in Phase 7 | Contract-only seams first | Runtime federation adds async/version/deploy complexity too early |

**Key insight:** Phase 7 reliability comes from strict boundaries and mature primitives, not custom infrastructure.
</dont_hand_roll>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: Cache Scope Leakage
**What goes wrong:** Data appears from another store/user context.
**Why it happens:** Query keys omit scope or scope is inconsistent.
**How to avoid:** Enforce `[resource, scope, ...rest]` key shape and key-factory-only usage.
**Warning signs:** Invalidations unexpectedly refresh unrelated pages.

### Pitfall 2: Redirect Loop Regressions
**What goes wrong:** Users bounce between `/auth/*`, `/onboarding`, and protected routes.
**Why it happens:** Guard overrides ignore precedence or unsafe `returnTo` behavior.
**How to avoid:** One deterministic guard function + same-origin `returnTo` sanitizer + loop protection.
**Warning signs:** Repeated navigation events and growing browser history with no rendered page.

### Pitfall 3: Silent Job Transport Failure
**What goes wrong:** UI freezes at stale progress while backend job continues.
**Why it happens:** SSE disconnect/silence not detected or fallback not started.
**How to avoid:** Inactivity probe timer with automatic polling fallback and terminal-state reconciliation.
**Warning signs:** No event updates while status endpoint reports progress changes.

### Pitfall 4: UI Source-of-Truth Drift
**What goes wrong:** Global tracker shows terminal states inconsistent with backend.
**Why it happens:** Local registry treated as authoritative after refresh.
**How to avoid:** Rehydrate from backend on mount/focus/reconnect and treat registry as UI projection only.
**Warning signs:** Terminal statuses differ between detail page and global list.
</common_pitfalls>

<code_examples>
## Code Examples

Verified patterns from official sources and adapted for Phase 7 contracts:

### App Router Redirect After Guard Decision
```ts
// Source: Next.js redirect API + redirecting guide
import { redirect } from 'next/navigation'

export async function enforceAccess(route: string, state: { A: boolean; V: boolean; S: boolean }) {
  const next = getRedirectForRoute(route, state)
  if (next) redirect(next)
}
```

### TanStack Mutation Rollback Pattern
```ts
// Source: TanStack Query optimistic updates guide (v5)
const mutation = useMutation({
  mutationFn: updateJob,
  onMutate: async (input) => {
    await queryClient.cancelQueries({ queryKey: jobKeys.detail(scope, input.id) })
    const prev = queryClient.getQueryData(jobKeys.detail(scope, input.id))
    queryClient.setQueryData(jobKeys.detail(scope, input.id), (old) => ({ ...old, ...input }))
    return { prev }
  },
  onError: (_err, input, ctx) => {
    if (ctx?.prev) queryClient.setQueryData(jobKeys.detail(scope, input.id), ctx.prev)
  },
  onSettled: (_data, _error, input) => {
    queryClient.invalidateQueries({ queryKey: jobKeys.detail(scope, input.id) })
  },
})
```

### Zustand Persist for UI Preferences
```ts
// Source: Zustand persist docs + TS create<T>() pattern
import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

type UiPrefs = {
  sidebarCollapsed: boolean
  setSidebarCollapsed: (v: boolean) => void
}

export const useUiPrefs = create<UiPrefs>()(
  persist(
    (set) => ({
      sidebarCollapsed: false,
      setSidebarCollapsed: (v) => set({ sidebarCollapsed: v }),
    }),
    {
      name: 'ui-prefs-v1',
      storage: createJSONStorage(() => localStorage),
      partialize: (s) => ({ sidebarCollapsed: s.sidebarCollapsed }),
      version: 1,
    },
  ),
)
```
</code_examples>

<operational_readiness>
## Operational Readiness

### Testing Strategy
- **Unit:** guard decision function, `returnTo` sanitizer, query key factories, error normalization mapper.
- **Integration/contract:** auth onboarding redirect behavior, jobs create/cancel/status flows, SSE fallback transition.
- **E2E/human checks:** onboarding completion via both ingest paths, refresh mid-job, ghost terminal alerts, mobile status-first behavior.

### Observability and Diagnostics
- **Metrics to add:** job-start ack latency, SSE disconnect rate, fallback-to-poll rate, terminal failure rate by endpoint class.
- **Logs/events to add:** `job_id`, `user_id`, `store_id`, route id, guard redirect reason, correlation id (`problem.instance` or equivalent).
- **Alert thresholds:** sustained increase in fallback-to-poll, repeated auth redirect loops, elevated 5xx on jobs/billing/oauth writes.

### Production Guardrails
- Feature-flag cutover points for new shell routing and global tracker behaviors.
- Conservative timeout defaults on write actions; disable duplicate submits while awaiting ack.
- Runbook expectations: auth loop triage, SSE degradation triage, cache scope leakage triage.
</operational_readiness>

<sota_updates>
## State of the Art (2024-2026)

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Next 14/15 mixed router migration strategies | Next 16 App Router-first baseline | 2025-2026 | Cleaner long-term architecture; requires modern Node/TS/React baseline |
| Optional Turbopack flags | Turbopack default in dev/build | Next 16 | Build behavior changes and webpack customization considerations |
| `middleware` convention | `proxy` convention in docs/codemods | Next 16 codemod flow | Guard/redirect placement should align with updated conventions |
| RFC 7807 as current reference | RFC 9457 obsoletes RFC 7807 | July 2023 | Keep compatibility naming but align normalization with updated standard |
| Runtime MF as obvious scaling path in Next | Next MF plugin support constraints and deprecation signals | 2025+ | Favor contract-first MF preparedness before runtime federation |

**New tools/patterns to consider:**
- Next codemod upgrade workflow for major-version uplift.
- Query-level persistence/broadcast options only after baseline reliability is stable.

**Deprecated/outdated:**
- Treating Pages Router + ad-hoc fetch state as long-term architecture for new platform work.
- Runtime Next MF expectation in App Router contexts for this phase.
</sota_updates>

<open_questions>
## Open Questions

1. **Deployment baseline readiness for Next 16 toolchain**
   - What we know: Next 16 upgrade guidance requires Node.js >= 20.9 and TS >= 5.1.
   - What's unclear: Production/staging runtime guarantees for Node and CI images.
   - Recommendation: Validate environment parity before implementation branch cutover.

2. **Active jobs bootstrap shape for global tracker**
   - What we know: Job status endpoints exist and can be queried by job id.
   - What's unclear: Whether mount-time bootstrap returns active jobs list without extra query choreography.
   - Recommendation: During planning, define one deterministic startup fetch strategy and document fallback.

3. **Frontend runtime parser strictness level**
   - What we know: Backend currently emits mixed legacy and v1 response styles.
   - What's unclear: Whether strict runtime schema parsing is needed on day one for all endpoints.
   - Recommendation: Start strict on critical write/read endpoints (`jobs`, `billing`, `oauth`), permissive on low-risk reads.
</open_questions>

<sources>
## Sources

### Primary (HIGH confidence)
- Local repository evidence:
  - `frontend/package.json` (current Next/React baseline)
  - `frontend/pages/index.js` (placeholder frontend state)
  - `src/api/__init__.py` (v1 + legacy route registration and migration posture)
  - `src/api/v1/jobs/routes.py` (202-accepted job creation, cancel semantics)
  - `src/api/jobs/events.py` (SSE stream + polling status fallback)
  - `src/auth/login.py`, `src/auth/oauth.py`, `src/billing/checkout.py` (auth/oauth/billing behavior contracts)
- Next.js official docs:
  - https://nextjs.org/docs/app/guides/upgrading/version-16
  - https://nextjs.org/docs/app/api-reference/file-conventions/route-groups
  - https://nextjs.org/docs/app/building-your-application/routing/redirecting
  - https://nextjs.org/docs/app/api-reference/functions/redirect
- TanStack Query docs:
  - https://tanstack.com/query/v5/docs/framework/react/guides/optimistic-updates
- Zustand docs:
  - https://zustand.docs.pmnd.rs/middlewares/persist
  - https://zustand.docs.pmnd.rs/integrations/persisting-store-data
  - https://zustand.docs.pmnd.rs/guides/advanced-typescript
- Standards reference:
  - https://datatracker.ietf.org/doc/html/rfc9457

### Secondary (MEDIUM confidence)
- Context7 curated docs snapshots:
  - `/vercel/next.js/v16.1.5` (redirect/proxy/route-group/upgrade behaviors)
  - `/tanstack/query/v5.71.10` (mutation optimistic update and rollback patterns)
  - `/pmndrs/zustand/v5.0.8` (persist + TS patterns)

### Tertiary (LOW confidence - needs validation)
- Module Federation Next.js status pages:
  - https://module-federation.io/guide/framework/nextjs.html
  - https://webpack.js.org/concepts/module-federation/
  (Used for runtime MF risk framing; validate against project-specific federation goals during planning.)
</sources>

<metadata>
## Metadata

**Research scope:**
- Core technology: Next.js App Router foundation
- Ecosystem: React Query v5, Zustand v5, TypeScript strict baseline, RFC problem-details handling
- Patterns: guard waterfall, scope-aware query keys, async job transport fallback, shell/feature boundary contracts
- Pitfalls: cache leakage, redirect loops, transport silence, source-of-truth drift

**Confidence breakdown:**
- Standard stack: **HIGH** - official docs and current repo baseline are aligned
- Architecture: **HIGH** - directly grounded in locked context + backend capabilities
- Pitfalls: **HIGH** - failure modes validated by existing endpoint behavior and known framework constraints
- Code examples: **HIGH** - based on official patterns adapted to Phase 7 contract rules

**Research date:** 2026-02-11
**Valid until:** 2026-02-18 (7 days for framework/version-sensitive guidance)
</metadata>

---

*Phase: 07-frontend-framework-setup*
*Research completed: 2026-02-11*
*Ready for planning: yes*
