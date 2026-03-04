# Frontend Architecture Guide

This folder contains the Phase 7 Next.js frontend for the Shopify Multi-Supplier Platform.

## 1) Stack and frameworks

| Layer | Technology | Notes |
|---|---|---|
| Framework | Next.js 16 (`App Router`) | Route groups, server/client components, dev server on port 3000 |
| UI | React 19 | Component-driven UI with route-level pages |
| Language | TypeScript 5 (strict) | `strict: true`, path alias `@/* -> src/*` |
| Data fetching | TanStack React Query | Query client configured in `src/shell/providers.tsx` |
| Local state | Zustand | UI preferences, drafts, and workflow/session state |
| Testing | Vitest + Testing Library + jsdom | Unit/integration/contract tests in `src` and `tests/frontend` |
| Linting | ESLint 9 + TypeScript ESLint + Next plugin | Includes architectural import-boundary rules |

## 2) Project hierarchy (key structure)

```text
frontend/
|-- src/
|   |-- app/
|   |   |-- layout.tsx
|   |   |-- page.tsx
|   |   |-- globals.css
|   |   |-- (app)/
|   |   |   |-- layout.tsx
|   |   |   |-- dashboard/page.tsx
|   |   |   |-- chat/page.tsx
|   |   |   |-- jobs/[id]/page.tsx
|   |   |   |-- onboarding/page.tsx
|   |   |   |-- search/page.tsx
|   |   |   `-- settings/page.tsx
|   |   `-- (auth)/
|   |       `-- auth/
|   |           |-- login/page.tsx
|   |           `-- verify/page.tsx
|   |
|   |-- features/
|   |   |-- manifest.ts
|   |   |-- chat/
|   |   |-- jobs/
|   |   |-- onboarding/
|   |   |-- resolution/
|   |   |-- search/
|   |   `-- settings/
|   |
|   |-- shell/
|   |   |-- providers.tsx
|   |   |-- components/
|   |   `-- state/
|   |
|   |-- lib/
|   |   |-- api/
|   |   |-- auth/
|   |   `-- query/
|   |
|   |-- shared/
|   |   |-- contracts/
|   |   `-- errors/
|   |
|   `-- state/
|
|-- tests/
|   `-- frontend/
|       |-- resolution/
|       `-- settings/
|
|-- package.json
|-- next.config.ts
|-- tsconfig.json
|-- eslint.config.mjs
|-- vitest.config.ts
`-- vitest.setup.ts
```

## 3) Route hierarchy

The app uses App Router route groups to separate authenticated app routes from auth routes.

- Public/auth group:
  - `/auth/login`
  - `/auth/verify`
- App shell group:
  - `/dashboard`
  - `/chat`
  - `/jobs/[id]`
  - `/onboarding`
  - `/search`
  - `/settings`

`src/app/page.tsx` redirects `/` to `/dashboard`.

## 4) Architectural layers and responsibilities

1. `src/app/*`
- Route entry points and layout wiring.
- Minimal orchestration; delegate feature logic to `features`, `shell`, and `lib`.

2. `src/features/*`
- Domain-specific functionality (chat/jobs/onboarding/resolution/search/settings).
- Owns feature API adapters, hooks, and components.

3. `src/shell/*`
- Global app shell, navigation/chrome, notifications, cross-feature surfaces.
- Hosts `QueryClientProvider` in `providers.tsx`.

4. `src/lib/*`
- Shared technical foundations:
  - API client and RFC 7807 normalization
  - Auth guard logic and redirect safety
  - Query key factories

5. `src/shared/*`
- Shared contracts/types and error presentation primitives.
- Must remain independent from app/feature/shell internals.

6. `src/state/*` and feature state folders
- Zustand stores for persisted UI preferences and transient drafts/session workflow state.

## 5) Guard model and routing behavior

The frontend uses a 3-flag guard state:

- `A`: authenticated
- `V`: email verified
- `S`: store connected

Core guard logic is in `src/lib/auth/guards.ts`.
`AppShell` hydrates guard state from backend endpoints and applies safe redirects.

## 6) API and environment configuration

API client: `src/lib/api/client.ts`

Base URL resolution:
1. `NEXT_PUBLIC_API_BASE_URL` if set.
2. `http://localhost:5000` when browser hostname is `localhost`.
3. Empty string (same-origin) fallback.

All requests use `credentials: "include"` for session cookie flows.

## 7) Feature manifest

`src/features/manifest.ts` defines the manifest contract used to map feature route prefixes and required guard state.

Example entries currently include:
- onboarding (`A+V`)
- jobs (`A+V+S`)
- chat (`A+V+S`)

## 8) Quality gates and code boundaries

ESLint rules enforce architectural boundaries:

1. No deep shell imports into feature internals.
2. `shared` cannot depend on `features`, `shell`, or `app`.
3. Cross-feature restrictions between onboarding and jobs internals.
4. Strict TypeScript linting (`no-explicit-any`, strict ts-comment policy, unused vars policy).

## 9) Testing strategy

Test types in this frontend:
1. Component tests (`*.test.tsx`)
2. Hook and utility tests (`*.test.ts`)
3. Route/contract tests in `src/app/*` and `tests/frontend/*`

Focus areas include:
1. Routing and guard contracts
2. Responsive shell behavior
3. API error normalization
4. Feature contracts and data-flow helpers

## 10) Local development commands

From `frontend/`:

```bash
npm install
npm run dev
```

Other commands:

```bash
npm run build
npm run start
npm run lint
npm run typecheck
npm run test
npm run test:watch
```

## 11) Developer auth bypass (local only)

If backend auth is not ready and you still need to navigate protected app routes:

1. In `next dev`, bypass is enabled by default (`NODE_ENV=development`).
2. Optional explicit flag in `frontend/.env.local`:
```bash
NEXT_PUBLIC_DEV_AUTH_BYPASS=1
```
3. Restart the dev server after env changes.
4. Open `/auth/login` and use:
   - `Sign in (verified)` or
   - `Sign in (full access)`

When bypass is enabled, `AppShell` trusts local guard cookies instead of forcing
backend session checks on every route.

## 12) Conventions for new work

1. Add new route pages under `src/app` and keep business logic in `src/features`.
2. Keep global concerns in `src/shell` and low-level utilities in `src/lib`.
3. Add shared cross-feature types to `src/shared/contracts`.
4. Add tests alongside implementation (`*.test.ts` / `*.test.tsx`) or in `tests/frontend` for cross-cutting contract tests.
5. Respect import-boundary rules; do not bypass by deep-linking across layers.





