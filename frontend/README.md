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





<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>Premium Glassmorphic AI Dashboard</title>
<script src="https://cdn.tailwindcss.com?plugins=forms,typography"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" rel="stylesheet"/>
<script>
        tailwind.config = {
            darkMode: "class",
            theme: {
                extend: {
                    colors: {
                        primary: "#FFFFFF", 
                        "background-dark": "#0a0a0f", 
                        "surface-dark": "#121212",
                        "card-dark": "#1c1c24",
                        "border-dark": "#27272a",
                    },
                    fontFamily: {
                        display: ["Inter", "sans-serif"],
                        sans: ["Inter", "sans-serif"],
                    },
                    borderRadius: {
                        DEFAULT: "0.25rem",'xl': '0.75rem','2xl': '1rem',
                        'card': '0.5rem', 
                    },
                    boxShadow: {
                        'glow': '0 0 20px -5px rgba(255, 255, 255, 0.05)',
                        'input-glow': '0 0 15px -3px rgba(255,255,255,0.1), inset 0 0 20px -10px rgba(255,255,255,0.05)',
                        'glass': '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
                    },
                    backgroundImage: {
                        'noise': "url('data:image/svg+xml,%3Csvg viewBox=%220 0 200 200%22 xmlns=%22http://www.w3.org/2000/svg%22%3E%3Cfilter id=%22noiseFilter%22%3E%3CfeTurbulence type=%22fractalNoise%22 baseFrequency=%220.65%22 numOctaves=%223%22 stitchTiles=%22stitch%22/%3E%3C/filter%3E%3Crect width=%22100%25%22 height=%22100%25%22 filter=%22url(%23noiseFilter)%22 opacity=%220.07%22/%3E%3C/svg%3E')",
                    }
                },
            },
        };
    </script>
<style>
        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }
        ::-webkit-scrollbar-track {
            background: transparent;
        }
        ::-webkit-scrollbar-thumb {
            background: #3f3f46;
            border-radius: 3px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #52525b;
        }
        body {
            font-family: 'Inter', sans-serif;
        }
        .material-symbols-rounded {
          font-variation-settings:
          'FILL' 0,
          'wght' 300,
          'GRAD' 0,
          'opsz' 24
        }
        .filled-icon {
            font-variation-settings: 'FILL' 1;
        }
        .glass-panel {
            background: rgba(18, 18, 18, 0.6);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border-right: 1px solid rgba(255, 255, 255, 0.08);
        }
        .glass-input {
            background: rgba(28, 28, 36, 0.4);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.15);
            box-shadow: 0 0 15px -3px rgba(255,255,255,0.05);
        }
    </style>
