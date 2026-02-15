"""Bulk chat orchestration helpers for chunking, concurrency, and progress."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha1
import re
from typing import Any

from src.models import Job, JobStatus, JobType, db
from src.models.chat_action import ChatAction
from src.resolution.throttle import AdaptiveThrottleController, parse_throttle_signal


MAX_BULK_SKUS = 1000
MAX_CHUNK_INPUTS = 250
DEFAULT_TARGET_CHUNK_SIZE = 100
MIN_TARGET_CHUNK_SIZE = 25
MAX_CONCURRENCY_CAP = 10

_SKU_PATTERN = re.compile(r"\b([A-Z0-9][A-Z0-9-]{2,63})\b", re.IGNORECASE)


class BulkPlanError(Exception):
    """Raised when bulk planning constraints fail."""

    def __init__(self, *, error_type: str, title: str, detail: str, status: int = 422):
        super().__init__(detail)
        self.error_type = error_type
        self.title = title
        self.detail = detail
        self.status = status


@dataclass(frozen=True)
class BulkChunk:
    """One deterministic chunk in a bulk chat plan."""

    chunk_id: str
    chunk_index: int
    skus: list[str]
    replay_key: str
    lineage: dict[str, Any]


@dataclass(frozen=True)
class BulkChunkPlan:
    """Deterministic bulk chunk plan with hard payload bounds."""

    normalized_skus: list[str]
    target_chunk_size: int
    max_chunk_inputs: int
    chunks: list[BulkChunk]

    @property
    def total_skus(self) -> int:
        return len(self.normalized_skus)

    def to_payload(self) -> dict[str, Any]:
        return {
            "total_skus": self.total_skus,
            "target_chunk_size": self.target_chunk_size,
            "max_chunk_inputs": self.max_chunk_inputs,
            "chunk_count": len(self.chunks),
            "chunks": [
                {
                    "chunk_id": chunk.chunk_id,
                    "chunk_index": chunk.chunk_index,
                    "sku_count": len(chunk.skus),
                    "skus": chunk.skus,
                    "replay_key": chunk.replay_key,
                    "lineage": chunk.lineage,
                }
                for chunk in self.chunks
            ],
        }


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_single_sku(value: str) -> str | None:
    candidate = str(value or "").strip().upper()
    if not candidate:
        return None
    if not _SKU_PATTERN.fullmatch(candidate):
        return None
    if candidate.startswith("-"):
        return None
    return candidate


def normalize_bulk_skus(raw_skus: list[str] | tuple[str, ...] | None) -> list[str]:
    """Normalize, validate, and deduplicate SKU inputs preserving first-seen order."""
    if raw_skus is None:
        raise BulkPlanError(
            error_type="missing-skus",
            title="Missing SKUs",
            detail="Bulk chat actions require at least one SKU.",
            status=422,
        )

    normalized: list[str] = []
    seen: set[str] = set()
    invalid: list[str] = []
    for raw in raw_skus:
        sku = _normalize_single_sku(raw)
        if sku is None:
            invalid.append(str(raw))
            continue
        if sku in seen:
            continue
        seen.add(sku)
        normalized.append(sku)

    if invalid:
        sample = ", ".join(invalid[:5])
        raise BulkPlanError(
            error_type="invalid-sku",
            title="Invalid SKU Inputs",
            detail=f"One or more SKU values are invalid: {sample}",
            status=422,
        )
    if not normalized:
        raise BulkPlanError(
            error_type="missing-skus",
            title="Missing SKUs",
            detail="Bulk chat actions require at least one valid SKU.",
            status=422,
        )
    if len(normalized) > MAX_BULK_SKUS:
        raise BulkPlanError(
            error_type="bulk-limit-exceeded",
            title="Bulk Limit Exceeded",
            detail=f"Bulk requests support up to {MAX_BULK_SKUS} unique SKUs.",
            status=422,
        )
    return normalized


def _target_chunk_size(total_skus: int, requested: int | None = None) -> int:
    if requested is not None:
        size = int(requested)
    elif total_skus <= 100:
        size = 50
    elif total_skus <= 500:
        size = 100
    else:
        size = 125
    size = max(MIN_TARGET_CHUNK_SIZE, min(size, DEFAULT_TARGET_CHUNK_SIZE if total_skus <= 500 else 125))
    return min(size, MAX_CHUNK_INPUTS)


def plan_chunks(*, raw_skus: list[str] | tuple[str, ...], requested_chunk_size: int | None = None) -> BulkChunkPlan:
    """Create a deterministic chunk plan with input hard bounds."""
    normalized = normalize_bulk_skus(raw_skus)
    chunk_size = _target_chunk_size(len(normalized), requested=requested_chunk_size)
    chunks: list[BulkChunk] = []
    for idx in range(0, len(normalized), chunk_size):
        chunk_skus = normalized[idx : idx + chunk_size]
        if len(chunk_skus) > MAX_CHUNK_INPUTS:
            raise BulkPlanError(
                error_type="chunk-limit-exceeded",
                title="Chunk Limit Exceeded",
                detail=f"Chunk payload cannot exceed {MAX_CHUNK_INPUTS} inputs.",
                status=422,
            )
        chunk_index = len(chunks)
        fingerprint = sha1(",".join(chunk_skus).encode("utf-8")).hexdigest()[:10]
        chunk_id = f"chunk-{chunk_index + 1:04d}-{fingerprint}"
        chunks.append(
            BulkChunk(
                chunk_id=chunk_id,
                chunk_index=chunk_index,
                skus=chunk_skus,
                replay_key=f"bulk:{chunk_id}",
                lineage={
                    "chunk_index": chunk_index,
                    "first_sku": chunk_skus[0],
                    "last_sku": chunk_skus[-1],
                    "sku_count": len(chunk_skus),
                },
            )
        )
    return BulkChunkPlan(
        normalized_skus=normalized,
        target_chunk_size=chunk_size,
        max_chunk_inputs=MAX_CHUNK_INPUTS,
        chunks=chunks,
    )


class AdaptiveBulkConcurrency:
    """Throttle-aware, bounded concurrency controller for chat bulk actions."""

    def __init__(
        self,
        *,
        initial: int = 3,
        min_concurrency: int = 1,
        max_concurrency: int = MAX_CONCURRENCY_CAP,
        admin_cap: int | None = None,
    ) -> None:
        hard_cap = max_concurrency if admin_cap is None else min(max_concurrency, max(1, int(admin_cap)))
        self._controller = AdaptiveThrottleController(
            initial_concurrency=max(min_concurrency, min(initial, hard_cap)),
            min_concurrency=min_concurrency,
            max_concurrency=hard_cap,
        )
        self._headroom_streak = 0
        self._min = min_concurrency
        self._hard_cap = hard_cap

    @property
    def current(self) -> int:
        return self._controller.current_concurrency

    @property
    def hard_cap(self) -> int:
        return self._hard_cap

    def observe(
        self,
        *,
        graphql_payload: dict[str, Any] | None = None,
        response_headers: dict[str, str] | None = None,
        throttled: bool = False,
    ) -> int:
        signal = parse_throttle_signal(
            graphql_payload=graphql_payload,
            response_headers=response_headers,
        )
        if throttled:
            self._headroom_streak = 0
            self._controller.current_concurrency = max(self._min, self.current - 2)
            return self.current

        if signal is None:
            return self.current
        if signal.utilization <= 0.40:
            self._headroom_streak += 1
        else:
            self._headroom_streak = 0

        self._controller.observe(signal)
        if signal.utilization <= 0.40 and self._headroom_streak >= 2:
            self._controller.current_concurrency = min(self._hard_cap, self.current + 1)
            self._headroom_streak = 0
        return self.current

    def bounded_for_queue(self, remaining_chunks: int) -> int:
        if remaining_chunks <= 0:
            return 0
        return max(self._min, min(self.current, remaining_chunks))

    def to_metadata(self) -> dict[str, Any]:
        return {"current": self.current, "hard_cap": self.hard_cap}


def create_or_get_bulk_job(
    *,
    action: ChatAction,
    total_items: int,
    chunk_count: int,
) -> Job:
    """Ensure a job row exists so progress uses canonical job contracts."""
    payload = dict(action.payload_json or {})
    job_id = payload.get("job_id")
    if isinstance(job_id, int):
        existing = Job.query.get(job_id)
        if existing is not None:
            return existing

    job = Job(
        user_id=action.user_id,
        store_id=action.store_id,
        job_type=JobType.PRODUCT_SYNC,
        job_name=f"chat_bulk_action_{action.id}",
        status=JobStatus.QUEUED,
        total_products=total_items,
        processed_count=0,
        total_items=total_items,
        processed_items=0,
        successful_items=0,
        failed_items=0,
        parameters={
            "source": "chat_bulk",
            "action_id": action.id,
            "chunk_count": chunk_count,
            "current_step": "queued",
        },
    )
    db.session.add(job)
    db.session.flush()

    payload["job_id"] = job.id
    action.payload_json = payload
    return job


def emit_bulk_job_progress(
    *,
    job: Job,
    current_step: str,
    processed_items: int,
    total_items: int,
    successful_items: int,
    failed_items: int,
    status: JobStatus,
    error_message: str | None = None,
) -> None:
    """Bridge bulk execution state into canonical job progress SSE payloads."""
    job.status = status
    job.total_products = total_items
    job.total_items = total_items
    job.processed_count = processed_items
    job.processed_items = processed_items
    job.successful_items = successful_items
    job.failed_items = failed_items
    job.error_message = error_message
    params = dict(job.parameters or {})
    params["current_step"] = current_step
    params["chat_bulk"] = {
        "processed_items": processed_items,
        "total_items": total_items,
    }
    job.parameters = params
    try:
        from src.jobs.progress import announce_job_progress

        announce_job_progress(job_id=job.id, job=job)
    except Exception:
        # Keep progress bridge non-fatal in stripped test/runtime environments.
        return


def summarize_chunk_results(chunk_results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Compute terminal summary counts from chunk results."""
    applied = 0
    conflicted = 0
    failed = 0
    skipped = 0
    recovery_log_ids: list[int] = []
    for result in chunk_results.values():
        status = str(result.get("status") or "")
        if status in {"completed", "applied"}:
            applied += int(result.get("applied_count", 0))
        elif status in {"partial", "conflicted"}:
            conflicted += int(result.get("conflicted_count", 0))
            applied += int(result.get("applied_count", 0))
        elif status == "failed":
            failed += int(result.get("failed_count", 0))
        elif status == "skipped":
            skipped += int(result.get("sku_count", 0))
        for raw_id in result.get("recovery_log_ids", []) or []:
            if isinstance(raw_id, int):
                recovery_log_ids.append(raw_id)
    return {
        "applied": applied,
        "conflicted": conflicted,
        "failed": failed,
        "skipped": skipped,
        "recovery_log_ids": sorted(set(recovery_log_ids)),
    }


def fair_chunk_order(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Interleave heavier and lighter chunks to avoid starvation under mixed durations.

    This is a deterministic ordering heuristic used before queueing/executing chunk work.
    """
    heavy: list[dict[str, Any]] = []
    light: list[dict[str, Any]] = []
    for chunk in chunks:
        sku_count = len(chunk.get("skus") or [])
        if sku_count > 50:
            heavy.append(chunk)
        else:
            light.append(chunk)

    ordered: list[dict[str, Any]] = []
    while heavy or light:
        if heavy:
            ordered.append(heavy.pop(0))
        if light:
            ordered.append(light.pop(0))
    return ordered
