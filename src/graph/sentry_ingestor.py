"""
Failure Event Ingestor (Phase 14.3).
Ingests normalized failure events into the knowledge graph and triggers the self-healing orchestrator.
"""

import os
import json
import logging
import asyncio
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any, Optional, List
from src.graph.root_cause_classifier import RootCauseClassifier, FailureCategory

logger = logging.getLogger(__name__)

@dataclass
class FailureEvent:
    event_id: str
    title: str
    category: str  # AURA_UNREACHABLE, LOCAL_NEO4J_START_FAIL, SNAPSHOT_CORRUPT, SYNC_TIMEOUT, UNKNOWN
    culprit: str
    timestamp: str
    tags: Dict[str, str]
    level: str = "error"
    is_remediated: bool = False

WHITELISTED_CATEGORIES = [
    "AURA_UNREACHABLE", 
    "LOCAL_NEO4J_START_FAIL", 
    "SNAPSHOT_CORRUPT", 
    "SYNC_TIMEOUT"
]

FAILURE_JOURNEY_PATH = "FAILURE_JOURNEY.md"

def _append_to_failure_journey(event: FailureEvent):
    """Logs the failure to FAILURE_JOURNEY.md for long-term learning."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    task_id = "14.3-self-healing"
    
    entry = f"\n### {date_str} | {task_id}\n"
    entry += f"1. Tried X: Autonomous execution of knowledge graph tools.\n"
    entry += f"2. Failed Y: {event.category}: {event.title} (Culprit: {event.culprit})\n"
    entry += f"3. Doing Z: Triggering autonomous remediator via orchestrate_healers.py\n"
    entry += f"4. Preventive rule added: none (automated ingestion)\n"
    
    try:
        with open(FAILURE_JOURNEY_PATH, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception as e:
        logger.error(f"Failed to append to FAILURE_JOURNEY.md: {e}")

async def _emit_graph_episode(event: FailureEvent):
    """Emits a Failure Ingested episode to the knowledge graph."""
    try:
        from src.jobs.graphiti_ingestor import GraphitiIngestor
        from src.core.synthex_entities import EpisodeType, create_episode_payload
        
        ingestor = GraphitiIngestor()
        episode = create_episode_payload(
            EpisodeType.SYSTEM_FAILURE,
            store_id="global",
            entity={
                "failure_id": event.event_id,
                "category": event.category,
                "title": event.title,
                "culprit": event.culprit,
                "level": event.level
            },
            correlation_id=f"failure-ingest-{event.event_id}",
            entity_created_at=datetime.fromisoformat(event.timestamp)
        )
        
        # Ingest in background
        await asyncio.to_thread(ingestor.ingest_episodes_batch, [episode])
    except Exception as e:
        logger.debug(f"Graph ingestion skipped (likely no client): {e}")

def normalize_sentry_issue(sentry_issue: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize raw Sentry payload into classifier-ready shape."""
    metadata = sentry_issue.get("metadata") or {}
    issue_id = str(
        sentry_issue.get("id")
        or sentry_issue.get("event_id")
        or sentry_issue.get("issue_id")
        or "unknown-issue"
    )
    error_type = str(
        sentry_issue.get("error_type")
        or metadata.get("type")
        or sentry_issue.get("type")
        or sentry_issue.get("title")
        or "UnknownError"
    )
    error_message = str(
        sentry_issue.get("error_message")
        or metadata.get("value")
        or sentry_issue.get("message")
        or sentry_issue.get("title")
        or ""
    )
    affected_module = str(
        sentry_issue.get("affected_module")
        or sentry_issue.get("culprit")
        or ""
    )
    traceback = str(
        sentry_issue.get("traceback")
        or sentry_issue.get("stacktrace")
        or affected_module
    )
    return {
        "issue_id": issue_id,
        "error_type": error_type,
        "error_message": error_message,
        "affected_module": affected_module,
        "traceback": traceback,
        "raw": sentry_issue,
    }


def _map_classifier_to_failure_category(classifier_category: str, normalized: Dict[str, Any]) -> str:
    """
    Bridge Phase 15 classifier output back to Phase 14.3 failure taxonomy.
    """
    text = (
        f"{normalized.get('error_type', '')} "
        f"{normalized.get('error_message', '')} "
        f"{normalized.get('affected_module', '')}"
    ).lower()

    if classifier_category == FailureCategory.INFRASTRUCTURE:
        if "snapshot" in text or "jsondecodeerror" in text or "filenotfound" in text:
            return "SNAPSHOT_CORRUPT"
        if "sync" in text or "celery" in text or "timeout" in text:
            return "SYNC_TIMEOUT"
        if "docker" in text or "connectionrefused" in text or "local neo4j" in text:
            return "LOCAL_NEO4J_START_FAIL"
        return "AURA_UNREACHABLE"

    if classifier_category == FailureCategory.CONFIG and "sync" in text:
        return "SYNC_TIMEOUT"

    return "UNKNOWN"


def _build_failure_event_from_issue(
    normalized: Dict[str, Any],
    failure_category: str,
    classifier_category: str,
    confidence: float,
) -> FailureEvent:
    return FailureEvent(
        event_id=normalized["issue_id"],
        title=normalized.get("error_message") or normalized.get("error_type") or "Unknown issue",
        category=failure_category,
        culprit=normalized.get("affected_module") or "unknown",
        timestamp=datetime.utcnow().isoformat(),
        tags={
            "classifier_category": classifier_category,
            "confidence": str(round(float(confidence), 3)),
        },
        level="error",
    )


async def ingest_sentry_issue(
    sentry_issue: Dict[str, Any],
    *,
    classifier: Optional[RootCauseClassifier] = None,
) -> bool:
    """
    End-to-end intake: normalize -> classify -> ingest -> orchestrate.
    """
    normalized = normalize_sentry_issue(sentry_issue)
    classifier = classifier or RootCauseClassifier()
    category, confidence, evidence = classifier.classify(
        error_type=normalized["error_type"],
        error_message=normalized["error_message"],
        traceback=normalized["traceback"],
        affected_module=normalized["affected_module"],
    )
    normalized["category"] = category
    normalized["confidence"] = float(confidence)
    normalized["evidence"] = evidence

    failure_category = _map_classifier_to_failure_category(category, normalized)
    event = _build_failure_event_from_issue(normalized, failure_category, category, confidence)
    return await ingest_failure_event(event, normalized_issue=normalized)


async def ingest_failure_event(event: FailureEvent, normalized_issue: Optional[Dict[str, Any]] = None) -> bool:
    """Ingests a normalized failure and triggers the healing pipeline."""
    logger.info("[SentryIngestor] Ingesting %s failure: %s", event.category, event.event_id)
    
    # 1. Log to FAILURE_JOURNEY.md
    _append_to_failure_journey(event)
    
    # 2. Emit Graph Episode
    await _emit_graph_episode(event)
    
    # 3. Trigger Orchestrator if whitelisted
    if event.category in WHITELISTED_CATEGORIES:
        logger.info("[SentryIngestor] Triggering autonomous healing for %s...", event.category)
        try:
            command: List[str] = [sys.executable, "scripts/graph/orchestrate_healers.py"]
            if normalized_issue:
                command.extend(["--issue-json", json.dumps(normalized_issue)])
            else:
                command.extend(["--category", event.category, "--event_id", event.event_id])
            await asyncio.create_subprocess_exec(
                *command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception as e:
            logger.error("[SentryIngestor] Failed to trigger orchestrator: %s", e)
            return False
            
    return True
