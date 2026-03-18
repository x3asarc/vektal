# Phase 20: System Integrity Audit - Research

**Synthesized:** 2026-03-18
**Domain:** Codebase audit methodology, 8-surface deep analysis, automation strategies
**Confidence:** HIGH
**From:** 20-RESEARCH-core.md + 20-RESEARCH-deep.md

---

## User Constraints (LOCKED - Non-Negotiable)

Copied verbatim from 20-CONTEXT.md:

1. **22 logical audit units** — src/core/, src/, src/api/, src/jobs/, src/graph/, src/memory/, src/auth/, src/billing/, src/integrations/, universal_vendor_scraper/, frontend/, seo/, config/, data/, utils/, tests/, docs/, ops/, scripts/, reports/, migrations/, agent-frameworks
2. **All 8 surfaces per unit** — ownership, blast-radius, import-chain, data-access, api-surface, async-surface, config-surface, cross-domain
3. **Deep analysis** — full dependency graphs, cross-domain coupling maps, depth-3 blast-radius
4. **176 JSON files output** — 22 units × 8 surfaces
5. **tests/ as 1 logical unit** — all subdirs included (unit, integration, e2e, graph, daemons, planning)
6. **Agent frameworks combined** — .agents/, .claude/, .codex/, .gemini/, .letta/ as 1 unit

---

## Executive Summary

Phase 20 amendment requires comprehensive codebase audit for 22 folders across 8 surfaces. The existing Phase 20 audit achieved 48 folders (6%) with inconsistent surface coverage. This amendment targets 22 logical units with complete 8-surface deep analysis.

**Codebase Composition:**
- Python (Flask, Celery, SQLAlchemy): ~75%
- TypeScript/JavaScript (Next.js, React): ~20%
- JavaScript (Playwright scrapers): ~5%

**Technical Patterns Detected:**
- 12+ Celery tasks across 8 files
- 14+ Flask REST endpoints
- 178+ environment variable references
- Complex cross-domain coupling between graph, memory, and jobs systems

**Primary Recommendation:** Use existing JSON schema as canonical template, implement batch processing to iterate through 22 units with parallel surface analysis.

---

## Standard Stack

### Analysis Tools
| Tool | Purpose | Why Standard |
|------|---------|--------------|
| glob | File enumeration | Native to workspace |
| grep | Content search | Native to workspace, regex support |
| Read | File content extraction | Native to workspace |
| Python ast | Python import parsing | Standard library |
| neo4j (existing) | Graph dependency storage | Already integrated |

### JSON Schema (Canonical from existing artifacts)
```json
{
  "folder_path": "unit-name",
  "generated_at": "ISO timestamp",
  "coverage": {
    "evidence_source": ["filesystem-enumeration", "neo4j-bulk-snapshot"],
    "graph_backed": true,
    "filesystem_backed": true,
    "coverage_confidence": "high",
    "contract_satisfied": true,
    "known_blind_spots": [],
    "canonical_prefix": "unit-name",
    "matched_file_count": N
  },
  "summary": { ... }
}
```

### Surface Extraction Methods
| Surface | Extraction | Automation |
|---------|-----------|------------|
| ownership | git blame + file headers | Semi |
| blast-radius | Import chain + depth-3 traversal | Automated |
| import-chain | AST parsing | Automated |
| data-access | Model inspection | Automated |
| api-surface | Flask decorator parsing | Automated |
| async-surface | Celery decorator parsing | Automated |
| config-surface | env var grep + YAML | Automated |
| cross-domain | Graph + cross-prefix analysis | Semi |

---

## 22 Logical Audit Units

| # | Unit | Key Content | Framework |
|---|------|-------------|-----------|
| 1 | src/core/ | Pipeline, scraping, vision, image | Python |
| 2 | src/ | Root modules: app, celery, database, models | Python |
| 3 | src/api/ | REST API endpoints | Python/Flask |
| 4 | src/jobs/ | Celery orchestrator, dispatcher | Python/Celery |
| 5 | src/graph/ | MCP server, sentry ingestion, sandbox | Python |
| 6 | src/memory/ | Memory manager, event log | Python |
| 7 | src/auth/ | OAuth, login, email verification | Python/Flask |
| 8 | src/billing/ | Stripe checkout, subscriptions | Python/Flask |
| 9 | src/integrations/ | Perplexity client | Python |
| 10 | universal_vendor_scraper/ | JS scrapers, strategies | JavaScript |
| 11 | frontend/ | Next.js/React, components, features | TypeScript |
| 12 | seo/ | SEO generator, prompts, validator | Python |
| 13 | config/ | YAML vendor/image/quality rules | YAML |
| 14 | data/ | Logs, CSV exports, vision cache | Mixed |
| 15 | utils/ | shopify_utils, pentart_db | Python |
| 16 | tests/ | unit, integration, e2e, graph, daemons | Python |
| 17 | docs/ | Guides, phase-reports | Markdown |
| 18 | ops/ | Governance, scripts | Mixed |
| 19 | scripts/ | Deployment, debug, checkpoints | Python/Shell |
| 20 | reports/ | Phase reports | Markdown |
| 21 | migrations/ | Alembic DB migrations | Python |
| 22 | agent-frameworks/ | Skills, agents, hooks, settings | YAML/MD |

