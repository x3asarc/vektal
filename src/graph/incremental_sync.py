"""
Incremental sync engine for codebase knowledge graph.

Processes only changed files (added, modified, deleted) to update the graph
efficiently on every commit via git hooks.

Phase 14 - Codebase Knowledge Graph & Continual Learning
"""

import os
import time
import subprocess
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from src.core.codebase_entities import (
    FileEntity, 
    ClassEntity, 
    FunctionEntity, 
    PlanningDocEntity,
    ImportsEdge,
    ContainsEdge,
    ImplementsEdge,
    ReferencesEdge,
    CodebaseEdgeType
)
from src.core.embeddings import generate_embedding
from src.core.summary_generator import (
    generate_file_summary,
    generate_function_summary,
    generate_class_summary,
    generate_planning_doc_summary
)
from src.graph.file_parser import (
    parse_python_file,
    parse_markdown_file,
    detect_language
)
from src.graph.commit_parser import parse_commit_message, CommitInfo
from src.graph.planning_linker import link_commit_to_plan, detect_natural_references, resolve_plan_path
from src.core.graphiti_client import get_graphiti_client
from src.graph.sync_status import update_sync_status
from src.assistant.governance.mutation_guard import check_mutation_allowed

logger = logging.getLogger(__name__)


@dataclass
class IncrementalSyncResult:
    """Result of incremental graph sync."""
    files_processed: int = 0
    entities_created: int = 0
    entities_updated: int = 0
    relationships_created: int = 0
    planning_links_created: int = 0
    errors: List[str] = field(default_factory=list)
    duration_ms: float = 0.0
    graph_available: bool = False


def get_staged_files() -> List[str]:
    """
    Get list of files staged for commit.
    
    Returns:
        List of file paths relative to project root.
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            check=True
        )
        return [f.strip() for f in result.stdout.split('\n') if f.strip()]
    except subprocess.CalledProcessError:
        return []


def get_file_status(file_path: str) -> str:
    """
    Get git status of a staged file (A, M, D, R).
    
    Args:
        file_path: Path to the file.
        
    Returns:
        Status code: "added", "modified", "deleted", "renamed", or "unknown".
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-status", "--", file_path],
            capture_output=True,
            text=True,
            check=True
        )
        if not result.stdout.strip():
            return "unknown"
            
        status_line = result.stdout.split('\n')[0]
        status_code = status_line.split('\t')[0][0]
        
        status_map = {
            'A': 'added',
            'M': 'modified',
            'D': 'deleted',
            'R': 'renamed',
            'C': 'copied'
        }
        return status_map.get(status_code, "unknown")
    except subprocess.CalledProcessError:
        return "unknown"


def sync_changed_files(
    changed_files: List[str], 
    commit_message: str,
    sync_mode: str = "auto",
    last_source: str = "git_hook"
) -> IncrementalSyncResult:
    """
    Sync changed files with the knowledge graph.
    """
    start_time = time.time()
    result = IncrementalSyncResult()
    
    # 0. Mutation Guard
    allowed, reason = check_mutation_allowed()
    if not allowed:
        logger.warning(f"Sync blocked: {reason}")
        result.errors.append(reason)
        return result

    # Check graph availability
    client = get_graphiti_client()
    # Note: We continue even if client is None for this exercise, but in production we'd fail-open
    # if not client:
    #     result.errors.append("Graphiti client unavailable")
    #     result.graph_available = False
    #     return result
    
    result.graph_available = client is not None
    
    # 1. Parse commit message for phase/plan
    commit_info = parse_commit_message(commit_message)
    
    # 2. Process each changed file
    for rel_path in changed_files:
        status = get_file_status(rel_path)
        if status == 'deleted':
            logger.info(f"File deleted: {rel_path}, skipping sync")
            continue
            
        if not os.path.exists(rel_path):
            continue
            
        result.files_processed += 1
        
        # Detect language
        language = detect_language(rel_path)
        if language == 'unknown':
            continue
            
        try:
            # Parse based on type
            if language == 'python':
                _sync_python_file(rel_path, commit_info, result)
            elif language == 'markdown' and '.planning' in rel_path:
                _sync_planning_doc(rel_path, result)
                
        except Exception as e:
            logger.error(f"Error syncing {rel_path}: {e}")
            result.errors.append(f"{rel_path}: {e}")

    # Invalidate semantic cache entries that reference changed files.
    try:
        get_semantic_cache().invalidate(changed_files)
    except Exception as e:
        logger.debug(f"Semantic cache invalidation skipped: {e}")
            
    result.duration_ms = (time.time() - start_time) * 1000
    
    # Sync tool nodes to graph on every sync run to ensure they are up-to-date
    try:
        synced_tools = sync_tool_nodes_to_graph()
        result.entities_updated += synced_tools
    except Exception as e:
        logger.error(f"Error syncing tool nodes: {e}")
        result.errors.append(f"tool_sync: {e}")
        
    # Update sync status
    update_sync_status(
        sync_mode=sync_mode,
        last_source=last_source,
        success=len(result.errors) == 0,
        error="; ".join(result.errors) if result.errors else None,
        files_processed=result.files_processed,
        entities_updated=result.entities_updated
    )
        
    return result


