"""
Celery tasks for asynchronous graph episode emission and FAILURE_JOURNEY sync.

Provides fire-and-forget episode ingestion to Neo4j via Graphiti client.
All tasks implement fail-open semantics: errors are logged but do not
propagate to callers.

Phase 13.2 - Oracle Framework Reuse
"""

import os
import logging
import json
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

from celery import group
from src.celery_app import app
from src.core.graphiti_client import get_graphiti_client, check_graph_availability
from src.core.synthex_entities import EpisodeType, create_episode_payload

logger = logging.getLogger(__name__)


def _generate_episode_id(
    episode_type: str,
    store_id: str,
    correlation_id: Optional[str],
    payload: Dict[str, Any]
) -> str:
    """
    Generate deterministic episode ID for idempotency.

    Uses hash of episode_type + store_id + correlation_id + key payload fields
    to create stable episode identifier for deduplication.

    Args:
        episode_type: Episode type string
        store_id: Store ID
        correlation_id: Optional correlation ID
        payload: Episode payload dict

    Returns:
        Hex-encoded SHA256 hash (first 16 chars)
    """
    # Build deterministic key from immutable fields
    key_parts = [
        episode_type,
        store_id,
        correlation_id or "null",
    ]

    # Add key payload fields based on episode type
    if episode_type == EpisodeType.ORACLE_DECISION.value:
        key_parts.extend([
            payload.get('decision', ''),
            payload.get('source_adapter', ''),
        ])
    elif episode_type == EpisodeType.FAILURE_PATTERN.value:
        key_parts.extend([
            payload.get('module_path', ''),
            payload.get('error_signature', ''),
        ])
    elif episode_type == EpisodeType.ENRICHMENT_OUTCOME.value:
        key_parts.extend([
            payload.get('product_id', ''),
            payload.get('profile_gear', ''),
        ])
    elif episode_type == EpisodeType.USER_APPROVAL.value:
        key_parts.extend([
            payload.get('action_id', ''),
            payload.get('user_id', ''),
        ])
    elif episode_type == EpisodeType.VENDOR_CATALOG_CHANGE.value:
        key_parts.extend([
            payload.get('vendor_id', ''),
        ])
    elif episode_type == EpisodeType.DECISION_RECORDED.value:
        key_parts.extend([
            payload.get('title', ''),
            payload.get('status', ''),
        ])
    elif episode_type == EpisodeType.CONVENTION_ESTABLISHED.value:
        key_parts.extend([
            payload.get('rule', ''),
            payload.get('scope', ''),
        ])
    elif episode_type == EpisodeType.BUG_ROOT_CAUSE_IDENTIFIED.value:
        key_parts.extend([
            payload.get('symptom', ''),
            payload.get('root_cause', ''),
        ])
    elif episode_type == EpisodeType.QUERY_REASONING_TRACE.value:
        key_parts.extend([
            payload.get('query_text', ''),
            payload.get('template_used', ''),
        ])
    elif episode_type == EpisodeType.GRAPH_DISCREPANCY.value:
        key_parts.extend([
            payload.get('query_text', ''),
            ','.join(payload.get('paths', [])[:3]) if isinstance(payload.get('paths'), list) else '',
        ])

    # Add temporal anchor
    key_parts.append(str(payload.get('entity_created_at', '')))

    # Generate stable hash
    key_string = '|'.join(str(part) for part in key_parts)
    hash_obj = hashlib.sha256(key_string.encode('utf-8'))
    return hash_obj.hexdigest()[:16]


