# Phase 20: System Integrity Audit - Research

**Researched:** 2026-03-18
**Domain:** Codebase audit methodology, JSON schema design, cross-domain coupling analysis, automation strategies
**Confidence:** HIGH

## Summary

The Phase 20 amendment requires deep analysis audits for 22 code folders across 8 surfaces. This research establishes the methodology for generating comprehensive JSON audit files for each unit-surface combination (176 total files). The existing audit artifacts in `.planning/phases/20-system-integrity-audit-remediation-waves/audit/` provide a proven JSON schema that should be replicated for all 22 units.

**Primary recommendation:** Use existing JSON schema as canonical template, implement batch processing script to iterate through 22 units, apply parallel surface analysis where surfaces share data sources.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
1. 22 logical audit units (src/core/, src/, src/api/, src/jobs/, src/graph/, src/memory/, src/auth/, src/billing/, src/integrations/, universal_vendor_scraper/, frontend/, seo/, config/, data/, utils/, tests/, docs/, ops/, scripts/, reports/, migrations/, .agents.claude.codex.gemini.letta combined)
2. All 8 surfaces per unit: ownership, blast-radius, import-chain, data-access, api-surface, async-surface, config-surface, cross-domain
3. Deep analysis: full dependency graphs, cross-domain coupling maps, comprehensive blast-radius analysis
4. Output: 22 units × 8 surfaces = 176 JSON files in audit/ subdirectories
5. tests/ as 1 logical unit (all subdirs included)
6. Agent frameworks (.agents/, .claude/, .codex/, .gemini/, .letta/) as 1 logical unit

### Claude's Discretion
- How to organize the research
- Specific tooling and approach for each surface
- How to structure the JSON output
- Automation strategies

### Deferred Ideas (OUT OF SCOPE)
- Any folder not in the 22 units list
</user_constraints>

---

## Standard Stack

### Core Analysis Tools
| Tool | Purpose | Why Standard |
|------|---------|--------------|
| `glob` | File enumeration | Native to workspace, fast pattern matching |
| `grep` | Content search | Native to workspace, regex support |
| `read` | File content extraction | Native to workspace |
| `Python ast` | Python import parsing | Standard library, accurate dependency extraction |
| `JavaScript espree/acorn` | JS import parsing | Standard for Node.js AST analysis |
| `neo4j` (existing) | Graph dependency storage | Already integrated in `.graph/` |

### JSON Output Schema
| Surface | Key Fields | Source |
|---------|------------|--------|
| ownership | `matched_files`, `inbound_references`, `inbound_imports` | Filesystem + Neo4j |
| blast-radius | `direct_outbound_calls`, `direct_inbound_calls`, `depth_2_reach` | Call graph analysis |
| import-chain | `outbound_imports`, `transitive_dependencies_depth_2` | Import parsing |
| data-access | `table_accesses`, `query_patterns` | Model inspection |
| api-surface | `routes`, `handlers` | Route file parsing |
| async-surface | `tasks`, `queues` | Celery task decorator scan |
| config-surface | `env_dependencies`, `env_var_count` | Env var regex scanning |
| cross-domain | `imports_out`, `references_out`, `calls_out` | Cross-prefix analysis |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `jinja2` | Latest | Template generation for JSON |批量生成audit文件 |
| `concurrent.futures` | Built-in | Parallel surface processing | When analyzing independent surfaces |

---

## Architecture Patterns

### Recommended Project Structure
```
audit/
├── src-core/
│   ├── ownership.json
│   ├── blast-radius.json
│   ├── import-chain.json
│   ├── data-access.json
│   ├── api-surface.json
│   ├── async-surface.json
│   ├── config-surface.json
│   └── cross-domain.json
├── src/
├── src-api/
... (22 units total)
```

