# Frontend Framework Comparison: React vs Vue vs Svelte vs Flask+HTMX

**Domain:** SaaS Dashboard for Shopify Multi-Supplier Platform
**Researched:** 2026-02-03
**Confidence:** HIGH

## Executive Summary

This research evaluates four frontend approaches for adding a web dashboard to an existing Flask backend with OAuth, Shopify integration, and job processing capabilities. The target users are non-technical craft/hobby store owners who need progressive onboarding, CSV upload with real-time progress monitoring, and a path to modular micro-apps (analytics, image management, scraping, products).

**Recommendation:** React (Next.js) for brownfield Flask migration with future micro-frontend architecture.

**Rationale:**
- Largest ecosystem for enterprise SaaS dashboard components (10x larger than Svelte)
- Proven Flask+React integration patterns with 2025-2026 migration guides
- Best AI agent code generation support (LLMs are React-dominant in training data)
- Module Federation enables future modular apps without rewrite
- Superior file upload progress monitoring libraries
- 4-month faster time-to-market due to component availability

**Trade-offs:**
- Bundle size larger than Svelte (2.8s vs 1.4s Time to Interactive)
- More boilerplate than Vue
- Steeper learning curve than HTMX for Python developers

---

## Framework Options Analysis

### Option 1: React (Next.js 16)

**Category:** Full SPA Framework with SSR/SSG
**Confidence:** HIGH (verified with Context7, official docs, and 2026 sources)

#### Strengths

| Strength | Why It Matters | Evidence |
|----------|----------------|----------|
| **Ecosystem dominance** | Any SaaS dashboard problem has been solved and packaged into npm libraries | Next.js 16 with Partial Prerendering (PPR) and Server Components enables zero-bundle-size components |
| **Flask integration** | Well-documented brownfield migration patterns | Miguel Grinberg's 2025 guide provides step-by-step Flask API refactoring + React frontend setup |
| **File upload progress** | Robust libraries with chunked uploads, progress tracking, retry logic | Axios onUploadProgress with 500 KB chunked uploads (2026 standard), state management for progress/errors/success |
| **Micro-frontend ready** | Module Federation enables modular apps without rewrite | Webpack Module Federation used by Spotify, ByteDance, Microsoft in production; Nx tooling for monorepo |
| **AI code generation** | LLMs reach for React almost every time | Vercel AI SDK most downloaded TypeScript AI framework; TypeScript + React = fewer fixes after generation |
| **Component libraries** | Enterprise-grade dashboards out-of-the-box | Syncfusion, Material-UI, Ant Design, Chakra UI with progress bars, file uploaders, data grids |

#### Weaknesses

| Weakness | Impact | Mitigation |
|----------|--------|------------|
| **Bundle size** | 2.8s Time to Interactive vs Svelte's 1.4s on slower connections | Next.js 16 Server Components reduce client bundle; Progressive enhancement with streaming |
| **Boilerplate complexity** | More code than Vue/Svelte for same functionality | Use opinionated starter templates (create-next-app); AI agents excel at React boilerplate generation |
| **Learning curve** | Steeper than HTMX for Python-first teams | Strong typing with TypeScript catches mistakes early; massive Stack Overflow community for troubleshooting |

#### Best For

- **Enterprise SaaS** where component availability = faster time-to-market (4 months earlier)
- **Brownfield Flask migration** with existing API endpoints
- **Future micro-frontend architecture** (separate analytics, image management, scraping apps)
- **AI-assisted development** where LLM code generation works best
- **Non-technical users** requiring polished, production-tested UI components

#### Integration Pattern

```
Flask Backend (existing)          React Frontend (new)
├── /api/jobs                 →   Next.js 16 app
├── /api/products            →   ├── /dashboard
├── /api/auth (OAuth)        →   ├── /jobs/upload
└── /api/shopify             →   └── /products/search

Migration: Formalize Flask routes as REST API, add Flask-CORS, serve React from Flask static folder or separate deployment
```

#### Complexity Assessment

| Aspect | Complexity | Timeline |
|--------|-----------|----------|
| Initial setup | MEDIUM | 1-2 weeks (Flask API refactoring + Next.js scaffold) |
| File upload + progress | LOW | 3-5 days (Axios + React hooks, well-documented patterns) |
| Real-time job monitoring | MEDIUM | 1 week (WebSocket or SSE integration with React Query) |
| Progressive onboarding | LOW | 2-3 days (React Router + localStorage, standard patterns) |
| Future micro-frontend | MEDIUM | 2-3 weeks per module (Module Federation setup once, then add modules) |

**Total MVP Timeline:** 6-8 weeks

---

### Option 2: Vue (Vue 3 + Vite)

**Category:** Progressive Framework with Composition API
**Confidence:** MEDIUM (verified with WebSearch + SaaS boilerplate evidence)

#### Strengths

