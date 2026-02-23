"""
MCP server exposing knowledge graph tools for Claude Code.
"""

import asyncio
from typing import Any, Dict, List

from src.graph.query_interface import query_graph

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
    return {
        "results": result.data,
        "source": result.source,
        "duration_ms": result.duration_ms,
        "success": result.success,
        "error": result.error,
    }


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
    return {
        "file": file_path,
        "dependencies": list(dedup.values()),
        "direction": direction,
        "depth": depth,
        "impact_radius": len(dedup),
    }


def retrieve_intent_tool(query: str) -> Dict[str, Any]:
    result = query_graph(query, use_natural_language=True)
    return {
        "results": result.data,
        "source": result.source,
        "confidence": 0.7 if result.data else 0.0,
    }


async def run_server() -> None:
    if not MCP_AVAILABLE:
        raise RuntimeError("MCP SDK is not available. Install 'mcp' dependency first.")

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
