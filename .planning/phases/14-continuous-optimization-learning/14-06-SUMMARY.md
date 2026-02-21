# Phase 14 Plan 06 - Periodic Consistency Daemon

## Summary

Implemented a periodic consistency daemon to detect and repair divergences between the codebase knowledge graph and the filesystem. This acts as a fallback mechanism (Layer 2) to catch changes made outside of the Git workflow.

## What Was Built

### Consistency Checker (`src/graph/consistency_daemon.py`)
- `check_consistency()`: Scans the filesystem and compares it with graph nodes.
- Detects missing files, stale entries (soft deletes), and hash mismatches.
- `compute_file_hash()`: Uses SHA-256 for reliable change detection.

### Repair Logic (`src/graph/consistency_daemon.py`)
- `repair_divergence()`: Provides automated fixes for detected inconsistencies.
- Supports `dry_run` mode for safe simulation.
- Counts actions: files added, removed, and updated.

### CLI Trigger (`scripts/graph/run_consistency_check.py`)
- Manual trigger for consistency checks and repairs.
- Flags: `--repair`, `--verbose`, `--no-dry-run`.
- Clean, actionable output for developers.

## Verification

- `tests/unit/test_wave_sync.py` verified consistency detection and repair counts.
- `scripts/graph/run_consistency_check.py` verified for CLI functionality.
- Successfully handles path normalization across different platforms.

## Files Created

- `src/graph/consistency_daemon.py`
- `scripts/graph/run_consistency_check.py`

**Phase:** 14-06 | **Status:** Complete | **Tests:** 6 passed (unit)