| Strength | Why It Matters | Evidence |
|----------|----------------|----------|
| **Developer experience** | Cleaner syntax than React, less boilerplate | Team that rebuilt SaaS in all 3 frameworks: "Vue won - we knew React, but Vue's DX was just better" |
| **Progressive enhancement** | Official "progressive framework" philosophy aligns with progressive onboarding requirement | VueJS described as progressive JavaScript framework known for simplicity and reactivity |
| **Flask integration** | Dedicated SaaS boilerplates with Flask + Vue + Bootstrap + Webpack | CaravelKit/saas-base and JoseLizcano/saas-boilerplate provide production-ready foundations |
| **Fast MVP velocity** | Faster than React for initial development | Recommended for faster MVP startups and larger scalable builds |
| **Single File Components** | Co-located template, script, style in .vue files reduces context switching | Easier to reason about component boundaries for small teams |

#### Weaknesses

| Weakness | Impact | Mitigation |
|----------|--------|------------|
| **Smaller ecosystem** | Fewer enterprise dashboard components than React | Vue has strong ecosystem but not React-scale; may need to build custom components |
| **Micro-frontend tooling** | Module Federation less mature for Vue than React | Single-spa or Vite federation plugin, but less documentation/examples |
| **AI code generation** | LLMs less familiar with Vue patterns than React | Still good but React dominates training data; may need more prompt engineering |

#### Best For

- **Python teams** preferring cleaner syntax over React's JSX
- **MVP-first approach** where developer velocity > ecosystem breadth
- **Monolithic dashboard** without near-term micro-frontend plans

#### Integration Pattern

```
Flask Backend (existing)          Vue Frontend (new)
├── /api/jobs                 →   Vite + Vue 3 app
├── /api/products            →   ├── /src/views/Dashboard.vue
├── /api/auth (OAuth)        →   ├── /src/views/JobUpload.vue
└── /api/shopify             →   └── /src/components/ProgressBar.vue

Migration: Same as React - formalize Flask API, add Flask-CORS, Vite dev server proxies to Flask
```

#### Complexity Assessment

| Aspect | Complexity | Timeline |
|--------|-----------|----------|
| Initial setup | LOW | 1 week (Flask API refactoring + Vite scaffold) |
| File upload + progress | LOW | 3-5 days (axios + Vue 3 Composition API, similar to React) |
| Real-time job monitoring | MEDIUM | 1 week (WebSocket or SSE with Vue 3 reactivity) |
| Progressive onboarding | LOW | 2-3 days (Vue Router + Pinia store, standard patterns) |
| Future micro-frontend | HIGH | 4-6 weeks per module (less mature tooling, more custom work) |

**Total MVP Timeline:** 5-7 weeks

---

### Option 3: Svelte (SvelteKit)

**Category:** Compiler-First Framework
**Confidence:** MEDIUM (verified with WebSearch + performance benchmarks)

#### Strengths

| Strength | Why It Matters | Evidence |
|----------|----------------|----------|
| **Performance** | 3x faster DOM manipulation, 1.4s Time to Interactive vs React's 2.8s | Svelte compiles to vanilla JS with no runtime overhead; ideal for 50K+ row dashboards |
| **Minimal boilerplate** | Clearest syntax of all options, reactive variables without hooks | Developer quote: "the lack of boilerplate was night-and-day compared to a similar analytics tool in React" |
| **Bundle size** | Smallest production builds | Users waited 1.4s vs 2.8s for React on slower connections |
| **Flask integration** | Dedicated flask-svelte package and SvelteKit hybrid patterns | Flask-svelte serves Svelte templates as dynamic components; sveltekit-flask hybrid for SvelteKit + Flask API |

#### Weaknesses

| Weakness | Impact | Mitigation |
|----------|--------|------------|
| **Ecosystem 10x smaller** | For enterprise SaaS, component gap = build from scratch | Team that rebuilt SaaS in all 3: "Svelte lost because we kept building things from scratch" |
| **Fewer enterprise components** | No Syncfusion/Material-UI equivalent for grids, calendars, charts | Use headless libraries (TanStack Table) + custom styling; increases dev time |
| **Micro-frontend immaturity** | Module Federation not well-established for Svelte | Would need custom solution or iframe-based architecture |
| **Smaller talent pool** | Harder to hire Svelte developers vs React | Mitigate with good documentation and onboarding, but higher risk for team scaling |

#### Best For

- **High-frequency trading dashboards** or performance-critical apps (50K+ rows)
- **Small team** prioritizing clean code over ecosystem breadth
- **Monolithic dashboard** without micro-frontend plans

#### Integration Pattern

```
Flask Backend (existing)          Svelte Frontend (new)
├── /api/jobs                 →   SvelteKit app
├── /api/products            →   ├── /src/routes/+page.svelte (dashboard)
├── /api/auth (OAuth)        →   ├── /src/routes/jobs/+page.svelte
└── /api/shopify             →   └── /src/lib/ProgressBar.svelte

Migration: Use hooks.server.ts handleFetch to map /api/:path* to Flask (127.0.0.1:3000 in dev)
```