---

## Architecture Patterns

### Pattern 1: Batch Surface Analyzer
```python
UNITS = ["src/core", "src", "src/api", "src/jobs", "src/graph",
         "src/memory", "src/auth", "src/billing", "src/integrations",
         "universal_vendor_scraper", "frontend", "seo", "config",
         "data", "utils", "tests", "docs", "ops", "scripts",
         "reports", "migrations", "agent-frameworks"]

SURFACES = ["ownership", "blast-radius", "import-chain",
            "data-access", "api-surface", "async-surface",
            "config-surface", "cross-domain"]
```

### Pattern 2: Depth-3 Blast-Radius
```json
{
  "file": "src/core/pipeline.py",
  "blast_radius": {
    "depth_1": ["src/core/enrichment/pipeline.py"],
    "depth_2": ["src/core/enrichment/generators/description.py"],
    "depth_3": ["src/core/enrichment/templating/engine.py"]
  }
}
```

### Pattern 3: Cross-Domain Coupling Map
```json
{
  "coupling_matrix": {
    "src/core": {
      "imports_from": ["src", "src/api"],
      "called_by": ["src/jobs", "src/api"],
      "references": ["src/memory", "src/graph"]
    }
  }
}
```

---

## Common Pitfalls

### Pitfall 1: Incomplete Unit Coverage
- **Prevention:** Use 22-unit checklist, verify each exists with glob
- **Warning:** Final count ≠ 176 JSON files

### Pitfall 2: Surface Data Mismatch
- **Prevention:** Compute matched_files once per unit, inject into all 8 surfaces
- **Warning:** Same file in different surfaces with different counts

### Pitfall 3: Cross-Domain Blindness
- **Prevention:** Filter import chains for different prefixes
- **Warning:** cross-domain shows zero references when coupling exists

### Pitfall 4: Shallow Blast-Radius
- **Prevention:** Recursive depth-first traversal to max depth 3
- **Warning:** blast-radius.json missing depth_2_reach

---

## Implementation Playbooks

### Celery Task Extraction
```bash
grep -rn "@app.task" src/ --include="*.py" | sed 's/.*@app\.task\([^)]*\).*name="\([^"]*\)".*/\2/'
```

### Flask API Extraction
```python
from src.app import app
routes = [{'endpoint': r.endpoint, 'methods': list(r.methods - {'HEAD', 'OPTIONS'}), 'path': str(r)}
          for r in app.url_map.iter_rules()]
```

### Cross-Domain Cypher Query
```cypher
MATCH (a)-[:IMPORTS|REFERENCES|CALLS]->(b)
WHERE a.file STARTS WITH 'src/'
  AND NOT b.file STARTS WITH 'src/'
RETURN a.file, b.file, type(r)
```

### Git Ownership Analysis
```bash
git log --format='%ae' -- src/core/ | head -10
git blame --line-porcelain src/core/pipeline.py | head -20
```

---

## Sources

### Primary (HIGH)
- Existing audit JSON schema from audit/universal_vendor_scraper/
- 20-CONTEXT.md locked decisions
- audit/SURFACE_REGISTRY.json
- audit/README.md

### Secondary (MEDIUM)
- Codebase structure via glob/enumeration
- ARCHITECTURE.md

### Tertiary (LOW)
- N/A - internal artifacts provide sufficient foundation

### Context7 Evidence
- Context7 not applicable for this task (internal codebase audit, not external library research)

---

## Open Questions

1. **Python vs JS handling:** Use file extension to select parser (.py → ast, .js/.ts/.tsx → pattern matching)
2. **Agent frameworks combined:** Treat as single prefix match for all 5 directories
3. **tests/ subdirectory preservation:** Maintain tests/ as prefix, all subdirs included
4. **Verification:** Script should output count verification, fail if ≠ 176

---

## Next Steps

1. Create audit directory structure for 22 units
2. Implement automated extraction for high-confidence surfaces
3. Manual review for cross-domain and blast-radius
4. Generate 176 JSON files
5. Validate with count verification

---

**RESEARCH COMPLETE** — Ready for planning.
