# 06-01 Summary: Schema and Model Invariants Foundation

## Completed
- Added Phase 6 migration: `migrations/versions/b7d5c4a9e8f1_phase6_ingest_chunks_audit_checkpoints.py`.
- Added models:
  - `src/models/ingest_chunk.py`
  - `src/models/audit_checkpoint.py`
- Extended `src/models/job.py` with:
  - `store_id`, `total_products`, `processed_count`, cancellation metadata
  - new statuses (`queued`, `cancel_requested`, `failed_terminal`)
  - ingest active-lock partial unique index
  - progress bounds check constraints.
- Updated model exports in `src/models/__init__.py`.

## Outcome
- DB now enforces chunk/checkpoint idempotency primitives:
  - `UNIQUE(job_id, chunk_idx)`
  - `UNIQUE(job_id, checkpoint)`
- Job-level invariants and ingest lock support Phase 6 state-machine semantics.