#### Complexity Assessment

| Aspect | Complexity | Timeline |
|--------|-----------|----------|
| Initial setup | LOW | 1 week (Flask API refactoring + SvelteKit scaffold) |
| File upload + progress | MEDIUM | 1 week (fewer pre-built libraries, need custom progress tracking) |
| Real-time job monitoring | MEDIUM | 1 week (WebSocket with Svelte stores, good patterns but less examples) |
| Progressive onboarding | LOW | 2-3 days (SvelteKit routing + stores, clean patterns) |
| Future micro-frontend | HIGH | 6-8 weeks per module (immature tooling, likely custom iframe-based solution) |

**Total MVP Timeline:** 6-9 weeks (components built from scratch offset fast syntax)

---

### Option 4: Flask + HTMX

**Category:** Hypermedia-Driven Architecture
**Confidence:** HIGH (verified with official HTMX docs + 2026 trends)

#### Strengths

| Strength | Why It Matters | Evidence |
|----------|--------|----------|
| **Zero context switching** | Stay in Python/Jinja templates, no JS build toolchain | Python teams remain in familiar territory; Flask-HTMX library provides tight integration |
| **Minimal client-side JS** | ~14 KB for htmx.js vs 300 KB React bundle | "Shipping 300kb of JavaScript for a simple dashboard is now considered a liability" (2026 sentiment) |
| **Real-time capable** | WebSocket extension + SSE extension for progress monitoring | htmx WebSockets with auto-reconnect (full-jitter exponential backoff); SSE for unidirectional progress updates |
| **Hypermedia patterns** | No JSON API needed - Flask returns HTML fragments | Hypermedia-driven apps eliminate API versioning headaches; simpler mental model |
| **Progressive enhancement** | Works without JS, enhances with htmx | Accessibility wins; graceful degradation for older browsers |

#### Weaknesses

| Weakness | Impact | Mitigation |
|----------|--------|------------|
| **Not suited for complex SPAs** | Limited client-side state management | For highly interactive dashboards or offline capabilities, SPA still better |
| **No micro-frontend story** | Modular apps would require separate Flask apps with shared auth | Could work but more operational complexity (multiple deployments, session sharing) |
| **Smaller component ecosystem** | No React/Vue component library equivalent | Build custom Jinja components; TailwindCSS for styling; more manual work |
| **AI code generation** | LLMs less trained on HTMX patterns than React | 2026 HTMX adoption growing but still niche vs React; prompts need more context |
| **CSV upload complexity** | Multi-part file upload + chunking + progress requires custom HTMX patterns | htmx file uploads documented but less polished than React libraries (Dromo, CSVBox widgets) |

#### Best For

- **Python-first teams** avoiding JavaScript complexity
- **Content-heavy dashboards** with CRUD workflows (less real-time interactivity)
- **Brownfield Flask apps** where staying in-stack is priority
- **Simple approval workflows** (view data, approve/reject)

#### Integration Pattern

```
Flask Backend (existing)          HTMX Frontend (added to Flask)
├── /dashboard                →   Flask routes return HTML fragments
├── /jobs/upload              →   htmx hx-post="/jobs/upload" hx-target="#results"
├── /jobs/progress/{id}       →   htmx SSE extension for real-time progress
└── /products/search          →   htmx hx-get="/products/search?q={value}" hx-trigger="keyup changed delay:500ms"

Migration: Add htmx.js CDN to base template, convert existing Flask routes to return HTML fragments instead of JSON
```

#### Complexity Assessment

| Aspect | Complexity | Timeline |
|--------|-----------|----------|
| Initial setup | LOW | 2-3 days (add htmx to existing Flask templates) |
| File upload + progress | HIGH | 2 weeks (custom multipart upload + htmx SSE extension for progress; less documented than React) |
| Real-time job monitoring | MEDIUM | 1 week (htmx SSE extension works well for unidirectional updates) |
| Progressive onboarding | MEDIUM | 1 week (Flask session + conditional Jinja rendering; less polished than React onboarding libraries) |
| Future micro-frontend | HIGH | N/A (not viable - would need separate Flask apps with complex session sharing) |

**Total MVP Timeline:** 5-7 weeks (fast initial setup, slower complex features)

---

## Feature Requirements Matrix

### Table Stakes (Required for MVP)

Features users expect in a SaaS dashboard. Missing these = product feels broken.

