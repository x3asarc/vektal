"""
Neo4j connection health and recovery remediator.
Handles Neo4j connection failures with retry logic and exponential backoff.
"""

from __future__ import annotations
import asyncio
import logging
import os
from typing import Dict, Any, Optional
from src.graph.universal_fixer import UniversalRemediator, RemediationResult

logger = logging.getLogger(__name__)


class Neo4jHealthRemediator(UniversalRemediator):
    """Diagnose and fix Neo4j connection issues with intelligent retry."""

    @property
    def service_name(self) -> str:
        return "neo4j_health"

    @property
    def description(self) -> str:
        return "Diagnose and fix Neo4j connection issues with exponential backoff"

    def _neo4j_uri_candidates(self) -> list[str]:
        primary = (os.getenv("NEO4J_URI") or "").strip()
        fallback_raw = os.getenv("NEO4J_URI_FALLBACKS", "bolt://localhost:7687")
        fallbacks = [item.strip() for item in fallback_raw.split(",") if item.strip()]
        ordered = [uri for uri in [primary, *fallbacks] if uri]
        return list(dict.fromkeys(ordered))

    async def validate_environment(self) -> bool:
        """Check if neo4j module is available."""
        try:
            import neo4j  # noqa: F401
            return True
        except ImportError:
            logger.warning("neo4j module not available for Neo4j health remediation")
            return False

    async def diagnose_and_fix(
        self, params: Optional[Dict[str, Any]] = None
    ) -> RemediationResult:
        """Attempt to restore Neo4j connection with retries."""
        actions = ["neo4j_connection_probe"]

        # Get Neo4j configuration from environment
        uri_candidates = self._neo4j_uri_candidates()
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "")

        if not uri_candidates:
            return RemediationResult(
                False,
                "NEO4J_URI not configured in environment",
                actions + ["config_check_failed"],
                error_details="Missing NEO4J_URI environment variable",
            )

        if not password:
            logger.warning("NEO4J_PASSWORD is empty, connection may fail")

        logger.info(
            "Attempting Neo4j connection across %d URI candidate(s): %s",
            len(uri_candidates),
            uri_candidates,
        )

        # Try to connect with exponential backoff (3 attempts)
        max_attempts = 3
        last_error = None
        last_uri = ""

        for attempt in range(max_attempts):
            attempt_action = f"connection_attempt_{attempt + 1}"
            actions.append(attempt_action)

            for uri in uri_candidates:
                try:
                    # Import Neo4j driver
                    from neo4j import GraphDatabase

                    # Attempt connection with timeout
                    with GraphDatabase.driver(
                        uri,
                        auth=(user, password),
                        connection_timeout=5.0,
                        max_connection_lifetime=10.0,
                    ) as driver:
                        # Verify connectivity
                        driver.verify_connectivity()

                        # If successful, also try Graphiti client
                        try:
                            from src.core.graphiti_client import get_graphiti_client

                            client = get_graphiti_client()
                            if client:
                                actions.append("graphiti_client_validated")
                                logger.info("Graphiti client also validated")
                        except Exception as graphiti_error:
                            logger.warning(
                                "Neo4j connected but Graphiti client issue: %s",
                                graphiti_error,
                            )

                        return RemediationResult(
                            True,
                            f"Neo4j connection restored on attempt {attempt + 1}/{max_attempts}",
                            actions + ["connection_success"],
                            output=f"Connected to {uri}",
                        )

                except Exception as e:
                    last_error = e
                    last_uri = uri
                    error_msg = str(e)
                    logger.warning(
                        "Neo4j connection attempt %d/%d failed for %s: %s",
                        attempt + 1,
                        max_attempts,
                        uri,
                        error_msg,
                    )

            # If not last attempt, wait with exponential backoff
            if attempt < max_attempts - 1:
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                actions.append(f"backoff_wait_{wait_time}s")
                logger.info("Waiting %ds before retry...", wait_time)
                await asyncio.sleep(wait_time)

        # All attempts failed
        error_details = (
            f"Last URI {last_uri} error: {str(last_error)}"
            if last_error
            else "Unknown error"
        )

        # Check if it's a specific error type we can give guidance on
        error_type = type(last_error).__name__ if last_error else "Unknown"
        guidance = self._get_error_guidance(error_type, str(last_error))

        return RemediationResult(
            False,
            f"Neo4j still unreachable after {max_attempts} attempts. {guidance}",
            actions + ["all_attempts_failed"],
            error_details=error_details,
        )

    def _get_error_guidance(self, error_type: str, error_message: str) -> str:
        """Provide actionable guidance based on error type."""
        error_msg_lower = error_message.lower()

        if "authentication" in error_msg_lower or "unauthorized" in error_msg_lower:
            return "Check NEO4J_USER and NEO4J_PASSWORD credentials."

        if "connection refused" in error_msg_lower:
            return "Neo4j service may not be running. Try: docker compose up -d neo4j"

        if "unknown host" in error_msg_lower or "nodename" in error_msg_lower:
            return "Check NEO4J_URI hostname is correct."

        if "timeout" in error_msg_lower:
            return "Neo4j may be starting up or overloaded. Wait and retry."

        if "version" in error_msg_lower:
            return "Neo4j driver version may be incompatible with server."

        return "Check Neo4j logs for details: docker compose logs neo4j"
