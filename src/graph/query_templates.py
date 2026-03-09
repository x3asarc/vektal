"""
Pre-built Cypher query templates for knowledge graph operations.

Optimized for <100ms response time for 95% of common developer/AI queries.

Phase 14 - Codebase Knowledge Graph & Continual Learning
"""

import logging
import asyncio
import inspect
import threading
import os
import time
from typing import List, Dict, Any, Optional
from src.core.graphiti_client import get_graphiti_client
from src.graph.backend_resolver import runtime_backend_mode as _read_runtime_backend_mode
from src.graph.local_graph_store import query_template as local_query_template

logger = logging.getLogger(__name__)
_NEO4J_UNAVAILABLE_UNTIL = 0.0


def _runtime_backend_mode() -> str:
    return _read_runtime_backend_mode()


# Standard query templates (Cypher)
QUERY_TEMPLATES = {
    # File relationships
    "imports": """
        MATCH (f:File {path: $file_path})-[:IMPORTS]->(imported:File)
        RETURN imported.path as path, imported.purpose as purpose
    """,

    "imported_by": """
        MATCH (f:File {path: $file_path})<-[:IMPORTS]-(importer:File)
        RETURN importer.path as path, importer.purpose as purpose
    """,

    # Semantic similarity (vector search)
    "similar_files": """
        MATCH (f:File {path: $file_path})
        CALL db.index.vector.queryNodes('codebase_embeddings', $limit, f.embedding)
        YIELD node, score
        WHERE score > $threshold
        RETURN node.path as path, node.purpose as purpose, score
        ORDER BY score DESC
    """,

    # Planning context
    "planning_context": """
        MATCH (f:File {path: $file_path})-[:IMPLEMENTS]->(plan:PlanningDoc)
        RETURN plan.path as path, plan.phase_number as phase, plan.goal as goal
    """,

    "phase_code": """
        MATCH (plan:PlanningDoc {phase_number: $phase})<-[:IMPLEMENTS]-(f:File)
        RETURN f.path as path, f.purpose as purpose
    """,

    # Impact analysis
    "impact_radius": """
        MATCH path = (f:File {path: $file_path})<-[:IMPORTS*1..3]-(dependent:File)
        RETURN dependent.path as path, length(path) as depth
        ORDER BY depth
    """,

    # Failure patterns (for auto-improver)
    "similar_failures": """
        MATCH (e:Episode {episode_type: 'oracle_decision'})
        WHERE e.test_result = 'FAIL'
        AND e.root_cause STARTS WITH $root_cause_type
        RETURN e.root_cause as root_cause, e.suggested_fix as fix, e.phase as phase, e.plan as plan, e.created_at as created_at
        ORDER BY e.created_at DESC
        LIMIT $limit
    """,

    # Function lookup
    "function_callers": """
        MATCH (caller:Function)-[:CALLS]->(f:Function {full_name: $function_name})
        RETURN caller.full_name as full_name, caller.file_path as file_path
    """,

    "function_callees": """
        MATCH (f:Function {full_name: $function_name})-[:CALLS]->(callee:Function)
        RETURN callee.full_name as full_name, callee.file_path as file_path
    """,

    "functions_in_file": """
        MATCH (f:Function {file_path: $file_path})
        RETURN f.full_name as full_name, f.file_path as file_path
    """,

    "top_conventions": """
        MATCH (c:Convention)
        OPTIONAL MATCH ()-[:EXPLAINS]->(c)
        WITH c, count(*) as references
        RETURN c.rule as rule, c.scope as scope, c.enforcement as enforcement, references
        ORDER BY references DESC, c.rule ASC
        LIMIT $limit
    """,

    "long_term_patterns": """
        MATCH (lp:LongTermPattern)
        RETURN lp.description as description, lp.domain as domain, lp.task_id as task_id, lp.created_at as created_at
        ORDER BY lp.created_at DESC
        LIMIT $limit
    """,

    "recent_discrepancies": """
        MATCH (e:Episode {episode_type: 'graph_discrepancy'})
        RETURN e.query_text as query_text, e.paths as paths, e.created_at as created_at
        ORDER BY e.created_at DESC
        LIMIT $limit
    """,

    "tool_search": """
        CALL db.index.vector.queryNodes('tool_embedding_index', $top_k, $query_embedding)
        YIELD node, score
        WHERE node:Tool
        AND ($tier IS NULL OR EXISTS {
            MATCH (node)-[:ALLOWED_IN]->(tier:Tier {level: $tier})
        })
        RETURN node.name AS name,
               node.description AS description,
               node.schema_json AS schema,
               node.input_examples AS examples,
               score
        ORDER BY score DESC
        LIMIT $top_k
    """,

    "tool_search_text": """
        MATCH (t:Tool)
        WHERE (t.description CONTAINS $query OR t.name CONTAINS $query)
        AND ($tier IS NULL OR EXISTS {
            MATCH (t)-[:ALLOWED_IN]->(tier:Tier {level: $tier})
        })
        RETURN t.name AS name,
               t.description AS description,
               t.schema_json AS schema,
               t.input_examples AS examples,
               1.0 AS score
        LIMIT $top_k
    """
}


