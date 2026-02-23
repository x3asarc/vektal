"""
MCP server exposing knowledge graph tools for Claude Code.
"""

import asyncio
from typing import Any, Dict, List

from src.graph.convention_checker import check_against_conventions, load_default_conventions
from src.graph.query_interface import query_graph
from src.graph.query_templates import execute_template

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


def list_tool_contracts() -> List[Dict[str, Any]]:
    return [
        {
            "name": "query_graph",
            "description": "Query knowledge graph using template, bridge, or fallback path",
            "inputSchema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
        {
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
        },
        {
            "name": "retrieve_intent",
            "description": "Retrieve decision/convention/bug root-cause intent context",
            "inputSchema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    ]


def query_graph_tool(query: str) -> Dict[str, Any]:
    result = query_graph(query, use_natural_language=True)
    payload = {
        "results": result.data,
        "source": result.source,
        "duration_ms": result.duration_ms,
        "success": result.success,
        "error": result.error,
        "conventions_checked": result.conventions_checked,
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
            )
            for tool in list_tool_contracts()
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]):
        if name == "query_graph":
            return query_graph_tool(arguments["query"])
        if name == "get_dependencies":
            return get_dependencies_tool(
                file_path=arguments["file_path"],
                direction=arguments.get("direction", "both"),
                depth=arguments.get("depth", 1),
            )
        if name == "retrieve_intent":
            return retrieve_intent_tool(arguments["query"])
        raise ValueError(f"Unknown tool: {name}")

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
