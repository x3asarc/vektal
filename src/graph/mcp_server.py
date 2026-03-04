"""
MCP server exposing knowledge graph tools for Claude Code.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List

# Ensure absolute imports resolve when running as `python src/graph/mcp_server.py`
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.graph.convention_checker import check_against_conventions, load_default_conventions
from src.graph.batch_handlers import batch_dependencies_handler, batch_query_handler
from src.graph.query_interface import query_graph
from src.graph.query_templates import execute_template
from src.graph.mcp_response_metadata import enrich_response

logger = logging.getLogger(__name__)

try:
    import mcp.server.stdio
    import mcp.types as types
    from mcp.server.lowlevel import Server, NotificationOptions
    from mcp.server.models import InitializationOptions

    MCP_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency during local tests
    mcp = None
    types = None
    Server = None
    NotificationOptions = None
    InitializationOptions = None
    MCP_AVAILABLE = False


_SESSION_CONTEXT: Dict[str, Any] = {
    "initialized": False,
    "system_context_emitted": False,
    "conventions": [],
}
_ARCHITECTURAL_KEYWORDS = ("architecture", "architectural", "convention", "refactor", "design", "pattern")


def _is_architectural_query(query: str) -> bool:
    lowered = query.lower()
    return any(keyword in lowered for keyword in _ARCHITECTURAL_KEYWORDS)


def _normalize_conventions(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    conventions: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        rule = row.get("rule")
        if not isinstance(rule, str) or not rule.strip():
            continue
        conventions.append(
            {
                "rule": rule.strip(),
                "scope": row.get("scope", "global"),
                "enforcement": row.get("enforcement", "advisory"),
                "examples": row.get("examples", ""),
            }
        )
    return conventions


def initialize_session_context(force: bool = False) -> List[Dict[str, Any]]:
    if _SESSION_CONTEXT["initialized"] and not force:
        return _SESSION_CONTEXT["conventions"]

    conventions = _normalize_conventions(execute_template("top_conventions", {"limit": 3}))
    if not conventions:
        conventions = load_default_conventions(limit=3)

    _SESSION_CONTEXT["initialized"] = True
    _SESSION_CONTEXT["system_context_emitted"] = False
    _SESSION_CONTEXT["conventions"] = conventions
    return conventions


def _attach_system_context(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not _SESSION_CONTEXT["initialized"]:
        initialize_session_context()
    if not _SESSION_CONTEXT["system_context_emitted"]:
        payload["system_context"] = {"conventions": _SESSION_CONTEXT["conventions"]}
        _SESSION_CONTEXT["system_context_emitted"] = True
    return payload


def _query_graph_schema() -> Dict[str, Any]:
    return {
        "name": "query_graph",
        "description": "Query knowledge graph using template, bridge, or fallback path",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "compact_output": {
                    "type": "boolean",
                    "default": False,
                    "description": "If true, return only essential fields (path, type, summary). Reduces token usage by ~40% for large result sets.",
                },
            },
            "required": ["query"],
        },
        "input_examples": [
            {"query": "who imports src/core/graphiti_client.py"},
            {"query": "what conventions exist for error handling", "compact_output": True},
            {"query": "show decisions made about the token budget"},
            {"query": "find all files that call semantic_cache.py"},
        ],
    }


def _get_dependencies_schema() -> Dict[str, Any]:
    return {
        "name": "get_dependencies",
        "description": "Get import dependency graph for a file",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "direction": {"type": "string", "enum": ["imports", "imported_by", "both"]},
                "depth": {"type": "integer"},
            },
            "required": ["file_path"],
        },
        "input_examples": [
            {
                "file_path": "src/core/graphiti_client.py",
                "direction": "imported_by",
                "depth": 2,
            },
            {
                "file_path": "src/graph/mcp_server.py",
                "direction": "both",
                "depth": 1,
            },
            {
                "file_path": "src/assistant/governance/kill_switch.py",
                "direction": "imports",
                "depth": 3,
            },
        ],
    }


def _retrieve_intent_schema() -> Dict[str, Any]:
    return {
        "name": "retrieve_intent",
        "description": "Retrieve decision/convention/bug root-cause intent context",
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
        "input_examples": [
            {"query": "why was 8192 chosen as the token budget"},
            {"query": "what architectural decisions exist for Neo4j vector index"},
            {"query": "any known bugs related to session lifecycle hooks"},
            {"query": "conventions for Celery queue naming"},
        ],
    }


def _search_tools_schema() -> Dict[str, Any]:
    return {
        "name": "search_tools",
        "description": "Search for available tools by natural language query. Returns tool schemas matching the intent.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language description of what you want to do",
                },
                "tier": {
                    "type": "integer",
                    "description": "Optional tier restriction (1, 2, or 3)",
                    "enum": [1, 2, 3],
                },
                "top_k": {
                    "type": "integer",
                    "description": "Max number of tools to return",
                    "default": 3,
                },
            },
            "required": ["query"],
        },
        "input_examples": [
            {"query": "tools for updating product prices"},
            {"query": "tools allowed in tier 2 that mutate data", "tier": 2},
            {"query": "read product information", "top_k": 5},
        ],
    }


def _batch_query_schema() -> Dict[str, Any]:
    return {
        "name": "batch_query",
        "description": "Execute multiple graph queries in a single call. Returns aggregated results with per-query status. Use this for multi-entity resolution instead of calling query_graph repeatedly.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "queries": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of natural language queries to execute",
                    "minItems": 1,
                    "maxItems": 50,
                },
                "aggregate_mode": {
                    "type": "string",
                    "enum": ["separate", "merged"],
                    "default": "separate",
                    "description": "separate: per-query results; merged: combine into single list",
                },
            },
            "required": ["queries"],
        },
        "input_examples": [
            {
                "queries": [
                    "who imports src/core/graphiti_client.py",
                    "what calls src/graph/semantic_cache.py",
                ]
            },
            {
                "queries": [
                    "conventions for rate limiting",
                    "decisions about Celery queues",
                    "known bugs in session lifecycle",
                ],
                "aggregate_mode": "merged",
            },
        ],
    }


def _batch_dependencies_schema() -> Dict[str, Any]:
    return {
        "name": "batch_dependencies",
        "description": "Get dependency information for multiple files in a single call. Returns combined dependency map. Use this for multi-file analysis instead of calling get_dependencies repeatedly.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of file paths to analyze",
                    "minItems": 1,
                    "maxItems": 30,
                },
                "direction": {
                    "type": "string",
                    "enum": ["imports", "imported_by", "both"],
                    "default": "both",
                },
                "depth": {"type": "integer", "minimum": 1, "maximum": 3, "default": 2},
            },
            "required": ["file_paths"],
        },
        "input_examples": [
            {
                "file_paths": ["src/core/graphiti_client.py", "src/graph/mcp_server.py"],
                "direction": "both",
                "depth": 2,
            },
            {
                "file_paths": [
                    "src/assistant/governance/kill_switch.py",
                    "src/assistant/governance/field_policy.py",
                ],
                "direction": "imports",
            },
        ],
    }


def _research_vendor_schema() -> Dict[str, Any]:
    return {
        "name": "research_vendor",
        "description": "Research vendor capabilities, API changes, or documentation. Uses Firecrawl web scraping with Perplexity AI fallback.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vendor_name": {
                    "type": "string",
                    "description": "Vendor domain or name (e.g., 'pentart', 'schmincke')",
                },
                "query": {
                    "type": "string",
                    "description": "What to research (e.g., 'API authentication changes in 2026')",
                },
            },
            "required": ["vendor_name", "query"],
        },
        "input_examples": [
            {"vendor_name": "pentart", "query": "API authentication methods 2026"},
            {"vendor_name": "schmincke", "query": "product catalog structure changes"},
        ],
    }


def _search_documentation_schema() -> Dict[str, Any]:
    return {
        "name": "search_documentation",
        "description": "Search for technical documentation using AI-powered search. Returns relevant docs with citations.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Technical topic to research"},
                "library": {"type": "string", "description": "Specific library/framework name (optional)"},
            },
            "required": ["topic"],
        },
        "input_examples": [
            {"topic": "Neo4j vector search optimization"},
            {"topic": "rate limiting", "library": "Flask"},
            {"topic": "Celery group patterns", "library": "celery"},
        ],
    }


def list_tool_contracts() -> List[Dict[str, Any]]:
    """Return tool schemas. If deferred_loading=true, return only base tools."""
    from pathlib import Path

    # Load config
    config_path = Path(__file__).parent.parent.parent / ".claude" / "settings.local.json"
    config = {}
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    mcp_config = config.get("mcp_server", {})
    deferred = mcp_config.get("deferred_loading", False)
    base_tools = set(mcp_config.get("base_tools", ["search_tools"]))

    all_tools = [
        _query_graph_schema(),
        _get_dependencies_schema(),
        _retrieve_intent_schema(),
        _search_tools_schema(),
        _batch_query_schema(),
        _batch_dependencies_schema(),
        _research_vendor_schema(),
        _search_documentation_schema(),
    ]

    if deferred:
        # Only return tools in base_tools list
        return [t for t in all_tools if t["name"] in base_tools]

    # Threshold check: if few tools, load all anyway
    threshold = mcp_config.get("discovery_threshold", 10)
    if len(all_tools) < threshold:
        return all_tools

    return all_tools


def query_graph_tool(query: str, compact_output: bool = False) -> Dict[str, Any]:
    result = query_graph(query, use_natural_language=True, compact=compact_output)
    payload = {
        "results": result.data,
        "source": result.source,
        "duration_ms": result.duration_ms,
        "success": result.success,
        "error": result.error,
        "conventions_checked": result.conventions_checked,
        "compact": compact_output,
    }
    return _attach_system_context(payload)


def get_dependencies_tool(file_path: str, direction: str = "both", depth: int = 1) -> Dict[str, Any]:
    queries = []
    if direction in ("imports", "both"):
        queries.append(query_graph(f"what does {file_path} depend on"))
    if direction in ("imported_by", "both"):
        queries.append(query_graph(f"what imports {file_path}"))

    dependencies: List[Dict[str, Any]] = []
    for result in queries:
        dependencies.extend(result.data)

    dedup = {(item.get("path"), item.get("purpose")): item for item in dependencies if isinstance(item, dict)}
    payload = {
        "file": file_path,
        "dependencies": list(dedup.values()),
        "direction": direction,
        "depth": depth,
        "impact_radius": len(dedup),
    }
    return _attach_system_context(payload)


def retrieve_intent_tool(query: str) -> Dict[str, Any]:
    if not _SESSION_CONTEXT["initialized"]:
        initialize_session_context()

    result = query_graph(query, use_natural_language=True)
    is_architectural = _is_architectural_query(query)
    conventions = _SESSION_CONTEXT["conventions"] if is_architectural else []

    violations = []
    if conventions:
        violations = [
            {
                "convention": violation.convention,
                "confidence": violation.confidence,
                "suggested_alternative": violation.suggested_alternative,
            }
            for violation in check_against_conventions(query, conventions=conventions, threshold=0.7)
        ]

    payload = {
        "results": result.data,
        "source": result.source,
        "confidence": 0.7 if result.data else 0.0,
        "conventions": conventions,
        "convention_violations": violations,
    }
    return _attach_system_context(payload)


def _search_tools_handler(query: str, tier: int | None = None, top_k: int = 3) -> Dict[str, Any]:
    """Search Neo4j for tools matching the query."""
    from src.core.embeddings import generate_embedding
    from src.graph.query_templates import execute_template

    # Generate query embedding
    query_embedding = generate_embedding(query)

    # Execute graph query
    results = execute_template(
        "tool_search",
        {"query_embedding": query_embedding, "tier": tier, "top_k": top_k},
    )

    # Fallback to text search if no results or vector index error
    if not results:
        results = execute_template(
            "tool_search_text",
            {"query": query, "tier": tier, "top_k": top_k},
        )

    # Format results
    tools = []
    for record in results:
        try:
            # record["schema"] is the full schema stored in ToolNode
            schema = json.loads(record["schema"]) if isinstance(record["schema"], str) else record["schema"]
            input_schema = schema.get("inputSchema") if isinstance(schema, dict) and "inputSchema" in schema else schema
            input_examples = (
                json.loads(record["examples"])
                if isinstance(record["examples"], str)
                else (record["examples"] or [])
            )
            tools.append(
                {
                    "name": record["name"],
                    "description": record["description"],
                    "inputSchema": input_schema if isinstance(input_schema, dict) else {},
                    "input_examples": input_examples,
                    # Backward-compatible aliases for existing tests/consumers.
                    "schema": input_schema if isinstance(input_schema, dict) else {},
                    "examples": input_examples,
                    "relevance_score": record.get("score", 1.0),
                    # Include full schema for Claude to "load" the tool
                    "fullSchema": schema,
                }
            )
        except Exception as e:
            # logger is already defined in the module
            logger.error(f"Error parsing tool record {record.get('name')}: {e}")
            continue

    payload = {
        "tools": tools,
        "query": query,
        "tier_filter": tier,
    }
    return _attach_system_context(payload)


async def dispatch_tool_call(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatch MCP tool call to appropriate handler."""
    result = None
    if name == "query_graph":
        result = query_graph_tool(
            query=arguments["query"],
            compact_output=arguments.get("compact_output", False),
        )
    elif name == "get_dependencies":
        result = get_dependencies_tool(
            file_path=arguments["file_path"],
            direction=arguments.get("direction", "both"),
            depth=arguments.get("depth", 1),
        )
    elif name == "retrieve_intent":
        result = retrieve_intent_tool(arguments["query"])
    elif name == "search_tools":
        result = _search_tools_handler(
            query=arguments["query"],
            tier=arguments.get("tier"),
            top_k=arguments.get("top_k", 3),
        )
    elif name == "batch_query":
        result = await batch_query_handler(
            queries=arguments["queries"],
            aggregate_mode=arguments.get("aggregate_mode", "separate"),
        )
    elif name == "batch_dependencies":
        result = await batch_dependencies_handler(
            file_paths=arguments["file_paths"],
            direction=arguments.get("direction", "both"),
            depth=arguments.get("depth", 1),
        )
    elif name == "research_vendor":
        from src.graph.research_tools import research_vendor

        result = await research_vendor(
            vendor_name=arguments["vendor_name"],
            query=arguments["query"],
        )
    elif name == "search_documentation":
        from src.graph.research_tools import search_documentation

        result = await search_documentation(
            topic=arguments["topic"],
            library=arguments.get("library"),
        )
    
    if result is not None:
        return enrich_response(result)
        
    raise ValueError(f"Unknown tool: {name}")
    
async def run_server() -> None:
    if not MCP_AVAILABLE:
        raise RuntimeError("MCP SDK is not available. Install 'mcp' dependency first.")

    initialize_session_context()
    server = Server("synthex-knowledge-graph")

    @server.list_tools()
    async def list_tools():
        return [
            types.Tool(
                name=tool["name"],
                description=tool["description"],
                inputSchema=tool["inputSchema"],
                input_examples=tool.get("input_examples", []),
            )
            for tool in list_tool_contracts()
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]):
        return await dispatch_tool_call(name, arguments)

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="synthex-knowledge-graph",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(run_server())