@app.task(
    bind=True,
    name='src.tasks.graphiti_sync.emit_episode',
    queue='assistant.t1',
    max_retries=2,
    default_retry_delay=5
)
def emit_episode(
    self,
    episode_type: str,
    store_id: str,
    payload: Dict[str, Any],
    correlation_id: Optional[str] = None
) -> bool:
    """
    Emit episode to graph asynchronously.

    Fire-and-forget task that ingests episode into Graphiti graph.
    Implements fail-open semantics: returns False on error but does not
    propagate exceptions.

    Args:
        episode_type: Episode type from EpisodeType enum values
        store_id: Store ID for multi-tenant isolation
        payload: Episode payload dict with type-specific fields.
            Graph bridge contract (Task 10): Developer-KG episode types MUST include
            `function_signature` (format: "module.path.function_name") to enable
            (:Episode)-[:REFERS_TO]->(:Function) bridge edges in Task 11.
            Required for: CODE_INTENT (active), FAILURE_PATTERN (active),
            BUG_ROOT_CAUSE_IDENTIFIED (inactive — add when implementing),
            CONVENTION_ESTABLISHED (inactive — add when implementing).
        correlation_id: Optional correlation ID for lineage tracking

    Returns:
        bool: True on success, False on failure

    Retry behavior:
        - Retries on transient errors (connection, timeout)
        - Does NOT retry on validation errors
        - Max 2 retries with 5s delay
    """
    try:
        # Check if graph Oracle is enabled
        if not os.environ.get('GRAPH_ORACLE_ENABLED', 'false').lower() == 'true':
            logger.debug("Graph Oracle disabled - skipping episode emission")
            return False

        # Get Graphiti client
        client = get_graphiti_client()
        if client is None:
            logger.warning("Graphiti client unavailable - skipping episode emission")
            return False

        # Check graph availability
        if not check_graph_availability():
            logger.warning("Graph unavailable - skipping episode emission")
            return False

        # Generate episode ID for idempotency
        # Use entity_created_at if provided, else current time
        payload_with_time = dict(payload)
        if "entity_created_at" not in payload_with_time:
            payload_with_time["entity_created_at"] = datetime.utcnow()

        episode_id = _generate_episode_id(
            episode_type, store_id, correlation_id, payload_with_time
        )

        # Create full episode payload
        episode = create_episode_payload(
            EpisodeType(episode_type),
            store_id,
            episode_id=episode_id,
            correlation_id=correlation_id,
            **payload_with_time,
        )

        # Ingest episode via GraphitiIngestor
        from src.jobs.graphiti_ingestor import GraphitiIngestor
        ingestor = GraphitiIngestor(client=client)
        success = ingestor.ingest_episode(episode)

        if success:
            logger.info(f"Episode emitted successfully: {episode_type} (id={episode_id})")
        else:
            logger.warning(f"Episode emission failed: {episode_type} (id={episode_id})")

        return success

    except ValueError as e:
        # Validation error - do NOT retry
        logger.error(f"Episode validation error: {e}", exc_info=True)
        return False

    except Exception as e:
        # Transient error - retry
        logger.warning(f"Episode emission error (will retry): {e}")
        try:
            # Retry on connection/timeout errors
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f"Episode emission failed after max retries: {e}", exc_info=True)
            return False


@app.task(name="src.tasks.graphiti_sync.emit_episodes_batch", queue="assistant.t1")
def emit_episodes_batch(episodes_data: list[dict]) -> dict:
    """
    Emit multiple episodes using Celery group pattern.

    Args:
        episodes_data: List of dicts, each containing:
            - episode_type: str
            - store_id: str
            - payload: dict
            - correlation_id: Optional[str]
    """
    if not episodes_data:
        return {"status": "no_episodes"}

    # Chunk episodes (max 50 per chunk to prevent worker overload)
    CHUNK_SIZE = 50
    chunks = [episodes_data[i : i + CHUNK_SIZE] for i in range(0, len(episodes_data), CHUNK_SIZE)]

    total_queued = 0
    for chunk in chunks:
        tasks = [
            emit_episode.s(
                episode_type=ep.get("episode_type"),
                store_id=ep.get("store_id"),
                payload=ep.get("payload"),
                correlation_id=ep.get("correlation_id"),
            )
            for ep in chunk
        ]
        group(tasks).apply_async()
        total_queued += len(chunk)

    return {
        "status": "queued",
        "total_episodes": len(episodes_data),
        "chunks": len(chunks),
        "total_queued": total_queued,
    }