### Pattern 1: Batch Surface Analyzer
**What:** Script that iterates through 22 units, generates all 8 surfaces per unit
**When to use:** Initial audit generation phase
**Example:**
```python
UNITS = [
    "src/core", "src", "src/api", "src/jobs", "src/graph",
    "src/memory", "src/auth", "src/billing", "src/integrations",
    "universal_vendor_scraper", "frontend", "seo", "config",
    "data", "utils", "tests", "docs", "ops", "scripts",
    "reports", "migrations", "agent-frameworks"
]

SURFACES = [
    "ownership", "blast-radius", "import-chain",
    "data-access", "api-surface", "async-surface",
    "config-surface", "cross-domain"
]

def generate_audit(unit: str, surface: str) -> dict:
    # Implementation based on surface type
    pass
```

### Pattern 2: Cross-Domain Coupling Map
**What:** Builds relationship matrix between the 22 units showing import/reference/call patterns
**When to use:** After individual unit audits, for system-level understanding
**Example:**
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

### Pattern 3: Deep Blast-Radius Analysis
**What:** For each file in unit, trace impact through import chain and call graph to depth 3
**When to use:** High-value change impact assessment
**Output:**
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

### Anti-Patterns to Avoid
- **Single-threaded sequential processing:** With 176 files, processing sequentially will be too slow. Use parallel execution.
- **Duplicate file enumeration:** Each surface shouldn't re-enumerate files. Cache matched_files.
- **Ignoring Neo4j:** Existing `.graph/local-snapshot.json` already contains cross-file references. Leverage instead of re-parsing.
- **Shallow analysis only:** "Deep analysis" requirement means full dependency graphs, not just direct imports.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Python import parsing | Custom regex | `ast` module + existing audit patterns | Handles edge cases, tracks aliasing |
| JavaScript import parsing | Custom regex | `acorn` or existing patterns from `universal_vendor_scraper/audit/` | Handles ESM/CommonJS |
| File enumeration | `os.walk` | `glob` tool | Pattern matching, faster |
| Cross-file reference finding | Custom graph builder | `.graph/local-snapshot.json` | Already populated |
| JSON schema validation | Custom validator | Reuse existing audit JSON structure | Proven schema |

**Key insight:** The existing audit files in `audit/universal_vendor_scraper/` provide a working template. The `coverage` object with `evidence_source`, `graph_backed`, `filesystem_backed` should be replicated exactly.

---

## Common Pitfalls

### Pitfall 1: Incomplete Unit Coverage
**What goes wrong:** Missing some of the 22 units, especially the smaller ones like `src/integrations/` or `seo/`
**Why it happens:** Manual unit selection, not using the complete list from CONTEXT.md
**How to avoid:** Use the 22-unit list as definitive checklist, verify each exists with glob before generating
**Warning signs:** Final count ≠ 176 JSON files

### Pitfall 2: Surface Data Mismatch
**What goes wrong:** Each surface JSON has different matched_files list
**Why it happens:** Not caching file enumeration, re-parsing per surface
**How to avoid:** Compute matched_files once per unit, inject into all 8 surfaces
**Warning signs:** Same file appears in different surface audits with different counts

### Pitfall 3: Cross-Domain Analysis Blindness
**What goes wrong:** Not detecting that `src/core` imports from `src/auth` or similar cross-unit references
**Why it happens:** Only analyzing within-unit imports, not cross-prefix references
**How to avoid:** Filter import chains for any dependency with different prefix than source unit
**Warning signs:** cross-domain.json shows zero cross-references when system clearly has coupling

### Pitfall 4: Shallow Blast-Radius
**What goes wrong:** Only depth-1 impact analysis, missing cascade effects
**Why it happens:** "Deep analysis" requirement interpreted as "some analysis" rather than "full graph"
**How to avoid:** Implement recursive depth-first traversal to max depth (recommend 3), collect all reachable nodes
**Warning signs:** blast-radius.json only has direct_outbound_calls, no depth_2_reach

---

## Code Examples

Verified patterns from existing audit files:

