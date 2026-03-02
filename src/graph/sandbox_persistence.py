"""Persistence helpers for sandbox verification metadata."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

logger = logging.getLogger(__name__)


def persist_sandbox_run(
    *,
    result: dict[str, Any],
    changed_files: dict[str, str],
    failure_fingerprint: Optional[str],
    remediation_type: str,
    confidence: Optional[float],
) -> None:
    try:
        from src.models import db
        from src.models.sandbox_runs import SandboxRun, SandboxVerdict

        verdict_enum = SandboxVerdict(str(result["verdict"]).lower())
        confidence_decimal = Decimal(str(confidence)) if confidence is not None else None

        row = SandboxRun(
            run_id=str(result["run_id"]),
            failure_fingerprint=failure_fingerprint,
            remediation_type=remediation_type,
            changed_files=changed_files,
            blast_radius_files=int(result.get("blast_radius_files", 0)),
            blast_radius_loc=int(result.get("blast_radius_loc", 0)),
            verdict=verdict_enum,
            gate_results=result.get("gate_results"),
            confidence=confidence_decimal,
            duration_ms=int(result.get("duration_ms", 0)),
            container_id=result.get("container_id"),
            logs=str(result.get("logs", ""))[:50000],
            completed_at=datetime.now(timezone.utc),
            rollback_notes=str(result.get("rollback_notes", "")),
        )
        db.session.add(row)
        db.session.commit()
    except Exception as exc:
        try:
            from src.models import db

            db.session.rollback()
        except Exception:
            pass
        logger.debug("Sandbox run persistence skipped: %s", exc)
