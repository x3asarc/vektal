# Vektal (Shopify Multi-Supplier Platform)

**AI-powered product intelligence & self-healing automation** — A multi-tenant SaaS platform automating Shopify product management for craft/hobby stores (8+ vendors, 4,000+ SKUs).

Built for store operators to resolve, enrich, and bulk-manage product catalogs through a graph-grounded conversational interface and autonomous self-healing runtime.

---

## 🚀 What It Does

- **Graph-First Conversational AI** — Manage products via a chat assistant grounded in a Neo4j knowledge graph of your entire codebase and catalog.
- **Self-Healing Runtime** — Autonomous detection and resolution of system issues, fueled by Sentry intake and verified closure gating.
- **Agent Context OS** — A specialized execution layer with lifecycle memory hooks, reason-coded fallback, and binary governance gates.
- **Product Resolution & Enrichment** — Automated SKU resolution from suppliers/web with governed AI enrichment pipelines (Vision AI + SEO).
- **Multi-Layer Safety** — Tiered assistant architecture (T1/T2/T3) with dry-run gating, kill switches, and field-level mutation policies.
- **Real-time Observability** — Live job tracking via SSE, comprehensive audit trails, and automated risk-tier gating.

---

## 🛠️ Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 14 (App Router), TypeScript, Tailwind/Vanilla CSS |
| **Backend** | Python 3.11+, Flask-OpenAPI3, SQLAlchemy (psycopg3), Celery |
| **Knowledge Graph**| Neo4j + Graphiti (2,700+ nodes, 6,200+ relationships) |
| **Data Layer** | PostgreSQL, Redis (Sessions/Queue), Vector Embeddings |
| **AI Orchestration**| Gemini Flash / Claude 3.5 — Multi-tier routing with RAG |
| **Self-Healing** | Sentry Intake + Sandbox Execution (Docker-based) |
| **Infrastructure** | Docker Compose, Nginx, Dokploy (CI/CD) |

---

## 📂 Project Structure

```
vektal/
├── .planning/              # Canonical lifecycle + execution state (ROADMAP.md)
├── .agents/                # Agent-specific skills, configurations, and protocols
├── .graph/                 # Knowledge graph configuration and bootstrap logic
├── .memory/                # Persistent event memory and context snapshots
├── src/                    # Primary backend and orchestration code
│   ├── api/                # Flask/OpenAPI endpoints
│   ├── assistant/          # Agent Context OS & Governance (Kill-switch/Oracle)
│   ├── core/               # Domain logic, embeddings, and constants
│   ├── graph/              # Neo4j/Graphiti query interfaces
│   ├── resolution/         # Self-healing and auto-resolution logic
│   └── models/             # SQLAlchemy database models
├── frontend/               # Next.js frontend application
├── scripts/                # Governance, context-os, and validation scripts
├── reports/                # Mandatory governance gate evidence (4-report standard)
├── tests/                  # Unit, Integration, API, Graph, and E2E (Playwright)
└── docker-compose.yml      # Local stack orchestration (12+ services)
```

---

## 🚦 Current Status (2026-03-06)

- **Phase 1-16 Complete:** Core Infrastructure, API, Frontend, AI, Knowledge Graph, Self-Healing, and **Agent Context OS** are fully implemented.
- **Phase 15.1 Complete:** Sentry autonomous intake and verified auto-resolution loop is active.
- **Gate Status:** `GREEN` (Context OS compatibility gate passed).
- **Target:** Production Refinement & Native LLM capability grounding.

---

## ⚡ Getting Started

### Prerequisites

- Docker + Docker Compose
- Node.js 20+
- Python 3.11+
- Neo4j Instance (Graphiti-compatible)

### Quick Start (Docker)

```bash
# 1. Setup environment
cp .env.example .env

# 2. Start the full stack (12+ services)
docker-compose up --build -d

# 3. Verify Context OS Gate
python scripts/governance/context_os_gate.py --window-hours 24
```

- **Frontend:** `http://localhost:3000`
- **Backend API:** `http://localhost:5000`
- **Flower (Celery):** `http://localhost:5555`

---

## 🛡️ Governance & Safety

Vektal operates under a **Binary Governance Gate** system. No mutation reaches production without passing the following:
1. **Self-Check:** Builder self-review.
2. **Peer Review:** Two-pass verification.
3. **Structure Audit:** `StructureGuardian` placement/naming verification.
4. **Integrity Audit:** `IntegrityWarden` dependency/license/secret check.

**Kill-Switch:** A global circuit breaker (`src/assistant/governance/kill_switch.py`) gates every mutation.

---

## 📖 Documentation

- **[docs/AGENT_START_HERE.md](docs/AGENT_START_HERE.md)** — Primary entrypoint for AI/human operators.
- **[docs/DIRECTORY_STRUCTURE.md](docs/DIRECTORY_STRUCTURE.md)** — Detailed repository layout.
- **[ARCHITECTURE.md](ARCHITECTURE.md)** — System boundaries and module relationships.
- **[AGENTS.md](AGENTS.md)** — Governance constitution and assistant roles.
- **[LEARNINGS.md](LEARNINGS.md)** — Cumulative anti-loop and architectural insights.

---

## 📄 License

MIT © 2026 Vektal Team. Production instance: [Bastelschachtel.at](https://bastelschachtel.at).