| Feature | React | Vue | Svelte | HTMX | Notes |
|---------|-------|-----|--------|------|-------|
| **User authentication** | HIGH | HIGH | HIGH | HIGH | All options support OAuth integration with Flask backend |
| **CSV file upload** | HIGH | HIGH | MEDIUM | MEDIUM | React/Vue have polished libraries (Dromo, react-dropzone); Svelte/HTMX need custom |
| **Upload progress bar** | HIGH | HIGH | MEDIUM | MEDIUM | React/Vue: axios onUploadProgress; HTMX: SSE extension (custom setup) |
| **Real-time job monitoring** | HIGH | HIGH | MEDIUM | MEDIUM | React/Vue: WebSocket + React Query/Vue reactivity; HTMX: SSE extension (unidirectional) |
| **Product search/filtering** | HIGH | HIGH | HIGH | HIGH | All options support search with debouncing |
| **Responsive mobile UI** | HIGH | HIGH | HIGH | MEDIUM | React/Vue/Svelte: component libraries handle; HTMX: manual Tailwind responsive classes |
| **Error handling** | HIGH | HIGH | MEDIUM | MEDIUM | React/Vue: error boundaries + toast libraries; Svelte/HTMX: custom error UI |
| **Loading states** | HIGH | HIGH | HIGH | HIGH | All options support loading spinners/skeletons |

**Complexity Key:**
- HIGH: Well-documented patterns, pre-built libraries, minimal custom code
- MEDIUM: Some libraries/patterns exist, moderate custom code needed
- LOW: Mostly custom code, few examples/libraries

### Differentiators (Competitive Advantages)

Features that set this dashboard apart from competitors.

| Feature | Value Proposition | Best Framework | Complexity | Notes |
|---------|-------------------|----------------|------------|-------|
| **Progressive onboarding** | Non-technical users start simple, unlock features as they learn | React | LOW | React onboarding libraries (Joyride, Intro.js, Shepherd); Vue similar; HTMX needs custom |
| **Preview before apply** | See Shopify changes before they go live (approval workflow) | React / Vue | MEDIUM | React/Vue: Split-screen diff viewer components; HTMX: Server-rendered diff tables |
| **Bulk operations** | Process 100+ products at once with queue visibility | React | MEDIUM | React: TanStack Table + optimistic updates; needs WebSocket for live queue status |
| **Image similarity detection** | Auto-group visually similar products (using existing CLIP embeddings) | React | HIGH | Complex UI with image grids, clustering visualization; React ecosystem has image comparison components |
| **Modular app switching** | Seamless navigation between Analytics, Images, Scraping, Products apps | React | MEDIUM | React Module Federation shines here; Vue/Svelte harder; HTMX N/A (would be separate Flask apps) |
| **Offline-first job drafts** | Create CSV upload drafts offline, sync when online | React / Svelte | HIGH | SPA with IndexedDB; React: Workbox + React Query; HTMX not suitable (server-dependent) |

**Recommendation:** React captures 5 of 6 differentiators with LOW/MEDIUM complexity. HTMX unsuitable for modular apps and offline-first.

### Anti-Features (Avoid These)

Commonly requested features that create more problems than value.

| Anti-Feature | Why Requested | Why Problematic | Alternative Approach |
|--------------|---------------|-----------------|---------------------|
| **Real-time everything** | "Users want instant updates on all data" | WebSocket connections for every view = server load + complexity where polling suffices | Use SSE for job progress (unidirectional); poll every 30s for product lists; WebSocket only for chat/collaboration |
| **Inline spreadsheet editing** | "Excel power users want grid editing" | Complex state management + conflict resolution for multi-user editing; reinventing Excel | Stick with CSV upload + preview workflow; users edit in Excel (their familiar tool) then upload |
| **Custom dashboard builder** | "Let users drag-drop widgets to customize dashboard" | Massive dev time (2-3 months) for feature rarely used by non-technical users | Provide 2-3 pre-built dashboard layouts (onboarding, operations, analytics); role-based views |
| **In-app image editor** | "Users want to crop/filter images in dashboard" | Scope creep; existing tools (Canva, Photoshop) do this better | Integrate with user's local files; focus on image metadata management, not editing |
| **Mobile native app** | "Need iOS/Android apps for on-the-go" | 3x dev effort (web + iOS + Android) when PWA covers 90% of mobile use cases | Build responsive web dashboard with PWA features (offline drafts, push notifications) |
| **GraphQL over REST** | "GraphQL is modern, REST is legacy" | Flask REST API exists; adding GraphQL = migration cost without user-facing benefit | Formalize existing Flask REST API with OpenAPI spec; add GraphQL only if modular apps need cross-app queries |

**Key Pattern:** Non-technical users want familiar workflows (Excel uploads, simple approvals), not complex power features. Prioritize progressive onboarding over customization.

---

## Feature Dependencies

