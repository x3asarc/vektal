"""Persistence invariants tests for restart safety."""

from src.models import AuditCheckpoint, IngestChunk


def test_ingest_chunk_unique_and_progress_constraints_exist():
    constraint_names = {constraint.name for constraint in IngestChunk.__table__.constraints}
    assert "uq_ingest_chunks_job_chunk_idx" in constraint_names
    assert any("processed_bounds" in (name or "") for name in constraint_names)


def test_audit_checkpoint_unique_constraint_exists():
    constraint_names = {constraint.name for constraint in AuditCheckpoint.__table__.constraints}
    assert "uq_audit_checkpoints_job_checkpoint" in constraint_names