</head>
<body class="bg-background-dark text-gray-100 h-screen flex overflow-hidden selection:bg-white selection:text-black dark relative">
<div class="absolute inset-0 z-0 bg-noise pointer-events-none opacity-40 mix-blend-overlay"></div>
<div class="absolute inset-0 z-0 bg-gradient-to-b from-[#0a0a0f] via-[#0d0d12] to-[#0a0a0f] pointer-events-none"></div>
<aside class="w-16 flex flex-col items-center py-4 glass-panel flex-shrink-0 z-20 relative">
<div class="mb-6">
<button class="w-10 h-10 flex items-center justify-center rounded-xl bg-gray-800/50 hover:bg-gray-700/50 transition-colors border border-white/5">
<span class="material-symbols-rounded text-gray-300">asterisk</span>
</button>
</div>
<nav class="flex-1 flex flex-col gap-4 w-full px-2">
<button class="w-10 h-10 mx-auto flex items-center justify-center rounded-lg text-gray-400 hover:bg-white/10 hover:text-white transition-colors" title="Layout">
<span class="material-symbols-rounded">space_dashboard</span>
</button>
<button class="w-10 h-10 mx-auto flex items-center justify-center rounded-lg text-gray-400 hover:bg-white/10 hover:text-white transition-colors" title="New">
<span class="material-symbols-rounded">add_box</span>
</button>
<button class="w-10 h-10 mx-auto flex items-center justify-center rounded-lg text-gray-400 hover:bg-white/10 hover:text-white transition-colors" title="Search">
<span class="material-symbols-rounded">search</span>
</button>
<button class="w-10 h-10 mx-auto flex items-center justify-center rounded-xl bg-gray-700/50 text-white transition-colors shadow-glow border border-white/10" title="AI Tools">
<span class="material-symbols-rounded filled-icon">auto_awesome</span>
</button>
<button class="w-10 h-10 mx-auto flex items-center justify-center rounded-lg text-gray-400 hover:bg-white/10 hover:text-white transition-colors" title="Images">
<span class="material-symbols-rounded">image</span>
</button>
<button class="w-10 h-10 mx-auto flex items-center justify-center rounded-lg text-gray-400 hover:bg-white/10 hover:text-white transition-colors" title="Grid">
<span class="material-symbols-rounded">grid_view</span>
</button>
<button class="w-10 h-10 mx-auto flex items-center justify-center rounded-lg text-gray-400 hover:bg-white/10 hover:text-white transition-colors" title="Code">
<span class="material-symbols-rounded">code</span>
</button>
<button class="w-10 h-10 mx-auto flex items-center justify-center rounded-lg text-gray-400 hover:bg-white/10 hover:text-white transition-colors" title="Folder">
<span class="material-symbols-rounded">folder_open</span>
</button>
</nav>
<div class="flex flex-col gap-4 w-full px-2 mt-auto">
<button class="w-10 h-10 mx-auto flex items-center justify-center rounded-lg text-gray-400 hover:bg-white/10 hover:text-white transition-colors">
<span class="material-symbols-rounded">info</span>
</button>
<button class="w-10 h-10 mx-auto flex items-center justify-center rounded-lg text-gray-400 hover:bg-white/10 hover:text-white transition-colors">
<span class="material-symbols-rounded">headphones</span>
</button>
<button class="w-10 h-10 mx-auto flex items-center justify-center rounded-lg text-gray-400 hover:bg-white/10 hover:text-white transition-colors">
<span class="material-symbols-rounded">settings</span>
</button>
<button class="w-10 h-10 mx-auto flex items-center justify-center rounded-lg text-gray-400 hover:bg-white/10 hover:text-white transition-colors">
<span class="material-symbols-rounded">flare</span>
</button>
<button class="w-10 h-10 mx-auto mt-2 rounded-full overflow-hidden border border-white/10">
<img alt="User profile" class="w-full h-full object-cover opacity-80 hover:opacity-100 transition-opacity" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDD9h_iXky16WcCbArhY7GW1tU5aWbMqUW1LWBKI-GXj-871fsiM8lRlX3nf8VIoXPdmfk6HSyDvqG_Y9ktmeuJbXlO5kW5dAzPAnp62B6uuISnlt9P30uGjTYsAXdoxOTKBcFef4odmiuJ-u7gVAoAomT-QjS6rCZbt2Ar2lRp_heqrauRz-7Joj9vs5MMhb56irRGO3pnZXQSjBy8kPdNe5oLEcnyPql-e-xcS3xGbRp18psQthkmCXmnZn8nPHLLLBO-QwLnkQ"/>
</button>
</div>
</aside>
<main class="flex-1 flex flex-col h-full relative overflow-hidden z-10">
<header class="h-16 flex items-center px-6 border-b border-white/5 bg-transparent backdrop-blur-sm z-10 sticky top-0">
<div class="flex items-center gap-2 cursor-pointer group">
<h1 class="font-medium text-sm text-gray-200 tracking-wide">Proxyum 5.0</h1>
<span class="material-symbols-rounded text-base text-gray-500 group-hover:text-gray-300 transition-colors">arrow_drop_down</span>
</div>
<div class="ml-auto flex items-center gap-4">
<button class="text-gray-500 hover:text-white transition-colors">
<span class="material-symbols-rounded text-xl">more_horiz</span>
</button>
<button class="text-gray-500 hover:text-white transition-colors">
<span class="material-symbols-rounded text-xl">ios_share</span>
</button>
<button class="text-gray-500 hover:text-white transition-colors">
<span class="material-symbols-rounded text-xl">help</span>
</button>
</div>
</header>
<div class="flex-1 overflow-y-auto w-full relative custom-scrollbar">
<div class="absolute top-[-10%] left-1/2 -translate-x-1/2 w-3/4 h-1/2 bg-gradient-to-b from-white/5 to-transparent blur-[120px] pointer-events-none rounded-full"></div>
<div class="max-w-4xl mx-auto px-6 py-20 flex flex-col items-center relative z-10">
<div class="text-center mb-16 animate-fade-in-up">
<h2 class="text-4xl md:text-5xl font-bold text-white mb-3 tracking-tight drop-shadow-lg">Welcome to Proxyum!</h2>
<div class="flex items-center justify-center gap-2 text-xl md:text-2xl text-gray-400 font-normal">
<span>Friendly Vanuel</span>
<span class="text-2xl animate-pulse">👋</span>
</div>
</div>
<div class="w-full mb-12">
<h3 class="text-xs uppercase tracking-wider font-semibold text-gray-500 mb-4 ml-1">Starters</h3>
<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
<div class="bg-[#1c1c24] border border-white/10 hover:border-white/20 p-6 rounded-xl flex items-center justify-between group transition-all duration-300 cursor-pointer shadow-lg hover:shadow-glow hover:-translate-y-0.5">
<div class="flex flex-col gap-1 pr-4">
<span class="font-bold text-gray-100 text-lg">Smart Response Assistant</span>
<span class="text-xs text-gray-500 font-medium">Create instant, accurate AI replies.</span>
</div>
<button class="bg-transparent border border-white/20 hover:bg-white/5 text-xs font-semibold px-4 py-2 rounded-lg flex items-center gap-2 transition-colors text-gray-300 hover:text-white whitespace-nowrap">
<span class="material-symbols-rounded text-sm">auto_awesome</span>
                            Generate
                        </button>
