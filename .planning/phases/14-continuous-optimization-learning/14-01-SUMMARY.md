# Phase 14 Plan 01 - Codebase Entity Schema Foundation

## Summary

Extended Neo4j schema with codebase-specific entity types for knowledge graph indexing. Created Pydantic v2 models for files, modules, classes, functions, and planning docs with relationship edges for imports, containment, calls, inheritance, implementation, and references.

## What Was Built

### Core Entity Models (`src/core/codebase_entities.py`)

**Entity Types (5):**
1. **FileEntity** - Source file representation
   - Fields: path, language, purpose, exports, line_count, last_modified, content_hash
   - Supports Python, TypeScript, YAML, Markdown
   - Path normalization validator (forward slashes, relative paths)

2. **ModuleEntity** - Python module/package
   - Fields: path, name, purpose, is_package, submodules
   - Distinguishes between packages (directories) and simple modules

3. **ClassEntity** - Class definition
   - Fields: file_path, name, full_name, purpose, methods, bases, line_start, line_end
   - Tracks inheritance hierarchy and method signatures

4. **FunctionEntity** - Function or method
   - Fields: file_path, name, full_name, signature, purpose, is_async, line_start, line_end
   - Supports both standalone functions and class methods

5. **PlanningDocEntity** - Planning/documentation
   - Fields: path, doc_type, phase_number, plan_number, title, goal, status
   - Central hub nodes linking requirements to implementations
   - Doc types: PLAN, SUMMARY, CONTEXT, VERIFICATION, ROADMAP, STATE

**Edge Types (6):**
1. **ImportsEdge** - File imports (absolute, relative, from_import)
2. **ContainsEdge** - Hierarchical containment (module→file, file→class/function)
3. **CallsEdge** - Function call relationships with call counts
4. **InheritsEdge** - Class inheritance hierarchy
5. **ImplementsEdge** - Code implements planning doc (auto-linked via commits)
6. **ReferencesEdge** - Natural doc references (comments, docstrings)

**CodebaseEdgeType Enum:** Centralized edge type constants

### Schema Definitions (`src/core/codebase_schema.py`)

**Indexes (7):**
- 5 unique constraints: File.path, Module.path, Class.full_name, Function.full_name, PlanningDoc.path
- 2 composite indexes: File(language, last_modified), Function(file_path, name)

**Constraints (2):**
- EXISTS constraints: File.path, Function.full_name
- Note: Degrades gracefully on Neo4j Community Edition (warns but continues)

**ensure_schema(client, dry_run):**
- Idempotent schema initialization using IF NOT EXISTS clauses
- Async function with timeout protection
- Returns success/failure status
- Fail-open behavior: warns but doesn't block if graph unavailable

### CLI Script (`scripts/graph/init_codebase_schema.py`)

**Features:**
- `--dry-run` flag for schema preview
- Project root path resolution for imports
- Graceful degradation: exits 0 if graph unavailable (doesn't block pipelines)
- Logs all schema operations
- Exit codes: 0 (success or graceful skip), 1 (hard failure)

## Design Decisions

### 1. BaseEntity Inheritance Pattern

Inherited from `synthex_entities.BaseEntity` for consistency with Phase 13.2 graph structures. While codebase entities don't need `store_id` (single-tenant), this maintains architectural uniformity for potential future multi-repository support.

### 2. Path Normalization

All path validators normalize to forward slashes and remove leading `./` for cross-platform compatibility (Windows/Linux/Mac).

### 3. Planning Docs as Central Hubs

PlanningDocEntity designed as most-referenced node type in graph:
- Auto-linked via commit message parsing (ImplementsEdge)
- Natural references via code comments (ReferencesEdge)
- Keyboard analogy: Planning docs are "Fn keys" - see overview without drilling into implementation

### 4. Fail-Open Schema Initialization

Script exits 0 even if graph unavailable to prevent blocking CI pipelines when Neo4j isn't running locally. Production deployments can enforce hard requirement via different entrypoint.

### 5. Frozen Discriminators

All `entity_type` and `edge_type` fields use `frozen=True` to prevent accidental mutation, following Phase 13.2 pattern.

## Integration Points

### With Phase 13.2 (Oracle Framework)

- Reuses `BaseEntity`/`BaseEdge` patterns from `synthex_entities.py`
- Compatible with existing `get_graphiti_client()` singleton
- Follows fail-open timeout-bounded query patterns

### With Future Plans

- **Plan 02 (Vectors):** Entity models ready for embedding fields
- **Plan 03 (Scanner):** Schema ready for bulk node creation
- **Plan 04 (Planning Links):** PlanningDocEntity ready for central hub role
- **Plan 05-08:** Automatic update triggers will use these entities

## Verification Results

### Entity Import Tests
```bash
✓ All 5 entities importable (FileEntity, ModuleEntity, ClassEntity, FunctionEntity, PlanningDocEntity)
✓ All 6 edges importable (ImportsEdge, ContainsEdge, CallsEdge, InheritsEdge, ImplementsEdge, ReferencesEdge)
✓ CodebaseEdgeType enum available
```

### Schema Script Dry-Run
```bash
✓ Shows 5 unique constraints planned
✓ Shows 2 composite indexes planned
✓ Shows 2 existence constraints planned
✓ Exits 0 successfully
```

### Regression Tests
```bash
✓ 10 graphiti client tests pass
✓ 13 graph oracle adapter tests pass
✓ 10 graphiti sync tests pass
✓ Total: 33/33 graph-related tests pass
```

### Pattern Compliance
- ✓ Inherits from BaseEntity/BaseEdge (synthex_entities.py pattern)
- ✓ Uses frozen discriminators on entity_type/edge_type
- ✓ Includes path normalization validators
- ✓ No new dependencies (uses existing Pydantic v2)

## Files Created/Modified

### Created (0)
All files pre-existed from previous planning work.

### Modified (1)
- `scripts/graph/init_codebase_schema.py` - Added sys.path.insert for project root imports

## Known Limitations

### 1. store_id Field in Codebase Entities

Codebase entities inherit `store_id` from `BaseEntity` but it's semantically inappropriate for single-tenant project-level artifacts. Accepted for architectural consistency - future work could create `BaseCodebaseEntity` without multi-tenant fields.

### 2. EXISTS Constraints Require Enterprise

`EXISTS` constraints (File.path, Function.full_name) fail on Neo4j Community Edition. Script degrades gracefully with warnings rather than errors.

### 3. No Vector Embeddings Yet

Entity models don't include embedding fields - deferred to Plan 02 (Vector Embedding Pipeline).

## Next Steps (Plan 02)

1. Add `embedding: List[float]` fields to FileEntity, ClassEntity, FunctionEntity
2. Create hierarchical summary extractor (file docstring + exports, function signature + docstring)
3. Implement sentence-transformers embedding generation
4. Create Neo4j vector index (`file_embeddings`, `function_embeddings`)
5. Add similarity query helpers (find_similar_files, find_similar_functions)

---

**Phase:** 14-continuous-optimization-learning
**Plan:** 14-01
**Status:** Complete
**Execution Time:** ~15 minutes
**LOC Modified:** 3 lines (sys.path.insert in init script)
**Tests Passing:** 33/33 graph-related tests
**Commits:** Pending