def _fallback_top_conventions(limit: int = 5) -> List[Dict[str, Any]]:
    try:
        from src.graph.convention_checker import load_default_conventions
    except Exception:
        return []
    conventions = load_default_conventions(limit=limit)
    return [
        {
            "rule": item.get("rule"),
            "scope": item.get("scope", "global"),
            "enforcement": item.get("enforcement", "advisory"),
            "references": 0,
        }
        for item in conventions
        if isinstance(item, dict) and item.get("rule")
    ]


def _execute_local_template_fallback(template_name: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = local_query_template(template_name, params)
    if rows:
        return rows
    if template_name == "top_conventions":
        limit = int(params.get("limit", 5) or 5)
        return _fallback_top_conventions(limit=limit)
    return []


def _neo4j_uri_candidates() -> List[str]:
    primary = (os.environ.get("NEO4J_URI") or "").strip()
    fallback_raw = os.environ.get("NEO4J_URI_FALLBACKS", "bolt://localhost:7687")
    fallbacks = [item.strip() for item in fallback_raw.split(",") if item.strip()]
    ordered = [uri for uri in [primary, *fallbacks] if uri]
    return list(dict.fromkeys(ordered))


def _neo4j_backoff_seconds() -> float:
    return float(os.environ.get("NEO4J_UNAVAILABLE_BACKOFF_SECONDS", "30"))


def _neo4j_temporarily_unavailable() -> bool:
    return time.time() < _NEO4J_UNAVAILABLE_UNTIL


def execute_template(template_name: str, params: Dict[str, Any], timeout_ms: int = 2000) -> List[Dict[str, Any]]:
    """
    Execute a pre-built query template.
    
    Args:
        template_name: Name of the template in QUERY_TEMPLATES.
        params: Parameters to inject into the Cypher query.
        timeout_ms: Execution timeout in milliseconds.
        
    Returns:
        List of result dictionaries.
    """
    if template_name not in QUERY_TEMPLATES:
        logger.error(f"Template not found: {template_name}")
        return []
        
    cypher = QUERY_TEMPLATES[template_name]

    def _records_to_dicts(records: Any) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for record in records or []:
            if isinstance(record, dict):
                rows.append(record)
            elif hasattr(record, "data"):
                rows.append(record.data())
        return rows

    def _run_async_with_timeout(coro: Any, timeout_seconds: float) -> List[Dict[str, Any]]:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(asyncio.wait_for(coro, timeout_seconds))

        result_holder: Dict[str, Any] = {}
        error_holder: Dict[str, Exception] = {}

        def _runner() -> None:
            try:
                result_holder["value"] = asyncio.run(asyncio.wait_for(coro, timeout_seconds))
            except Exception as exc:  # pragma: no cover - exercised in integration
                error_holder["error"] = exc

        thread = threading.Thread(target=_runner, daemon=True)
        thread.start()
        thread.join(timeout_seconds + 0.25)

        if thread.is_alive():
            raise TimeoutError(f"Query timed out after {timeout_seconds}s")
        if "error" in error_holder:
            raise error_holder["error"]
        return result_holder.get("value", [])

    def _execute_via_driver(driver: Any) -> List[Dict[str, Any]]:
        if not hasattr(driver, "execute_query"):
            raise AttributeError("driver.execute_query unavailable")

        # Standard Neo4j 5.x AsyncDriver.execute_query signature uses query_ and parameters_
        # We wrap the call to handle potential sync/async driver variations gracefully
        try:
            query_result = driver.execute_query(query_=cypher, parameters_=params)
        except TypeError:
            # Fallback for older drivers or different signatures
            try:
                query_result = driver.execute_query(cypher, params)
            except TypeError:
                try:
                    query_result = driver.execute_query(cypher, parameters=params)
                except TypeError:
                    query_result = driver.execute_query(cypher, params=params)

        if inspect.isawaitable(query_result):
            async def _await_query() -> List[Dict[str, Any]]:
                eager_result = await query_result
                return _records_to_dicts(getattr(eager_result, "records", []))
            return _run_async_with_timeout(_await_query(), timeout_ms / 1000.0)

        return _records_to_dicts(getattr(query_result, "records", []))

    def _execute_via_session(driver: Any) -> List[Dict[str, Any]]:
        session_candidate = driver.session()
        if hasattr(session_candidate, "__aenter__"):
            async def _run_async_session() -> List[Dict[str, Any]]:
                async with driver.session() as session:
                    cursor = await session.run(cypher, params)
                    if hasattr(cursor, "data"):
                        data = cursor.data()
                        if inspect.isawaitable(data):
                            return await data
                        return data
                    return []
            return _run_async_with_timeout(_run_async_session(), timeout_ms / 1000.0)

        with session_candidate as session:
            cursor = session.run(cypher, params)
            if hasattr(cursor, "data"):
                data = cursor.data()
                if isinstance(data, list):
                    return data
            return _records_to_dicts(cursor)

    def _execute_via_sync_neo4j_env() -> List[Dict[str, Any]]:
        global _NEO4J_UNAVAILABLE_UNTIL

        force_probe = os.environ.get("GRAPH_FORCE_NEO4J_PROBE", "false").lower() == "true"
        if _runtime_backend_mode() == "local_snapshot" and not force_probe:
            raise RuntimeError("Runtime backend pinned to local_snapshot")

        if _neo4j_temporarily_unavailable():
            raise RuntimeError("Neo4j temporarily unavailable in this runtime")

        uris = _neo4j_uri_candidates()
        user = os.environ.get("NEO4J_USER", "neo4j")
        password = os.environ.get("NEO4J_PASSWORD")
        if not uris or not password:
            raise RuntimeError("NEO4J_URI/NEO4J_PASSWORD missing for sync fallback")

        try:
            from neo4j import GraphDatabase  # Imported lazily to avoid hard dependency at import time
        except Exception as exc:
            raise RuntimeError(f"neo4j driver unavailable for sync fallback: {exc}") from exc

        last_error: Optional[Exception] = None
        connect_timeout = float(os.environ.get("NEO4J_CONNECT_TIMEOUT_SECONDS", "0.25"))
        for uri in uris:
            try:
                with GraphDatabase.driver(uri, auth=(user, password), connection_timeout=connect_timeout) as driver:
                    driver.verify_connectivity()
                    with driver.session() as session:
                        cursor = session.run(cypher, params)
                        _NEO4J_UNAVAILABLE_UNTIL = 0.0
                        return [record.data() for record in cursor]
            except Exception as exc:
                last_error = exc
                logger.debug("Sync Neo4j URI failed (%s): %s", uri, exc)
                continue

        _NEO4J_UNAVAILABLE_UNTIL = time.time() + _neo4j_backoff_seconds()
        raise RuntimeError(f"All Neo4j URI candidates failed: {last_error}")

    try:
        logger.debug(f"Executing template {template_name} with params {params}")
        force_probe = os.environ.get("GRAPH_FORCE_NEO4J_PROBE", "false").lower() == "true"
        runtime_mode = _runtime_backend_mode()
        prefer_sync = os.environ.get("GRAPH_TEMPLATE_PREFER_SYNC", "true").lower() == "true"
        graph_enabled = os.environ.get("GRAPH_ORACLE_ENABLED", "false").lower() == "true"

        if runtime_mode == "local_snapshot" and not force_probe:
            return _execute_local_template_fallback(template_name, params)

        if prefer_sync and graph_enabled:
            try:
                return _execute_via_sync_neo4j_env()
            except Exception as sync_error:
                logger.debug("Direct Neo4j sync path unavailable, trying Graphiti client: %s", sync_error)

        if _neo4j_temporarily_unavailable():
            client = get_graphiti_client()
            if client is None:
                return _execute_local_template_fallback(template_name, params)
        else:
            client = get_graphiti_client()
        if not client:
            if runtime_mode == "local_snapshot" and not force_probe:
                return _execute_local_template_fallback(template_name, params)
            logger.warning("Graphiti client unavailable - using direct Neo4j fallback for template %s", template_name)
            return _execute_via_sync_neo4j_env()

        driver = getattr(client, "driver", None)
        if driver is None:
            if runtime_mode == "local_snapshot" and not force_probe:
                return _execute_local_template_fallback(template_name, params)
            logger.warning("Graphiti client has no driver - using direct Neo4j fallback for template %s", template_name)
            return _execute_via_sync_neo4j_env()

        try:
            return _execute_via_driver(driver)
        except Exception as driver_error:
            logger.debug("execute_query path failed, falling back to session.run: %s", driver_error)
            try:
                return _execute_via_session(driver)
            except Exception as session_error:
                logger.debug("session.run path failed, falling back to direct Neo4j driver: %s", session_error)
                return _execute_via_sync_neo4j_env()
    except Exception as e:
        logger.error(f"Error executing template {template_name}: {e}")
        return _execute_local_template_fallback(template_name, params)
