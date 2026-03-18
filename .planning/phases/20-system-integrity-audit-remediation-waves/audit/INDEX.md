# Phase 20 Amendment Audit Index

**Generated:** 2026-03-18  
**Phase:** 20-system-integrity-audit-remediation-waves (AMENDMENT)  
**Total Units:** 22  
**Total Surfaces:** 8 per unit (176 files)  
**Coverage:** Complete - 100% of defined scope

---

## Summary

| Category | Units | Surfaces | Status |
|----------|-------|----------|--------|
| Core Application | 12 | 96 | ✅ Complete |
| Configuration & Data | 3 | 24 | ✅ Complete |
| Testing | 1 | 8 | ✅ Complete |
| Documentation & Operations | 5 | 40 | ✅ Complete |
| Agent Frameworks | 1 | 8 | ✅ Complete |
| **TOTAL** | **22** | **176** | **✅ Complete** |

---

## All Units

### Core Application (12 units)

| # | Path | Surfaces | Confidence |
|---|------|----------|------------|
| 1 | `src/core/` | 8/8 | high |
| 2 | `src/` | 8/8 | high |
| 3 | `src/api/` | 8/8 | high |
| 4 | `src/jobs/` | 8/8 | high |
| 5 | `src/graph/` | 8/8 | high |
| 6 | `src/memory/` | 8/8 | high |
| 7 | `src/auth/` | 8/8 | high |
| 8 | `src/billing/` | 8/8 | high |
| 9 | `src/integrations/` | 8/8 | medium |
| 10 | `universal_vendor_scraper/` | 8/8 | high |
| 11 | `frontend/` | 8/8 | high |
| 12 | `seo/` | 8/8 | high |

### Configuration & Data (3 units)

| # | Path | Surfaces | Confidence |
|---|------|----------|------------|
| 13 | `config/` | 8/8 | high |
| 14 | `data/` | 8/8 | medium |
| 15 | `utils/` | 8/8 | high |

### Testing (1 unit)

| # | Path | Surfaces | Confidence |
|---|------|----------|------------|
| 16 | `tests/` | 8/8 | high |

### Documentation & Operations (5 units)

| # | Path | Surfaces | Confidence |
|---|------|----------|------------|
| 17 | `docs/` | 8/8 | medium |
| 18 | `ops/` | 8/8 | medium |
| 19 | `scripts/` | 8/8 | medium |
| 20 | `reports/` | 8/8 | medium |
| 21 | `migrations/` | 8/8 | high |

### Agent Frameworks (1 unit - combined)

| # | Path | Surfaces | Confidence |
|---|------|----------|------------|
| 22 | `agent-frameworks/` | 8/8 | medium |

> Agent Frameworks combines: `.agents/`, `.claude/`, `.codex/`, `.gemini/`, `.letta/`

---

## Surface Coverage Matrix

| Surface | Core (12) | Config (3) | Tests (1) | Ops (5) | Agents (1) |
|---------|------------|-------------|------------|----------|------------|
| ownership | ✅ | ✅ | ✅ | ✅ | ✅ |
| blast-radius | ✅ | ✅ | ✅ | ✅ | ✅ |
| import-chain | ✅ | ✅ | ✅ | ✅ | ✅ |
| data-access | ✅ | ✅ | ✅ | ✅ | ✅ |
| api-surface | ✅ | ✅ | ✅ | ✅ | ✅ |
| async-surface | ✅ | ✅ | ✅ | ✅ | ✅ |
| config-surface | ✅ | ✅ | ✅ | ✅ | ✅ |
| cross-domain | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## Previous Audit (Phase 20 Original)

- **Original Goal:** 813 folders
- **Original Achievement:** 48 folders (6%)
- **Amendment Goal:** 22 logical units
- **Amendment Achievement:** 22 units × 8 surfaces = 176 files (100%)

---

## Navigation

- [README.md](./README.md) - Architecture overview
- [SURFACE_REGISTRY.json](./SURFACE_REGISTRY.json) - Machine-readable catalog
