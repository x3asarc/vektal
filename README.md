# Synthex

**AI-powered product intelligence platform** — conversational interface for managing Shopify product catalogs at scale.

Built for store operators who need to resolve, enrich, and bulk-manage product data through natural language instead of manual workflows.

---

## What It Does

- **Conversational AI** — chat with an AI assistant to add, update, or bulk-import products
- **Product Resolution** — resolve SKUs from supplier data or the web automatically
- **Enrichment Engine** — governed AI enrichment pipeline with quality gates and audit trails
- **Real-time Job Tracking** — live progress on background jobs via SSE streaming
- **Search & Discovery** — search your product catalog with filters and snapshots
- **Dry-run Reviews** — preview changes before applying them to your Shopify store

---

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16 (App Router), React 19, TypeScript 5 |
| Styling | Pure CSS custom properties, Material Symbols icons |
| State | Zustand (client), TanStack React Query (server) |
| Backend | Python / Flask, SQLAlchemy, Celery |
| Database | PostgreSQL with Alembic migrations |
| Queue | Redis + Celery workers |
| AI | Claude (Anthropic) — multi-tier routing (T1/T2/T3) |
| Auth | OAuth + email verification |
| Infra | Docker Compose, Nginx reverse proxy |

---

## Project Structure

```
synthex/
├── frontend/               # Next.js app
│   └── src/
│       ├── app/            # Route pages (App Router)
│       ├── features/       # Feature modules (chat, jobs, search, enrichment)
│       └── shell/          # AppShell, Sidebar, providers
├── src/                    # Python backend
│   ├── api/                # Flask API (v1 routes)
│   ├── assistant/          # AI tier routing + governance
│   ├── resolution/         # Product resolution engine
│   ├── jobs/               # Job orchestration + Celery tasks
│   └── models/             # SQLAlchemy models
├── migrations/             # Alembic DB migrations
├── nginx/                  # Nginx config
├── docker-compose.yml
└── .planning/              # GSD roadmap + phase plans
```

---

## Getting Started

### Prerequisites

- Docker + Docker Compose
- Node.js 20+
- Python 3.11+

### Run with Docker

```bash
docker-compose up --build
```

Frontend → `http://localhost:3000`
Backend API → `http://localhost:5000`

### Run Frontend Locally

```bash
cd frontend
npm install
npm run dev
```

### Run Backend Locally

```bash
pip install -r requirements.txt
python src/app.py
```

---

## Key Features

### Dashboard
Dark-theme AI chat home — starter cards, quick-action pills, and a full-width chat composer with Attach, Deep Search, and Generate Image tools.

### Chat Interface
Real-time streaming AI responses via SSE. Supports single SKU queries, bulk imports, and inline action approvals with delegation traces.

### Enrichment Workspace
Governed enrichment pipeline with oracle signal verification, quality gates, field-level policies, and dry-run compilation before any data is applied.

### Job Tracker
Live job status with progress bars, retry logic, and terminal notifications. Supports cancellation and priority queuing.

---

## Architecture Highlights

- **Multi-tier AI routing** — T1 (fast/cheap) → T2 (capable) → T3 (heavy) with automatic fallback
- **Governed enrichment** — field-level policies, kill switches, and audit checkpoints at every step
- **Idempotent job execution** — all jobs are safe to retry with deduplication
- **Contract tests** — API contracts validated independently of implementation
- **Observability** — instrumentation signals, correlation IDs, and canary gates

---

## License

MIT