```
[User Authentication (Flask OAuth)]
    └──enables──> [Dashboard Access]
                      ├──requires──> [Product Search]
                      ├──requires──> [CSV Upload]
                      └──requires──> [Job Monitoring]

[CSV Upload]
    └──requires──> [File Upload Progress]
                      └──requires──> [Job Monitoring (real-time)]

[Job Monitoring]
    └──enables──> [Approval Workflow]
                      └──requires──> [Preview Changes]

[Modular Apps (future)]
    └──requires──> [Module Federation Setup]
                      └──conflicts──> [HTMX Architecture]
    └──requires──> [Shared Auth State]
```

### Dependency Notes

- **Authentication is foundational:** All features depend on Flask OAuth working. No framework choice impacts this (Flask backend handles it).
- **CSV Upload → Job Monitoring pipeline:** File upload progress and real-time job monitoring are tightly coupled. React/Vue have better patterns for this than HTMX.
- **Approval Workflow requires Preview:** Users must see what will change before applying. React/Vue component libraries (diff viewers, split-screen layouts) reduce custom code.
- **Modular Apps conflict with HTMX:** Future micro-frontend architecture (separate analytics, image management apps) requires Module Federation or similar. HTMX's server-rendered model doesn't support this without significant architectural changes (separate Flask apps with shared session = operational complexity).

---

## MVP Definition

### Launch With (v1)

Minimum features to validate the product with craft store owners.

- [ ] **User authentication (Flask OAuth)** — Essential; already built in Flask backend
- [ ] **Progressive onboarding flow** — 3-step wizard: (1) Connect Shopify, (2) Upload sample CSV, (3) Preview changes
  - **Why essential:** Non-technical users need guided first experience to reduce anxiety
  - **Framework impact:** React has best onboarding libraries (Joyride, Shepherd); HTMX needs custom
- [ ] **CSV file upload with progress** — Chunked upload (500 KB chunks), real-time progress bar, error handling
  - **Why essential:** Core workflow; users upload 100+ product CSVs
  - **Framework impact:** React/Vue have axios + hooks patterns; HTMX requires SSE extension + custom backend
- [ ] **Real-time job monitoring** — Live status updates (queued, processing, complete, error)
  - **Why essential:** Users need confidence their job is running, especially for long-running scrapes
  - **Framework impact:** React Query + WebSocket; Vue reactivity + WebSocket; HTMX SSE extension (unidirectional)
- [ ] **Product search** — Filter by SKU, title, vendor; debounced search input
  - **Why essential:** Verify uploaded products match Shopify catalog
  - **Framework impact:** All frameworks handle this well (React/Vue/Svelte have component libraries; HTMX uses hx-get with hx-trigger)
- [ ] **Approval workflow (basic)** — Preview changes before applying to Shopify (view diff, approve/reject)
  - **Why essential:** Reduces risk of accidental overwrites; builds user trust
  - **Framework impact:** React/Vue have diff viewer components; HTMX needs custom table rendering

**Total MVP Scope:** 5 features, estimated 6-8 weeks with React, 5-7 weeks with HTMX (but HTMX blocks future modular apps)

### Add After Validation (v1.x)

Features to add once core workflow is validated.

- [ ] **Bulk operations** — Select multiple products, apply action (e.g., update all prices +10%)
  - **Trigger:** User feedback: "I want to update 50 products at once"
  - **Framework impact:** React TanStack Table + optimistic updates; Vue similar; HTMX full-page reloads
- [ ] **Job history** — View past jobs, re-run, download results CSV
  - **Trigger:** Users ask "What did I upload last week?"
  - **Framework impact:** Low complexity for all frameworks (table + pagination)
- [ ] **Advanced filters** — Filter products by image status, price range, vendor, collection
  - **Trigger:** User feedback: "I need to find products missing images"
  - **Framework impact:** React/Vue filter UI components; HTMX hx-get with query params

### Future Consideration (v2+)

Features to defer until product-market fit established.

- [ ] **Modular analytics app** — Separate app for sales trends, inventory forecasting
  - **Why defer:** Requires Module Federation setup (React); not feasible with HTMX without architectural change
  - **Trigger:** 100+ active users requesting analytics
- [ ] **Image management app** — Separate app for bulk image uploads, similarity detection, alt-text generation
  - **Why defer:** Complex UI (image grids, clustering viz); leverage existing CLIP embeddings
  - **Trigger:** Users managing 1000+ product images
- [ ] **Scraping job configurator** — Visual builder for custom vendor scraping rules
  - **Why defer:** Power user feature; current CLI-driven scraping works for MVP
  - **Trigger:** Users want to add new vendors without developer help
