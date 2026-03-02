"""Classification-aware remediation orchestration."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from src.graph.root_cause_classifier import RootCauseClassifier, FailureCategory
from src.graph.remediation_registry import registry as default_registry
from src.graph.universal_fixer import NanoFixerLoop, RemediationResult

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTCOME_LOG_PATH = REPO_ROOT / ".graph" / "remediation-outcomes.jsonl"

CATEGORY_SERVICE_MAP = {
    "AURA_UNREACHABLE": "aura",
    "LOCAL_NEO4J_START_FAIL": "docker",
    "SNAPSHOT_CORRUPT": "local_snapshot",
    "SYNC_TIMEOUT": "graph_sync",
}


def normalize_sentry_issue(sentry_issue: dict[str, Any]) -> dict[str, Any]:
    """Normalize varied Sentry payload shapes to a stable internal schema."""
    issue_id = str(
        sentry_issue.get("id")
        or sentry_issue.get("event_id")
        or sentry_issue.get("issue_id")
        or "unknown-issue"
    )
    error_type = str(
        sentry_issue.get("error_type")
        or sentry_issue.get("exception_type")
        or (sentry_issue.get("metadata") or {}).get("type")
        or sentry_issue.get("type")
        or sentry_issue.get("category")
        or "UnknownError"
    )
    error_message = str(
        sentry_issue.get("error_message")
        or sentry_issue.get("message")
        or (sentry_issue.get("metadata") or {}).get("value")
        or sentry_issue.get("title")
        or ""
    )
    traceback = str(
        sentry_issue.get("traceback")
        or sentry_issue.get("stacktrace")
        or sentry_issue.get("culprit")
        or ""
    )
    affected_module = str(
        sentry_issue.get("affected_module")
        or sentry_issue.get("module")
        or sentry_issue.get("culprit")
        or ""
    )
    category = sentry_issue.get("category")

    return {
        "issue_id": issue_id,
        "error_type": error_type,
        "error_message": error_message,
        "traceback": traceback,
        "affected_module": affected_module,
        "category": category,
        "raw": sentry_issue,
    }


def route_service_for_classification(category: str, normalized: dict[str, Any]) -> str | None:
    """Map classification + error details to a concrete remediator service name."""
    message = f"{normalized.get('error_message', '')} {normalized.get('affected_module', '')}".lower()
    event_category = str(normalized.get("category") or "").strip().upper()

    if event_category in CATEGORY_SERVICE_MAP:
        return CATEGORY_SERVICE_MAP[event_category]

    if category == FailureCategory.INFRASTRUCTURE:
        if "redis" in message:
            return "redis"
        if "aura" in message:
            return "aura"
        if "snapshot" in message:
            return "local_snapshot"
        if "sync" in message:
            return "graph_sync"
        return "docker"

    if category == FailureCategory.CODE:
        return "code_fix"

    if category == FailureCategory.CONFIG:
        if "redis" in message:
            return "redis"
        if "graph" in message or "sync" in message:
            return "graph_sync"
        return "docker"

    return None


def record_remediation_outcome(
    *,
    issue_id: str,
    category: str,
    confidence: float,
    status: str,
    service: str | None,
    evidence: dict[str, Any],
) -> None:
    """Persist orchestration outcome for later learning-loop phases."""
    OUTCOME_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "ts": int(time.time()),
        "issue_id": issue_id,
        "category": category,
        "confidence": round(float(confidence), 3),
        "status": status,
        "service": service,
        "evidence": evidence,
    }
    with OUTCOME_LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, default=str) + "\n")


async def orchestrate_remediation(
    sentry_issue: dict[str, Any],
    *,
    classifier: RootCauseClassifier | None = None,
    fixer: NanoFixerLoop | None = None,
    registry: Any = None,
) -> dict[str, Any]:
    """
    Orchestrate remediation with root-cause classification and routed dispatch.
    """
    normalized = normalize_sentry_issue(sentry_issue)
    classifier = classifier or RootCauseClassifier()
    registry_instance = registry or default_registry
    fixer = fixer or NanoFixerLoop(registry_instance)

    category, confidence, evidence = classifier.classify(
        error_type=normalized["error_type"],
        error_message=normalized["error_message"],
        traceback=normalized["traceback"],
        affected_module=normalized["affected_module"],
    )

    service = route_service_for_classification(category, normalized)
    if not service:
        status = "manual_required"
        record_remediation_outcome(
            issue_id=normalized["issue_id"],
            category=category,
            confidence=confidence,
            status=status,
            service=None,
            evidence=evidence,
        )
        return {
            "status": status,
            "category": category,
            "confidence": confidence,
            "evidence": evidence,
            "issue_id": normalized["issue_id"],
        }

    try:
        params = {
            "error_type": normalized["error_type"],
            "error_message": normalized["error_message"],
            "affected_module": normalized["affected_module"],
            "classification_evidence": evidence,
        }
        result: RemediationResult = await fixer.fix_service(service, params=params)
        status = "remediated" if result.success else "failed"
        payload = {
            "status": status,
            "category": category,
            "confidence": confidence,
            "service": service,
            "issue_id": normalized["issue_id"],
            "evidence": evidence,
            "result": {
                "success": result.success,
                "message": result.message,
                "actions_taken": result.actions_taken,
                "error_details": result.error_details,
            },
        }
        record_remediation_outcome(
            issue_id=normalized["issue_id"],
            category=category,
            confidence=confidence,
            status=status,
            service=service,
            evidence=evidence,
        )
        return payload
    except Exception as exc:
        logger.error("Remediation dispatch failed for %s: %s", service, exc)
        status = "failed"
        record_remediation_outcome(
            issue_id=normalized["issue_id"],
            category=category,
            confidence=confidence,
            status=status,
            service=service,
            evidence={**evidence, "dispatch_error": str(exc)},
        )
        return {
            "status": status,
            "category": category,
            "confidence": confidence,
            "service": service,
            "issue_id": normalized["issue_id"],
            "error": str(exc),
            "evidence": evidence,
        }


async def orchestrate_healing(category: str, event_id: str | None = None) -> bool:
    """
    Backward-compatible category-based entrypoint used by phase 14.3 scripts.
    """
    synthetic_issue = {
        "id": event_id or f"event-{int(time.time())}",
        "category": category,
        "error_type": category,
        "error_message": category.replace("_", " ").lower(),
        "affected_module": "src/graph",
        "traceback": "",
    }
    result = await orchestrate_remediation(synthetic_issue)
    return result.get("status") == "remediated"
