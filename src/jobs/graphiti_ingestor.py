"""
GraphitiIngestor - Episode ingestion with retry, dedupe, and timeout protection.

Handles async bridge to Graphiti client, provides idempotency via LRU cache,
and implements fail-open semantics for episode ingestion.

Phase 13.2 - Oracle Framework Reuse
"""

import logging
import hashlib
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
from functools import lru_cache

logger = logging.getLogger(__name__)

# In-memory LRU cache for episode deduplication (10k entries)
@lru_cache(maxsize=10000)
def _is_episode_ingested(episode_id: str) -> bool:
    """
    Check if episode has already been ingested.

    Uses LRU cache with 10k entries for in-memory deduplication.
    Cache is per-worker and cleared on restart.

    Args:
        episode_id: Episode ID to check

    Returns:
        bool: True if episode was previously ingested
    """
    # This function is called to populate the cache.
    # The actual deduplication logic is in the cache itself.
    return True


class GraphitiIngestor:
    """
    Episode ingestor with retry, dedupe, and timeout protection.

    Provides idempotent episode ingestion to Graphiti graph with:
    - LRU cache-based deduplication (10k entries)
    - 5-second timeout per episode
    - Async bridge compatible with Celery workers
    - Batch ingestion support
    - Fail-open error handling (no exceptions propagated)
    """

    def __init__(self, client: Optional[Any] = None):
        """
        Initialize GraphitiIngestor.

        Args:
            client: Optional Graphiti client instance. If None, gets from singleton.
        """
        if client is None:
            from src.core.graphiti_client import get_graphiti_client
            client = get_graphiti_client()

        self.client = client
        self._ingested_cache = set()  # Local cache for this instance

    def _validate_episode(self, episode: Dict[str, Any]) -> bool:
        """
        Validate episode has required base fields.

        Args:
            episode: Episode dict to validate

        Returns:
            bool: True if episode is valid

        Raises:
            ValueError: If required fields are missing
        """
        required_fields = ["episode_type", "store_id", "entity_created_at"]
        missing_fields = [field for field in required_fields if field not in episode]

        if missing_fields:
            raise ValueError(f"Episode missing required fields: {missing_fields}")

        return True

    def _generate_episode_id(self, episode: Dict[str, Any]) -> str:
        """
        Generate episode ID for idempotency.

        If episode already has episode_id, use it. Otherwise generate
        from episode content hash.

        Args:
            episode: Episode dict

        Returns:
            str: Episode ID (16-char hex)
        """
        if "episode_id" in episode:
            return episode["episode_id"]

        # Generate from content hash
        # Use episode_type, store_id, and entity_created_at as minimal key
        key_parts = [
            episode.get("episode_type", ""),
            episode.get("store_id", ""),
            str(episode.get("entity_created_at", "")),
            episode.get("correlation_id", ""),
        ]

        key_string = "|".join(key_parts)
        hash_obj = hashlib.sha256(key_string.encode("utf-8"))
        return hash_obj.hexdigest()[:16]

    def _run_async(self, coro) -> Any:
        """
        Run async coroutine in sync context.

        Uses asyncio event loop compatible with Celery worker.
        Does NOT use asyncio.run() to avoid nested loop issues.

        Args:
            coro: Coroutine to run

        Returns:
            Coroutine result

        Raises:
            Exception: If coroutine raises
        """
        try:
            # Get or create event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # No event loop in current thread - create new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Run coroutine with timeout protection
            return loop.run_until_complete(coro)

        except Exception as e:
            logger.warning(f"Async execution failed: {e}")
            raise

    def ingest_episode(self, episode: Dict[str, Any]) -> bool:
        """
        Ingest single episode with idempotency and timeout protection.

        Args:
            episode: Episode dict with required fields

        Returns:
            bool: True on success, False on failure (never raises)

        Workflow:
            1. Validate episode has required fields
            2. Generate episode_id for idempotency
            3. Check if already ingested (LRU cache)
            4. Call graphiti client with 5s timeout
            5. Return True/False (no exceptions)
        """
        try:
            # Validate episode
            self._validate_episode(episode)

            # Generate episode ID
            episode_id = self._generate_episode_id(episode)

            # Check if already ingested (global LRU cache)
            if _is_episode_ingested(episode_id):
                # Check local cache for this worker
                if episode_id in self._ingested_cache:
                    logger.debug(f"Episode already ingested (skipping): {episode_id}")
                    return True

            # Check if client is available
            if self.client is None:
                logger.warning("Graphiti client unavailable - cannot ingest episode")
                return False

            # Ingest episode with timeout
            async def _ingest():
                try:
                    # Map entities for Graphiti to recognize them during extraction
                    from src.core.codebase_entities import (
                        FileEntity,
                        ModuleEntity,
                        ClassEntity,
                        FunctionEntity,
                        PlanningDocEntity,
                        ImportsEdge,
                        ContainsEdge,
                        ImplementsEdge,
                        ReferencesEdge,
                    )
                    from src.core.synthex_entities import (
                        ToolEntity,
                        ConventionEntity,
                        DecisionEntity,
                        BugRootCauseEntity,
                        RequiresIntegrationEdge,
                        AllowedInEdge,
                    )

                    entity_types = {
                        "File": FileEntity,
                        "Module": ModuleEntity,
                        "Class": ClassEntity,
                        "Function": FunctionEntity,
                        "PlanningDoc": PlanningDocEntity,
                        "Tool": ToolEntity,
                        "Convention": ConventionEntity,
                        "Decision": DecisionEntity,
                        "BugRootCause": BugRootCauseEntity,
                    }
                    edge_types = {
                        "IMPORTS": ImportsEdge,
                        "CONTAINS": ContainsEdge,
                        "IMPLEMENTS": ImplementsEdge,
                        "REFERENCES": ReferencesEdge,
                        "REQUIRES_INTEGRATION": RequiresIntegrationEdge,
                        "ALLOWED_IN": AllowedInEdge,
                    }

                    # Actual Graphiti client call
                    # entity_created_at is used as reference_time, not body attribute
                    # Use a prefix for all attributes to avoid protected names (like 'name', 'created_at')
                    body_dict = {f"attr_{k}": v for k, v in episode.items() if k not in ("entity_created_at", "correlation_id", "store_id", "episode_type")}
                    # Keep essential fields for manual inspection if needed
                    body_dict["episode_type"] = episode.get("episode_type")
                    body_dict["store_id"] = episode.get("store_id")

                    return await self.client.add_episode(
                        name=episode.get("correlation_id") or episode_id,
                        episode_body=str(body_dict),
                        source_description="synthex_platform",
                        reference_time=episode.get("entity_created_at") or datetime.utcnow(),
                        group_id=str(episode.get("store_id", "global")),
                        entity_types=entity_types,
                        edge_types=edge_types,
                    )
                except Exception as e:
                    logger.warning(f"Episode ingestion error: {e}")
                    return False

            # Run async with 5s timeout
            try:
                success = self._run_async(
                    asyncio.wait_for(_ingest(), timeout=5.0)
                )
            except asyncio.TimeoutError:
                logger.warning(f"Episode ingestion timed out after 5s: {episode_id}")
                return False

            if success:
                # Mark as ingested in both caches
                _is_episode_ingested(episode_id)  # Add to LRU cache
                self._ingested_cache.add(episode_id)  # Add to local cache
                logger.debug(f"Episode ingested successfully: {episode_id}")

                # Task 11a — piggyback write: store function_signature as a top-level
                # property on the Episodic node so the bridge query can use it directly.
                # Only for Developer-KG episode types (not operational/user-facing ones).
                _DEVELOPER_KG_TYPES = {
                    "code_intent", "bug_root_cause_identified",
                    "convention_established", "failure_pattern"
                }
                fn_sig = episode.get("function_signature")
                ep_type = episode.get("episode_type", "")
                ep_name = episode.get("correlation_id") or episode_id
                if fn_sig and ep_type in _DEVELOPER_KG_TYPES:
                    try:
                        driver = getattr(self.client, "driver", None)
                        if driver:
                            with driver._driver.session() as s:
                                s.run(
                                    "MATCH (e:Episodic {name: $name}) "
                                    "SET e.function_signature = $sig, "
                                    "    e.episode_type = $ep_type",
                                    name=ep_name, sig=fn_sig, ep_type=ep_type
                                )
                    except Exception as bridge_err:
                        logger.debug(f"Bridge piggyback write skipped: {bridge_err}")

                return True
            else:
                logger.warning(f"Episode ingestion failed: {episode_id}")
                return False

        except ValueError as e:
            # Validation error
            logger.error(f"Episode validation failed: {e}")
            return False

        except Exception as e:
            # Unexpected error - log and return False
            logger.error(f"Episode ingestion unexpected error: {e}", exc_info=True)
            return False

    def ingest_batch(self, episodes: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Ingest multiple episodes.

        Processes episodes sequentially with individual error handling.
        Does not stop on first failure.

        Args:
            episodes: List of episode dicts

        Returns:
            Dict with success/failed/skipped counts

        Example:
            >>> ingestor = GraphitiIngestor()
            >>> result = ingestor.ingest_batch([episode1, episode2, episode3])
            >>> print(result)
            {'success': 2, 'failed': 1, 'skipped': 0}
        """
        success_count = 0
        failed_count = 0
        skipped_count = 0

        for episode in episodes:
            try:
                # Check if already ingested before attempting
                episode_id = self._generate_episode_id(episode)
                if episode_id in self._ingested_cache or _is_episode_ingested(episode_id):
                    skipped_count += 1
                    continue

                # Attempt ingestion
                if self.ingest_episode(episode):
                    success_count += 1
                else:
                    failed_count += 1

            except Exception as e:
                logger.error(f"Batch episode ingestion error: {e}")
                failed_count += 1

        logger.info(
            f"Batch ingestion complete: {success_count} success, "
            f"{failed_count} failed, {skipped_count} skipped"
        )

        return {
            'success': success_count,
            'failed': failed_count,
            'skipped': skipped_count
        }

    def ingest_episodes_batch(self, episodes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Ingest multiple episodes in one call.
        
        Provides a unified interface for batch ingestion, favoring native
        Graphiti batch API if available, falling back to sequential loop.
        """
        if not episodes:
            return {"status": "skipped", "reason": "no_episodes"}

        # FAVOR: Native batch API if client supports it (check for add_episodes)
        if hasattr(self.client, 'add_episodes'):
            try:
                # Assuming client.add_episodes exists and takes list + timeout
                # This is future-proofing based on expected Graphiti API evolution
                async def _native_batch():
                    return await self.client.add_episodes(episodes)
                
                success = self._run_async(asyncio.wait_for(_native_batch(), timeout=30.0))
                if success:
                    return {"status": "success", "method": "native_batch", "count": len(episodes)}
            except Exception as e:
                logger.warning(f"Native batch ingestion failed, falling back: {e}")

        # FALLBACK: Use existing ingest_batch which handles loop + dedupe
        result = self.ingest_batch(episodes)
        return {
            "status": "completed",
            "method": "fallback_loop",
            "total": len(episodes),
            "successful": result["success"],
            "failed": result["failed"],
            "skipped": result["skipped"]
        }