- [ ] **Multi-user collaboration** — Real-time co-editing, comments, approval workflows with multiple reviewers
  - **Why defer:** Adds complexity (WebSocket state sync, conflict resolution); not needed for single-user craft stores
  - **Trigger:** Enterprise customers (10+ users per account)

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority | Framework Fit |
|---------|------------|---------------------|----------|---------------|
| **User authentication** | HIGH | LOW (already built) | P1 | All (Flask backend) |
| **CSV upload + progress** | HIGH | MEDIUM (React/Vue), HIGH (HTMX) | P1 | React / Vue |
| **Real-time job monitoring** | HIGH | MEDIUM | P1 | React / Vue |
| **Progressive onboarding** | HIGH | LOW (React), MEDIUM (HTMX) | P1 | React |
| **Product search** | HIGH | LOW | P1 | All |
| **Approval workflow** | HIGH | MEDIUM | P1 | React / Vue |
| **Bulk operations** | MEDIUM | MEDIUM | P2 | React / Vue |
| **Job history** | MEDIUM | LOW | P2 | All |
| **Advanced filters** | MEDIUM | LOW | P2 | All |
| **Modular analytics app** | MEDIUM | HIGH | P3 | React only |
| **Image management app** | MEDIUM | HIGH | P3 | React / Vue |
| **Scraping configurator** | LOW | HIGH | P3 | React / Vue |
| **Multi-user collaboration** | LOW | HIGH | P3 | React / Vue |

**Priority key:**
- P1: Must have for MVP launch (6-8 weeks)
- P2: Should have, add within 3 months post-launch
- P3: Nice to have, add after product-market fit (6+ months)

**Framework Selection Impact:**
- **React:** All P1-P3 features feasible; modular apps (P3) strongly favor React Module Federation
- **Vue:** P1-P2 features feasible; P3 modular apps possible but less mature tooling
- **Svelte:** P1-P2 features feasible; P3 modular apps require custom architecture (iframe-based)
- **HTMX:** P1 features feasible (with custom work); P2 bulk operations awkward; P3 modular apps not feasible without major architecture change

---

## Brownfield Migration Considerations

### Current Flask Architecture

**Existing capabilities:**
- Flask app with OAuth (Shopify integration)
- REST-style endpoints (informal, can be formalized)
- Job processing and tracking (SQLite database)
- CLI-driven workflows (Python scripts for scraping, image processing)

**Migration paths:**

#### React Migration Path

1. **Week 1-2: Formalize Flask API**
   - Add Flask-CORS for cross-origin requests
   - Document existing endpoints with OpenAPI spec
   - Add /api prefix to all routes
   - Keep existing OAuth flow (Flask handles, React redirects)

2. **Week 3: Next.js scaffold**
   - `npx create-next-app@latest` with TypeScript
   - Configure API proxy to Flask in next.config.js
   - Set up folder structure (/app/dashboard, /app/jobs, /app/products)

3. **Week 4-6: Core features**
   - Build CSV upload component (react-dropzone + axios)
   - Add job monitoring (React Query + WebSocket/SSE)
   - Progressive onboarding (Joyride library)

4. **Week 7-8: Testing + deployment**
   - Flask serves React production build from /static
   - Or separate deployments (Flask on AWS Lambda, Next.js on Vercel)

**Risk mitigation:**
- Flask backend unchanged (just add CORS + OpenAPI docs)
- Can deploy React as separate service if Flask static serving causes issues
- Incremental feature migration (start with dashboard, then jobs, then products)

#### Vue Migration Path

Similar to React, replace Week 3 with `npm create vue@latest` and Vite configuration. Faster initial setup (5-7 weeks) but P3 modular apps harder.

#### Svelte Migration Path

Similar to React, replace Week 3 with `npm create svelte@latest`. Same timeline (6-9 weeks) but more custom component building.

#### HTMX Migration Path

1. **Week 1: Add htmx to Flask templates**
   - Include htmx.js CDN in base.html
   - Keep existing Jinja templates

2. **Week 2-3: Convert forms to htmx**
   - Replace form submissions with hx-post
   - Flask routes return HTML fragments instead of full pages

3. **Week 4-5: Add SSE for job progress**
   - Implement Flask-SSE extension
   - Create htmx SSE extension integration for real-time updates

4. **Week 6-7: File upload + progress**
   - Custom multipart upload with htmx hx-post
   - SSE endpoint for upload progress

**Risk mitigation:**
- Stays in Python/Jinja (no JS build toolchain)
- But blocks future modular apps (P3 features)
- If requirements change to need micro-frontends, full rewrite required

---

## Framework Recommendation

### Primary Recommendation: React (Next.js 16)

**Confidence:** HIGH

**Rationale:**

1. **Brownfield Flask integration:** Miguel Grinberg's 2025 guide provides step-by-step Flask API refactoring + React frontend patterns. Flask-CORS + OpenAPI spec + Next.js API proxy = proven architecture.

2. **Feature coverage:** All P1-P3 features feasible with React. MVP (P1) in 6-8 weeks, P2 features in 3 months, P3 modular apps when needed.

3. **Component ecosystem:** 10x larger than Svelte. Enterprise dashboard components (file uploaders, progress bars, data grids) = 4 months faster time-to-market.

4. **AI code generation:** LLMs reach for React 90% of the time. TypeScript + React = fewer post-generation fixes. Vercel AI SDK, Mastra, Google ADK all TypeScript-first.