@app.task(
    name='src.tasks.graphiti_sync.sync_failure_journey',
    queue='assistant.t1'
)
def sync_failure_journey(store_id: str) -> Dict[str, int]:
    """
    Parse FAILURE_JOURNEY.md and emit failure pattern episodes.

    Reads FAILURE_JOURNEY.md from project root, extracts failure entries,
    and emits failure_pattern episodes for each unique failure. Tracks
    already-synced entries to avoid duplicates.

    Args:
        store_id: Store ID for multi-tenant isolation

    Returns:
        Dict with success/failed/skipped counts

    Format expected in FAILURE_JOURNEY.md:
        ## [YYYY-MM-DD HH:MM] Module: path.to.module
        Error: error message
        Context: additional context
    """
    try:
        # Check if graph Oracle is enabled
        if not os.environ.get('GRAPH_ORACLE_ENABLED', 'false').lower() == 'true':
            logger.debug("Graph Oracle disabled - skipping FAILURE_JOURNEY sync")
            return {'success': 0, 'failed': 0, 'skipped': 0}

        # Find FAILURE_JOURNEY.md
        journey_path = Path(__file__).parent.parent.parent / 'FAILURE_JOURNEY.md'
        if not journey_path.exists():
            logger.info("FAILURE_JOURNEY.md not found - nothing to sync")
            return {'success': 0, 'failed': 0, 'skipped': 0}

        # Read and parse file
        content = journey_path.read_text(encoding='utf-8')

        # Track synced entries (simple in-memory for now)
        # TODO: Persist synced entry hashes to avoid re-emitting on every call
        synced_count = 0
        failed_count = 0
        skipped_count = 0

        # Parse entries (simplified parser - looks for ## headers)
        lines = content.split("\n")
        current_entry = None
        episodes_to_emit = []

        for line in lines:
            # Look for failure entry headers
            if line.startswith("## [") and "Module:" in line:
                # Parse header: ## [2026-02-19 11:30] Module: src.tasks.enrichment
                try:
                    timestamp_str = line.split("[")[1].split("]")[0]
                    module_path = line.split("Module:")[1].strip()

                    current_entry = {"timestamp": timestamp_str, "module_path": module_path, "error_lines": []}
                except IndexError:
                    continue

            elif current_entry and line.startswith("Error:"):
                error_msg = line.replace("Error:", "").strip()
                current_entry["error_lines"].append(error_msg)

            elif current_entry and (line.startswith("##") or not line.strip()):
                # End of current entry - prepare episode
                if current_entry["error_lines"]:
                    # Generate error signature (hash of error message)
                    error_text = " ".join(current_entry["error_lines"])
                    error_signature = hashlib.sha256(error_text.encode()).hexdigest()[:16]

                    # Prepare failure pattern episode payload
                    # function_signature = module_path (best-effort; specific function
                    # not extractable from FAILURE_JOURNEY.md traceback format)
                    _mod = (current_entry["module_path"] or "").replace("/", ".").replace("\\", ".").replace(".py", "")
                    payload = {
                        "failure_type": "runtime_error",
                        "module_path": current_entry["module_path"],
                        "function_signature": _mod,  # Task 10: bridge key
                        "error_signature": error_signature,
                        "occurrence_count": 1,
                        "entity_created_at": datetime.utcnow(),
                    }

                    episodes_to_emit.append(
                        {
                            "episode_type": EpisodeType.FAILURE_PATTERN.value,
                            "store_id": store_id,
                            "payload": payload,
                            "correlation_id": f"failure_journey_{error_signature}",
                        }
                    )

                current_entry = None

        # Emit prepare episodes
        if len(episodes_to_emit) > 5:
            emit_episodes_batch.delay(episodes_to_emit)
            synced_count = len(episodes_to_emit)
        else:
            for ep in episodes_to_emit:
                success = emit_episode.delay(**ep)
                if success:
                    synced_count += 1
                else:
                    failed_count += 1

        logger.info(f"FAILURE_JOURNEY sync complete: {synced_count} success, {failed_count} failed")
        return {'success': synced_count, 'failed': failed_count, 'skipped': skipped_count}

    except Exception as e:
        logger.error(f"FAILURE_JOURNEY sync failed: {e}", exc_info=True)
        return {'success': 0, 'failed': 0, 'skipped': 0}
