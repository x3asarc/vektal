import asyncio
import logging
from typing import Any, Dict, List
from src.graph.query_interface import query_graph
from src.core.embeddings import generate_embedding

logger = logging.getLogger(__name__)

async def batch_query_handler(queries: List[str], aggregate_mode: str = "separate") -> Dict[str, Any]:
    """Execute multiple graph queries, return aggregated results."""
    
    async def _run_query(query: str, index: int):
        try:
            # query_graph is sync, run in thread to avoid blocking loop
            result = await asyncio.to_thread(query_graph, query)
            return {
                "index": index, 
                "query": query, 
                "data": result.data, 
                "success": result.success,
                "source": result.source,
                "status": "success"
            }
        except Exception as e:
            return {"index": index, "query": query, "error": str(e), "status": "error"}

    tasks = [_run_query(q, i) for i, q in enumerate(queries)]
    responses = await asyncio.gather(*tasks)

    results = []
    errors = []
    
    for resp in responses:
        if resp["status"] == "success":
            results.append(resp)
        else:
            errors.append(resp)

    if aggregate_mode == "merged":
        # Combine all data into a flat list
        merged_data = []
        seen_paths = set()
        for r in results:
            for item in r.get("data", []):
                if isinstance(item, dict) and "path" in item:
                    if item["path"] not in seen_paths:
                        merged_data.append(item)
                        seen_paths.add(item["path"])
                else:
                    merged_data.append(item)

        return {
            "mode": "merged",
            "total_queries": len(queries),
            "successful": len(results),
            "failed": len(errors),
            "results": merged_data,
            "errors": errors if errors else None
        }

    return {
        "mode": "separate",
        "total_queries": len(queries),
        "successful": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors if errors else None
    }


async def batch_dependencies_handler(file_paths: List[str], direction: str = "both", depth: int = 1) -> Dict[str, Any]:
    """Get dependencies for multiple files, return combined map."""
    from src.graph.mcp_server import get_dependencies_tool
    
    async def _get_deps(file_path: str):
        try:
            # reuse existing sync tool logic in thread
            result = await asyncio.to_thread(get_dependencies_tool, file_path, direction, depth)
            return {"file": file_path, "data": result, "status": "success"}
        except Exception as e:
            return {"file": file_path, "error": str(e), "status": "error"}

    tasks = [_get_deps(fp) for fp in file_paths]
    responses = await asyncio.gather(*tasks)

    combined_dependencies = []
    seen_deps = set()
    errors = []
    
    for resp in responses:
        if resp["status"] == "success":
            # get_dependencies_tool returns a dict with 'dependencies' key
            deps = resp["data"].get("dependencies", [])
            for dep in deps:
                key = (dep.get("path"), dep.get("purpose"))
                if key not in seen_deps:
                    combined_dependencies.append(dep)
                    seen_deps.add(key)
        else:
            errors.append(resp)

    return {
        "total_files": len(file_paths),
        "successful": len(file_paths) - len(errors),
        "failed": len(errors),
        "combined_dependencies": combined_dependencies,
        "impact_radius": len(seen_deps),
        "errors": errors if errors else None
    }
