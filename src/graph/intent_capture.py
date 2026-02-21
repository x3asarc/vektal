"""
Intent capture and emission API for LLM-generated code.

Captures semantic meaning ("why") behind AI-generated code changes and
emits them as episodes to the knowledge graph.

Phase 14 - Codebase Knowledge Graph & Continual Learning
"""

import os
import logging
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from src.core.synthex_entities import EpisodeType
from src.tasks.graphiti_sync import emit_episode

logger = logging.getLogger(__name__)


@dataclass
class IntentRecord:
    """Semantic context for an LLM code generation event."""
    # What was created/modified
    file_path: str
    entity_type: str  # "file", "function", "class"
    entity_name: str

    # Why it was created (semantic meaning)
    intent: str  # Brief description of purpose
    reasoning: str  # Why this approach was chosen
    alternatives_considered: List[str] = field(default_factory=list)  # Other approaches rejected

    # Context
    phase: Optional[str] = None  # Phase being implemented
    plan: Optional[str] = None   # Plan being executed
    task: Optional[str] = None   # Task within plan
    user_request: Optional[str] = None  # Original user request

    # Metadata
    agent: str = "gemini"  # "claude", "codex", "gemini"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    confidence: float = 1.0  # How confident in approach (0.0-1.0)


def capture_intent(record: IntentRecord) -> None:
    """
    Capture intent for an LLM-generated change and emit it to the graph.
    
    Args:
        record: The IntentRecord to capture.
    """
    # 1. Log locally for immediate audit
    logger.info(f"[intent-capture] {record.agent} created {record.entity_type} {record.entity_name} in {record.file_path}")
    logger.debug(f"Intent: {record.intent}")
    logger.debug(f"Reasoning: {record.reasoning}")
    
    # 2. Emit as a graph episode (async, fire-and-forget)
    emit_intent_episode(record)


def emit_intent_episode(record: IntentRecord) -> None:
    """
    Emit an IntentRecord as a graph episode using existing infrastructure.
    
    Args:
        record: The IntentRecord to emit.
    """
    payload = {
        'file_path': record.file_path,
        'entity_type': record.entity_type,
        'entity_name': record.entity_name,
        'intent': record.intent,
        'reasoning': record.reasoning,
        'alternatives': record.alternatives_considered,
        'phase': record.phase,
        'plan': record.plan,
        'agent': record.agent,
        'created_at': record.timestamp.isoformat() if record.timestamp else None
    }
    
    # Use Celery task to emit episode asynchronously
    # Signature: emit_episode(self, episode_type, store_id, payload, correlation_id=None)
    try:
        emit_episode.delay(
            EpisodeType.CODE_INTENT.value,
            "codebase",
            payload,
            correlation_id=f"intent_{record.agent}_{record.timestamp.timestamp()}"
        )
    except Exception as e:
        # Fall-back to local logging if Celery is down
        logger.warning(f"Failed to queue intent episode: {e}")