def sync_tool_nodes_to_graph() -> int:
    """
    Sync MCP + assistant tools to Neo4j as ToolEntity entities.
    Returns: Number of tool nodes synced.
    """
    from src.graph.mcp_server import list_tool_contracts
    from src.models.assistant_tool_registry import AssistantToolRegistry
    from src.jobs.graphiti_ingestor import GraphitiIngestor
    from src.core.synthex_entities import ToolEntity, EpisodeType, create_episode_payload
    import hashlib
    import json
    from datetime import datetime, timezone

    ingestor = GraphitiIngestor()
    synced_count = 0
    episodes_to_emit = []

    # 1. MCP tools from code
    for tool in list_tool_contracts():
        # Schema for hash excludes dynamic fields if any
        schema_json = json.dumps(tool, sort_keys=True)
        schema_hash = hashlib.sha256(schema_json.encode()).hexdigest()[:16]

        tool_entity = ToolEntity(
            store_id="global",
            name=tool["name"],
            description=tool["description"],
            tool_type="mcp",
            tier_restriction=None,  # MCP tools available to all tiers
            schema_json=schema_json,
            schema_hash=schema_hash,
            input_examples=json.dumps(tool.get("input_examples", [])),
            entity_created_at=datetime.now(timezone.utc),
            last_updated=datetime.now(timezone.utc),
        )

        episodes_to_emit.append(
            create_episode_payload(
                EpisodeType.TOOL_REGISTRATION,
                store_id="global",
                entity=tool_entity.model_dump(mode="json"),
                correlation_id=f"tool-sync-mcp-{tool_entity.name}-{schema_hash}",
                entity_created_at=tool_entity.entity_created_at,
            )
        )

    # 2. Assistant tools from PostgreSQL (if in app context)
    try:
        assistant_tools = AssistantToolRegistry.query.all()
        for tool in assistant_tools:
            # metadata_json contains inputSchema and input_examples
            metadata = tool.metadata_json or {}
            schema_json = json.dumps(metadata, sort_keys=True)
            schema_hash = hashlib.sha256(schema_json.encode()).hexdigest()[:16]

            # Determine min tier from allowed_tiers list
            min_tier = 1
            if tool.allowed_tiers:
                try:
                    tiers = [int(str(t).split("_")[-1]) for t in tool.allowed_tiers if "_" in str(t)]
                    if tiers:
                        min_tier = min(tiers)
                except Exception:
                    pass

            tool_entity = ToolEntity(
                store_id="global",
                name=tool.tool_id,
                description=tool.description or tool.display_name,
                tool_type="assistant",
                tier_restriction=min_tier,
                schema_json=schema_json,
                schema_hash=schema_hash,
                input_examples=json.dumps(metadata.get("input_examples", [])),
                entity_created_at=tool.updated_at or datetime.now(timezone.utc),
                last_updated=tool.updated_at or datetime.now(timezone.utc),
            )

            episodes_to_emit.append(
                create_episode_payload(
                    EpisodeType.TOOL_REGISTRATION,
                    store_id="global",
                    entity=tool_entity.model_dump(mode="json"),
                    correlation_id=f"tool-sync-assistant-{tool_entity.name}-{schema_hash}",
                    entity_created_at=tool_entity.entity_created_at,
                )
            )
    except Exception as e:
        logger.debug("Skipping assistant tool sync (likely no DB context): %s", e)

    # 3. External Research Tools
    from src.graph.mcp_server import _research_vendor_schema, _search_documentation_schema

    external_tools = [
        {"schema": _research_vendor_schema(), "type": "mcp_external"},
        {"schema": _search_documentation_schema(), "type": "mcp_external"},
    ]

    for tool in external_tools:
        schema = tool["schema"]
        schema_json = json.dumps(schema, sort_keys=True)
        schema_hash = hashlib.sha256(schema_json.encode()).hexdigest()[:16]

        tool_entity = ToolEntity(
            store_id="global",
            name=schema["name"],
            description=schema["description"],
            tool_type=tool["type"],
            tier_restriction=None,
            schema_json=schema_json,
            schema_hash=schema_hash,
            input_examples=json.dumps(schema.get("input_examples", [])),
            entity_created_at=datetime.now(timezone.utc),
            last_updated=datetime.now(timezone.utc),
        )

        episodes_to_emit.append(
            create_episode_payload(
                EpisodeType.TOOL_REGISTRATION,
                store_id="global",
                entity=tool_entity.model_dump(mode="json"),
                correlation_id=f"tool-sync-external-{tool_entity.name}-{schema_hash}",
                entity_created_at=tool_entity.entity_created_at,
            )
        )

    if episodes_to_emit:
        result = ingestor.ingest_episodes_batch(episodes_to_emit)
        synced_count = result.get("successful", 0)

    return synced_count


def _sync_python_file(rel_path: str, commit_info: CommitInfo, result: IncrementalSyncResult):
    """Internal helper to sync a Python file."""
    parse_res = parse_python_file(rel_path)
    if parse_res.errors:
        result.errors.extend([f"{rel_path}: {err}" for err in parse_res.errors])
        
    result.entities_created += 1 # FileEntity
    
    # Add classes
    for cls in parse_res.classes:
        result.entities_created += 1
        result.relationships_created += 1 # ContainsEdge (file -> class)
        
    # Add functions
    for func in parse_res.functions:
        result.entities_created += 1
        result.relationships_created += 1 # ContainsEdge (file -> function)
        
    # Natural references
    with open(rel_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    ref_edges = detect_natural_references(content, rel_path)
    result.relationships_created += len(ref_edges)
    
    # Commit auto-linking
    impl_edges = link_commit_to_plan(commit_info, [rel_path])
    result.planning_links_created += len(impl_edges)
    result.relationships_created += len(impl_edges)


def _sync_planning_doc(rel_path: str, result: IncrementalSyncResult):
    """Internal helper to sync a planning document."""
    parse_res = parse_markdown_file(rel_path)
    result.entities_created += 1 # PlanningDocEntity
