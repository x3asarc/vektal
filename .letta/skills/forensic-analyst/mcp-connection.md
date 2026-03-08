# MCP Server: synthex-knowledge-graph

## Connection Details
- **Transport:** stdio
- **Command:** `./venv/Scripts/python.exe src/graph/mcp_server.py`
- **CWD:** `C:\Users\Hp\Documents\Shopify Scraping Script`
- **Server name:** `synthex-knowledge-graph`

## Backend (verified working)
Neo4j is live and connected. Confirmed via live Cypher query warnings from Neo4j server during probe.

## Available Tools (deferred_loading=true, expand with search_tools)

| Tool | Purpose |
|---|---|
| `search_tools` | Vector-search for available tools — call first to load others |
| `query_graph` | Natural language graph query (semantic → template → bridge) |
| `get_dependencies` | Blast radius — import chains for any file |
| `retrieve_intent` | Root cause, known bugs, architectural decisions |
| `batch_query` | Multiple queries in one call |
| `batch_dependencies` | Multi-file dependency analysis |
| `research_vendor` | Web research via Firecrawl / Perplexity |
| `search_documentation` | Technical docs search |

## Usage Pattern (deferred loading)
Because `deferred_loading: true`, only `search_tools` loads on init.
To access other tools, first call:
```json
search_tools({"query": "dependency analysis", "top_k": 3})
```
Then use the returned tool schemas directly.

## Test Command (manual probe)
```bash
cmd /c "cd C:\Users\Hp\Documents\Shopify Scraping Script && npx tsx <skill-scripts>/mcp-stdio.ts ""./venv/Scripts/python.exe src/graph/mcp_server.py"" list-tools"
```

## Connectivity Fallback (if MCP fails)
1. Check `.graph/runtime-backend.json` for backend status
2. Check `.env` — `GRAPH_ORACLE_ENABLED=true` must be set
3. Check Docker is running (for local Neo4j)
4. Check Aura credentials: `AURA_CLIENT_ID`, `AURA_CLIENT_SECRET`