</div>
<div class="bg-[#1c1c24] border border-white/10 hover:border-white/20 p-6 rounded-xl flex items-center justify-between group transition-all duration-300 cursor-pointer shadow-lg hover:shadow-glow hover:-translate-y-0.5">
<div class="flex flex-col gap-1 pr-4">
<span class="font-bold text-gray-100 text-lg">Chatbot Flow Generator</span>
<span class="text-xs text-gray-500 font-medium">Design smart reply flows in seconds.</span>
</div>
<button class="bg-transparent border border-white/20 hover:bg-white/5 text-xs font-semibold px-4 py-2 rounded-lg flex items-center gap-2 transition-colors text-gray-300 hover:text-white whitespace-nowrap">
<span class="material-symbols-rounded text-sm">auto_awesome</span>
                            Generate
                        </button>
</div>
</div>
</div>
<div class="flex flex-wrap items-center justify-center gap-3 w-full mb-10">
<button class="flex items-center gap-2 px-5 py-2.5 rounded-full border border-white/10 bg-[#1c1c24] hover:bg-white/5 hover:border-white/20 transition-all text-xs font-medium text-gray-400 hover:text-white shadow-sm">
<span class="material-symbols-rounded text-sm">bar_chart</span>
                    Market Trend Research
                </button>
<button class="flex items-center gap-2 px-5 py-2.5 rounded-full border border-white/10 bg-[#1c1c24] hover:bg-white/5 hover:border-white/20 transition-all text-xs font-medium text-gray-400 hover:text-white shadow-sm">
<span class="material-symbols-rounded text-sm">assignment</span>
                    Generate Reports
                </button>
<button class="flex items-center gap-2 px-5 py-2.5 rounded-full border border-white/10 bg-[#1c1c24] hover:bg-white/5 hover:border-white/20 transition-all text-xs font-medium text-gray-400 hover:text-white shadow-sm">
<span class="material-symbols-rounded text-sm">database</span>
                    Create Data Visual
                </button>
</div>
<div class="w-full relative group">
<div class="absolute -inset-[1px] bg-gradient-to-r from-transparent via-white/10 to-transparent rounded-xl blur-md group-focus-within:via-white/20 transition-all duration-500 opacity-60"></div>
<div class="relative glass-input rounded-xl p-5 shadow-input-glow transition-all">
<textarea class="w-full bg-transparent border-none focus:ring-0 resize-none text-gray-100 placeholder-gray-500 text-base min-h-[60px]" placeholder="Ask anything..." rows="2"></textarea>
<div class="flex items-center justify-between mt-3 pt-2 border-t border-white/5">
<div class="flex items-center gap-2">
<button class="w-9 h-9 flex items-center justify-center rounded-lg hover:bg-white/10 text-gray-400 hover:text-white transition-colors border border-white/5 bg-white/5 backdrop-blur-sm">
<span class="material-symbols-rounded text-xl">add</span>
</button>
<button class="h-9 px-3 flex items-center gap-1.5 rounded-lg hover:bg-white/10 text-gray-400 hover:text-white transition-colors text-xs font-medium border border-white/5 bg-white/5 backdrop-blur-sm">
<span class="material-symbols-rounded text-sm">attachment</span>
                                Attach
                            </button>
<button class="h-9 px-3 flex items-center gap-1.5 rounded-lg hover:bg-white/10 text-gray-400 hover:text-white transition-colors text-xs font-medium border border-white/5 bg-white/5 backdrop-blur-sm">
<span class="material-symbols-rounded text-sm">language</span>
                                Deep Search
                            </button>
<button class="h-9 px-3 flex items-center gap-1.5 rounded-lg hover:bg-white/10 text-gray-400 hover:text-white transition-colors text-xs font-medium border border-white/5 bg-white/5 backdrop-blur-sm">
<span class="material-symbols-rounded text-sm">image</span>
                                Generate Image
                            </button>
</div>
<div class="flex items-center gap-3">
<button class="w-9 h-9 flex items-center justify-center rounded-full hover:bg-white/10 text-gray-400 hover:text-white transition-colors">
<span class="material-symbols-rounded">graphic_eq</span>
</button>
<button class="w-9 h-9 flex items-center justify-center rounded-lg bg-white text-black hover:bg-gray-200 transition-colors shadow-glow">
<span class="material-symbols-rounded text-xl filled-icon">arrow_upward</span>
</button>
</div>
</div>
</div>
</div>
<div class="mt-6 flex items-center gap-2 text-[10px] sm:text-xs text-gray-600 font-light">
<span class="material-symbols-rounded text-sm">info</span>
<p>Don't enter sensitive info. AI may generate inaccurate or incomplete responses.</p>
</div>
</div>
</div>
</main>

</body></html>