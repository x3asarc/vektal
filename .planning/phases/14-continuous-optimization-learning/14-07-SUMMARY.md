# Phase 14 Plan 07 - LLM Instruction Framework

## Summary

Created an LLM instruction framework to capture the "intent" behind AI-generated code. This enriches the knowledge graph with semantic meaning (the "why"), providing invaluable context for future autonomous maintenance and self-healing.

## What Was Built

### Intent Capture API (`src/graph/intent_capture.py`)
- `IntentRecord`: Dataclass capturing file path, entity, intent, reasoning, and alternatives.
- `capture_intent()`: High-level API for agents to record their thought process.
- `emit_intent_episode()`: Asynchronous emission to the graph via Celery.
- Integration: Added `CODE_INTENT` to `EpisodeType` enum in `synthex_entities.py`.

### Agent Instructions (`.claude/agents/code-generator.md`)
- Comprehensive guide for AI agents on when and how to capture intent.
- Provides concrete examples and reasoning frameworks (formulate intent before writing, emit after).
- Agent-agnostic design (works for Claude, Codex, Gemini).

## Verification

- `tests/unit/test_wave_sync.py` verified that `capture_intent` correctly queues Celery tasks.
- Manual verification of `IntentRecord` serialization and payload structure.
- Extension of `EpisodeType` verified in core entities.

## Files Created/Modified

- `src/graph/intent_capture.py` (Created)
- `.claude/agents/code-generator.md` (Created)
- `src/core/synthex_entities.py` (Modified)

**Phase:** 14-07 | **Status:** Complete | **Tests:** 6 passed (unit)
