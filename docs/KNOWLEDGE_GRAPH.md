# Knowledge Graph - System-Wide Context Source

**Neo4j/Graphiti knowledge graph is the DEFAULT context source for ALL operations in this codebase.**

## Overview

The knowledge graph contains 2,784 nodes and 6,254 relationships representing the entire codebase structure, dependencies, and semantic relationships. It's automatically used for all context retrieval operations.

## Graph Contents

### Node Types
- **File** - All Python/TypeScript source files
- **Class** - Class definitions with their methods
- **Function** - Function definitions and signatures
- **PlanningDoc** - Phase plans and architectural docs
- **Tool** - MCP tools and their schemas
- **Convention** - Code conventions and patterns
- **Entity**, **Community**, **Saga**, **Episodic** - Graphiti semantic entities

### Relationship Types
- **IMPORTS** - File → File import relationships
- **CALLS** - Function → Function call relationships
- **DEFINES_CLASS** - File → Class definitions
- **DEFINES_FUNCTION** - File/Class → Function definitions
- **CONTAINS** - Containment relationships
- **RELATES_TO**, **MENTIONS** - Semantic relationships
- **HAS_EPISODE**, **HAS_MEMBER** - Graphiti relationships

## Configuration

### Required Environment Variables

```bash
GRAPH_ORACLE_ENABLED=true
NEO4J_URI=neo4j+s://5953bf18.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=<your-password>
```

These are already configured in `.env`.

### Instance Details
- **Name**: vaktal
- **ID**: 5953bf18
- **Type**: Neo4j Aura (cloud-hosted)
- **Model**: sentence-transformers/all-MiniLM-L6-v2

## Usage

### Automatic Integration (Recommended)

The graph is **automatically used** by the assistant context broker. No explicit code needed:

```python
from src.assistant.context_broker import get_context

# Graph is used automatically as primary source
bundle = get_context("files that handle embeddings")
print(bundle.output_text)  # Context from graph
print(bundle.telemetry["graph_used"])  # True if graph was used
```

### Direct Graph Queries

For specific queries, use the query interface:

```python
from src.graph.query_interface import query_graph

# Find what imports a file
result = query_graph("imported_by", {"file_path": "src/core/embeddings.py"})

# Find what a file imports
result = query_graph("imports", {"file_path": "src/core/embeddings.py"})

# Trace impact radius (what depends on this)
result = query_graph("impact_radius", {"file_path": "src/core/embeddings.py"})

# Find similar files (semantic search)
result = query_graph("similar_files", {
    "file_path": "src/core/embeddings.py",
    "limit": 5,
    "threshold": 0.7
})

# Find function callers
result = query_graph("function_callers", {"function_name": "embed_file_summary"})

# Find function callees
result = query_graph("function_callees", {"function_name": "embed_file_summary"})
```

### Natural Language Queries

For unstructured queries, use the bridge:

```python
from src.graph.query_interface import query_with_bridge

# Natural language semantic search
result = query_with_bridge("files that handle memory management", compact=True)

for item in result.data:
    print(f"{item['path']}: {item['purpose']}")
```

## Available Query Templates

See `src/graph/query_templates.py:QUERY_TEMPLATES` for all available templates:

| Template | Purpose | Parameters |
|----------|---------|------------|
| `imports` | Files imported by a file | `file_path` |
| `imported_by` | Files that import a file | `file_path` |
| `similar_files` | Semantically similar files | `file_path`, `limit`, `threshold` |
| `impact_radius` | Dependency chain 1-3 levels deep | `file_path` |
| `function_callers` | Functions that call a function | `function_name` |
| `function_callees` | Functions called by a function | `function_name` |
| `functions_in_file` | All functions in a file | `file_path` |
| `planning_context` | Planning docs for a file | `file_path` |
| `phase_code` | Files implementing a phase | `phase` |
| `top_conventions` | Most referenced conventions | `limit` |
| `tool_search` | Vector search for tools | `query_embedding`, `top_k`, `tier` |
| `tool_search_text` | Text search for tools | `query`, `top_k`, `tier` |

## Integration Points

The graph is automatically used by:

- **Assistant context retrieval** (`src/assistant/context_broker.py`)
- **/simplify skill** - dead code investigation, import tracing
- **Code exploration** - finding related files and patterns
- **Impact analysis** - understanding change radius
- **Duplication detection** - finding similar code patterns

## Fallback Behavior

If the graph is unavailable:
1. Tries local snapshot (if available)
2. Falls back to doc search (`docs/AGENT_START_HERE.md`, etc.)
3. Returns baseline "no context" message

Graph queries log gracefully and never break the flow. Empty results are valid (means no connections).

## Maintenance

### Syncing the Graph

After major codebase changes, sync the graph:

```bash
python scripts/graph/sync_to_neo4j.py
```

This scans the codebase and updates:
- File nodes with current content
- Import/call relationships
- Semantic embeddings
- Planning doc links

### Incremental Sync

For quick updates after small changes:

```python
from src.graph.incremental_sync import sync_changed_files

# Sync only changed files from git
result = sync_changed_files()
print(f"Synced {result.files_synced} files")
```

## Debugging

### Check Graph Connectivity

```bash
python -c "
from src.graph.query_interface import query_graph
result = query_graph('imports', {'file_path': 'src/api/app.py'})
print(f'Success: {result[\"success\"]}')
print(f'Data: {result[\"data\"][:3]}')  # First 3 results
"
```

### Inspect Graph Schema

```bash
python -c "
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()
driver = GraphDatabase.driver(
    os.getenv('NEO4J_URI'),
    auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))
)

with driver.session() as session:
    # Get node labels
    labels = session.run('CALL db.labels() YIELD label RETURN label')
    print('Node Labels:', [r['label'] for r in labels])

    # Get relationship types
    rels = session.run('CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType')
    print('Relationships:', [r['relationshipType'] for r in rels])
"
```

## Best Practices

1. **Always use the graph first** - It's faster and more accurate than grep/file search
2. **Investigate before deleting** - Use `function_callers`, `imported_by`, `impact_radius` to trace dead code
3. **Trace incomplete integrations** - Graph shows where code SHOULD be connected but isn't
4. **Use semantic search** - `similar_files` finds patterns even with different naming
5. **Check impact radius** - Before refactoring, see what depends on your changes

## See Also

- **CLAUDE.md** - Project-wide knowledge graph documentation
- **src/graph/query_interface.py** - Query interface implementation
- **src/graph/query_templates.py** - Available query templates
- **src/graph/search_expand_bridge.py** - Semantic search bridge
- **src/assistant/context_broker.py** - Context retrieval with graph integration