### ownership.json structure
```json
{
  "folder_path": "universal_vendor_scraper",
  "generated_at": "2026-03-12T18:49:30.439349+00:00",
  "coverage": {
    "evidence_source": ["filesystem-enumeration", "neo4j-bulk-snapshot", "phase20-wave2-canonical-surface-model"],
    "graph_backed": true,
    "filesystem_backed": true,
    "coverage_confidence": "high",
    "contract_satisfied": true,
    "known_blind_spots": [],
    "canonical_prefix": "universal_vendor_scraper",
    "canonical_surface": "universal_vendor_scraper",
    "matched_file_count": 16
  },
  "matched_files": ["..."],
  "inbound_references": [{"source": ".graph/local-snapshot.json", "dependency": "..."}],
  "summary": {
    "inbound_importer_count": 0,
    "inbound_referrer_count": 1,
    "owned_function_count": 0
  }
}
```

### import-chain.json structure
```json
{
  "outbound_imports": [{"source": "...", "dependency": "..."}],
  "transitive_dependencies_depth_2": [{"root_file": "...", "dependency": "...", "depth": 1}],
  "summary": {
    "direct_dependency_file_count": 8,
    "cross_prefix_dependency_file_count": 0
  }
}
```

### cross-domain.json structure
```json
{
  "imports_out": [],
  "references_out": [],
  "calls_out": [],
  "domain_summary": {
    "imports_out": [],
    "references_out": [],
    "calls_out": []
  },
  "summary": {
    "cross_import_count": 0,
    "cross_reference_count": 0,
    "cross_call_count": 0
  }
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual folder-by-folder audit | Batch scripted generation | Phase 20 original | 48 folders, 6% coverage |
| Per-surface file enumeration | Cached matched_files per unit | This amendment | Consistent file counts |
| Single-surface focus | 8-surface parallel analysis | This amendment | Complete coverage |
| Shallow dependency trace | Depth-3 blast-radius | This amendment | True impact analysis |

**Deprecated/outdated:**
- Manual audit entry - replaced by automated JSON generation
- Per-folder surface files not in audit/ subdirectory - now standardized to audit/{unit}/{surface}.json

---

## Open Questions

1. **Python vs JavaScript handling**
   - What we know: src/core, src/api are Python; universal_vendor_scraper, frontend are JS
   - What's unclear: Should we use different parsing logic per file type, or generic approach?
   - Recommendation: Use file extension to select parser (`.py` → ast, `.js/.ts/.tsx` → acorn pattern matching)

2. **Agent frameworks combined unit**
   - What we know: .agents/, .claude/, .codex/, .gemini/, .letta/ should be one audit unit
   - What's unclear: How to handle the different nested structures (skills vs agents vs settings)?
   - Recommendation: Treat as single prefix match, all files under any of the 5 directories

3. **tests/ as single unit**
   - What we know: tests/unit, tests/integration, tests/e2e, tests/graph, tests/daemons, tests/planning
   - What's unclear: Should we maintain subdirectory structure in audit output?
   - Recommendation: Use tests/ as prefix, all matched files in any subdirectory

4. **Verification approach**
   - What we know: Need to confirm 176 JSON files generated
   - What's unclear: Manual verification vs automated check?
   - Recommendation: Script should output count verification, fail if ≠ 176

---

## Sources

### Primary (HIGH confidence)
- Existing audit JSON schema from `audit/universal_vendor_scraper/` - 8 surface files examined
- CONTEXT.md locked decisions - 22 units defined with confidence HIGH
- SURFACE_REGISTRY.json - surface definitions with confidence HIGH

### Secondary (MEDIUM confidence)
- Codebase structure via glob - confirms all 22 units exist with files

### Tertiary (LOW confidence)
- N/A - no external research needed, internal artifacts provide sufficient foundation

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Using existing audit schema, native tools
- Architecture: HIGH - Proven batch processing pattern, existing artifact structure
- Pitfalls: HIGH - Identified from audit gap analysis in CONTEXT.md

**Research date:** 2026-03-18
**Valid until:** 90 days - methodology is stable, only execution varies