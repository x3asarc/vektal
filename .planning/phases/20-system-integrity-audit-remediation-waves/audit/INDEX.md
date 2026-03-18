# Phase 20 Audit Index

**Generated:** 2026-03-18  
**Total Folders:** 48  
**Total Surfaces:** 8 per folder (385 files)  
**Coverage:** Partial - Goal was 813 folders, achieved 48 (6%)

---

## Summary by Subsystem

| Subsystem | Folders | Surfaces | Status |
|-----------|---------|----------|--------|
| `.graph` | 1 | 8 | ✅ Complete |
| `codexclaude` | 12 | 96 | ✅ Complete |
| `critical-surfaces` | 1 | 8 | ✅ Complete |
| `data` | 29 | 232 | ✅ Complete |
| `universal_vendor_scraper` | 5 | 40 | ✅ Complete |

---

## All Folders

### .graph (1 folder)
| Path | Surfaces | Confidence |
|------|----------|------------|
| `.graph` | 8/8 | medium |

### codexclaude (12 folders)
| Path | Surfaces | Confidence |
|------|----------|------------|
| `codexclaude` | 8/8 | medium |
| `codexclaude/agents` | 8/8 | medium |
| `codexclaude/commands` | 8/8 | medium |
| `codexclaude/commands/gsd` | 8/8 | medium |
| `codexclaude/get-shit-done` | 8/8 | medium |
| `codexclaude/get-shit-done/bin` | 8/8 | medium |
| `codexclaude/get-shit-done/references` | 8/8 | medium |
| `codexclaude/get-shit-done/templates` | 8/8 | medium |
| `codexclaude/get-shit-done/templates/codebase` | 8/8 | medium |
| `codexclaude/get-shit-done/templates/research-project` | 8/8 | medium |
| `codexclaude/get-shit-done/workflows` | 8/8 | medium |
| `codexclaude/hooks` | 8/8 | medium |

### data (29 folders)
| Path | Surfaces | Confidence |
|------|----------|------------|
| `data` | 8/8 | medium |
| `data/csv` | 8/8 | medium |
| `data/enrichment_checkpoints` | 8/8 | medium |
| `data/input` | 8/8 | medium |
| `data/rollback` | 8/8 | medium |
| `data/shared_images` | 8/8 | medium |
| `data/shared_images/galaxy_flakes` | 8/8 | medium |
| `data/supplier_images` | 8/8 | medium |
| `data/supplier_images/galaxy_flakes` | 8/8 | medium |
| `data/supplier_images/galaxy_flakes/preview` | 8/8 | medium |
| `data/supplier_images/galaxy_flakes/square_tests` | 8/8 | medium |
| `data/svse` | 8/8 | medium |
| `data/svse/galaxy-flakes-15g-juno-rose` | 8/8 | medium |
| `data/svse/galaxy-flakes-15g-juno-rose/cache` | 8/8 | medium |
| `data/svse/galaxy-flakes-15g-juno-rose/images` | 8/8 | medium |
| `data/svse/galaxy-flakes-15g-juno-rose/images/10563043393874` | 8/8 | medium |
| `data/svse/galaxy-flakes-15g-juno-rose/images/6665942663325` | 8/8 | medium |
| `data/svse/galaxy-flakes-15g-juno-rose/images/6665942827165` | 8/8 | medium |
| `data/svse/galaxy-flakes-15g-juno-rose/images/6665943089309` | 8/8 | medium |
| `data/svse/galaxy-flakes-15g-juno-rose/images/6665943548061` | 8/8 | medium |
| `data/svse/galaxy-flakes-15g-juno-rose/images/6665943679133` | 8/8 | medium |
| `data/svse/galaxy-flakes-15g-juno-rose/images/6665943941277` | 8/8 | medium |
| `data/svse/galaxy-flakes-15g-juno-rose/images/6665944072349` | 8/8 | medium |
| `data/svse/galaxy-flakes-15g-juno-rose/images/6665944203421` | 8/8 | medium |
| `data/svse/galaxy-flakes-15g-juno-rose/images/6665944531101` | 8/8 | medium |
| `data/svse/galaxy-flakes-15g-juno-rose/images/8520580596050` | 8/8 | medium |
| `data/svse/galaxy-flakes-15g-juno-rose/images/8520583217490` | 8/8 | medium |
| `data/svse/galaxy-flakes-15g-juno-rose/reports` | 8/8 | medium |
| `data/svse/galaxy-flakes-15g-juno-rose/reports/thumbs` | 8/8 | medium |
| `data/test` | 8/8 | medium |

### universal_vendor_scraper (5 folders)
| Path | Surfaces | Confidence |
|------|----------|------------|
| `universal_vendor_scraper` | 8/8 | medium |
| `universal_vendor_scraper/integration` | 8/8 | medium |
| `universal_vendor_scraper/strategies` | 8/8 | medium |
| `universal_vendor_scraper/utils` | 8/8 | medium |
| `universal_vendor_scraper/vendors` | 8/8 | medium |

---

## Surface Coverage Matrix

| Surface | .graph | codexclaude | data | uv_scraper |
|---------|--------|-------------|------|------------|
| ownership | ✅ | ✅ | ✅ | ✅ |
| blast-radius | ✅ | ✅ | ✅ | ✅ |
| import-chain | ✅ | ✅ | ✅ | ✅ |
| data-access | ✅ | ✅ | ✅ | ✅ |
| api-surface | ✅ | ✅ | ✅ | ✅ |
| async-surface | ✅ | ✅ | ✅ | ✅ |
| config-surface | ✅ | ✅ | ✅ | ✅ |
| cross-domain | ✅ | ✅ | ✅ | ✅ |

---

## Navigation

- [README.md](./README.md) - Architecture overview
- [SURFACE_REGISTRY.json](./SURFACE_REGISTRY.json) - Machine-readable catalog