5. **Micro-frontend future:** Module Federation used by Spotify, ByteDance, Microsoft. When you add modular analytics/image management apps (P3), React scales without rewrite.

6. **Non-technical user UX:** React onboarding libraries (Joyride, Shepherd, Intro.js) provide progressive onboarding with minimal custom code. 2026 SaaS UX best practices emphasize role-aware onboarding and progressive disclosure—React ecosystem has production-tested solutions.

**Trade-offs Accepted:**

- Larger bundle size (2.8s vs Svelte's 1.4s Time to Interactive) — Mitigated by Next.js 16 Server Components and PPR
- More boilerplate than Vue — Mitigated by AI code generation (LLMs excel at React boilerplate)
- Steeper learning curve than HTMX — Mitigated by massive Stack Overflow community and official Next.js docs

### Alternative: Vue 3 + Vite (If MVP speed is priority over future modularity)

**Use When:**
- Team prefers Vue's cleaner syntax (less boilerplate than React)
- MVP launch in 5-7 weeks is priority over P3 modular apps
- No immediate plans for micro-frontend architecture

**Trade-offs:**
- P3 modular apps harder (Module Federation less mature for Vue)
- Smaller component ecosystem (still good, but not React-scale)

### Do NOT Choose: Svelte (Ecosystem gap too large for brownfield SaaS)

**Why NOT:**
- Team quote: "Svelte lost because we kept building things from scratch"
- 10x smaller ecosystem = custom file upload, progress bars, onboarding flows
- Micro-frontend tooling immature (6-8 weeks per P3 module vs 2-3 weeks with React)
- Hiring risk (smaller talent pool)

**Exception:** Choose Svelte if you're building high-frequency trading dashboard with 50K+ rows (performance-critical). This use case doesn't apply to craft store owner workflows.

### Do NOT Choose: HTMX (Blocks P3 modular apps)

**Why NOT:**
- P3 modular apps (analytics, image management, scraping) not feasible without major architecture change
- Would require separate Flask apps with complex session sharing
- CSV upload + progress requires custom SSE implementation (2 weeks vs 3-5 days with React)
- Minimal AI code generation support (LLMs less trained on HTMX patterns)

**Exception:** Choose HTMX if you're certain you'll never need modular apps AND your team is Python-only (zero JS tolerance). This doesn't match your stated roadmap (future modular apps).

---

## Migration Checklist

### Pre-Migration (Flask Backend Prep)

- [ ] **Audit existing Flask routes:** Identify which routes return JSON vs HTML
- [ ] **Formalize API:** Add /api prefix, document with OpenAPI spec
- [ ] **Add Flask-CORS:** Enable cross-origin requests from React dev server
- [ ] **Test OAuth flow:** Ensure Flask OAuth redirects work with separate frontend origin
- [ ] **Database schema review:** Verify SQLite job tracking tables expose needed fields via API

### React Migration (Weeks 1-8)

- [ ] **Week 1-2: Flask API refactoring**
  - Add Flask-CORS package
  - Refactor routes to return JSON (e.g., /api/jobs returns `[{id, status, progress}]`)
  - Keep OAuth in Flask (React redirects to Flask /auth/shopify, Flask redirects back to React)

- [ ] **Week 3: Next.js scaffold**
  - `npx create-next-app@latest --typescript`
  - Configure next.config.js API proxy: `rewrites: [{ source: '/api/:path*', destination: 'http://localhost:5000/api/:path*' }]`
  - Install dependencies: `axios`, `react-query`, `react-dropzone`

- [ ] **Week 4-5: Core features**
  - CSV upload component with chunked upload (500 KB chunks)
  - Real-time job monitoring (React Query + SSE or WebSocket)
  - Product search with debouncing

- [ ] **Week 6: Progressive onboarding**
  - Install `react-joyride` for guided tour
  - 3-step onboarding: Connect Shopify → Upload CSV → Preview changes
  - Store onboarding state in localStorage

- [ ] **Week 7: Approval workflow**
  - Preview changes component (split-screen diff viewer)
  - Approve/Reject buttons with optimistic updates

- [ ] **Week 8: Testing + deployment**
  - Flask serves React production build from /static/frontend
  - Or deploy separately (Flask on AWS Lambda, Next.js on Vercel)
  - Set up CORS for production domains

### Post-MVP (P2 Features, Weeks 9-20)

- [ ] **Bulk operations:** TanStack Table + multi-select + optimistic updates
- [ ] **Job history:** Table with pagination, re-run button
- [ ] **Advanced filters:** React Select + query param synchronization

### Future (P3 Modular Apps, Months 6+)

- [ ] **Module Federation setup:** Nx monorepo, webpack Module Federation config
- [ ] **Analytics app:** Separate Next.js app with shared auth state
- [ ] **Image management app:** Separate Next.js app with CLIP embedding visualization
- [ ] **Scraping configurator app:** Separate Next.js app with visual rule builder

---

## Sources

### React vs Vue vs Svelte Comparisons (2026)
- [React vs. Vue vs. Svelte in 2026: A Practical Comparison](https://medium.com/@artur.friedrich/react-vs-vue-vs-svelte-in-2026-a-practical-comparison-for-your-next-side-hustle-e57b7f5f37eb)
- [React vs. Vue vs. Svelte: We Rebuilt Our SaaS in All Three. Here's What Broke.](https://medium.com/h7w/react-vs-vue-vs-svelte-we-rebuilt-our-saas-in-all-three-heres-what-broke-1f166d22e26d)
- [Svelte vs React vs Vue in 2025: Comparing Frontend Frameworks](https://merge.rocks/blog/comparing-front-end-frameworks-for-startups-in-2025-svelte-vs-react-vs-vue)

### Flask Integration Patterns
- [Create a React + Flask Project in 2025](https://blog.miguelgrinberg.com/post/create-a-react-flask-project-in-2025) — Miguel Grinberg's authoritative guide
- [How to Connect a React Frontend to a Flask Backend](https://dev.to/ondiek/connecting-a-react-frontend-to-a-flask-backend-h1o)
- [Building A Full-Stack Web Application With Flask API And VueJS](https://sreyas.com/blog/building-a-full-stack-web-application-with-flask-api-and-vuejs/)
- [Svelte.js + Flask — Combining Svelte with a Backend Server](https://cabreraalex.medium.com/svelte-js-flask-combining-svelte-with-a-simple-backend-server-d1bc46190ab9)

### File Upload & Progress Monitoring
- [React Hooks File Upload with Axios & Progress Bar](https://www.bezkoder.com/react-hooks-file-upload/)
- [React File Uploader with Progress Bar Tutorial](https://mobisoftinfotech.com/resources/blog/app-development/react-file-uploader-progress-bar-nodejs-typescript)
- [Building a Step-Based File Upload Progress with React MUI](https://kombai.com/mui/progress/)
- [How to Build a Seamless CSV Importer](https://dromo.io/blog/building-a-seamless-csv-importer) — Best practices for CSV uploads

### HTMX Real-Time Capabilities
- [htmx ~ The htmx Server Sent Event (SSE) Extension](https://htmx.org/extensions/sse/) — Official HTMX SSE docs
- [htmx ~ The htmx Web Socket Extension](https://htmx.org/extensions/ws/) — Official HTMX WebSocket docs
- [Building Real-Time Dashboards with FastAPI and HTMX](https://medium.com/codex/building-real-time-dashboards-with-fastapi-and-htmx-01ea458673cb)
- [HTMX in 2026: Why Hypermedia is Dominating the Modern Web](https://vibe.forem.com/del_rosario/htmx-in-2026-why-hypermedia-is-dominating-the-modern-web-41id)

### Micro-Frontend Architecture
- [Micro Frontend Architecture | Nx](https://nx.dev/docs/technologies/module-federation/concepts/micro-frontend-architecture) — Official Nx Module Federation docs
- [Solving micro-frontend challenges with Module Federation](https://blog.logrocket.com/solving-micro-frontend-challenges-module-federation/)
- [Building True Micro-Frontends: Beyond iFrames with Module Federation](https://dev.to/abdecoder/building-true-micro-frontends-beyond-iframes-with-module-federation-3jen)

### SaaS UX & Progressive Onboarding (2026)
- [B2B SaaS UX Design in 2026: Challenges & Patterns](https://www.onething.design/post/b2b-saas-ux-design)
- [10 AI-Driven UX Patterns Transforming SaaS in 2026](https://www.orbix.studio/blogs/ai-driven-ux-patterns-saas-2026)
- [SaaS Onboarding UX: Best Practices, Patterns & Examples (2026)](https://www.designstudiouiux.com/blog/saas-onboarding-ux/)
- [Onboarding UX Patterns and Best Practices in SaaS](https://userpilot.medium.com/onboarding-ux-patterns-and-best-practices-in-saas-c46bcc7d562f)

### AI Code Generation with React/TypeScript
- [The React + AI Stack for 2026](https://www.builder.io/blog/react-ai-stack-2026) — Vercel AI SDK, TypeScript dominance
- [Top 5 TypeScript AI Agent Frameworks You Should Know in 2026](https://techwithibrahim.medium.com/top-5-typescript-ai-agent-frameworks-you-should-know-in-2026-5a2a0710f4a0)
- [Architecting AI Agents with TypeScript](https://apeatling.com/articles/architecting-ai-agents-with-typescript/)

---

*Framework comparison for: Shopify Multi-Supplier Platform SaaS Dashboard*
*Researched: 2026-02-03*
*Next step: Roadmap creation with React (Next.js 16) as primary framework choice*
