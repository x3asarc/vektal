---
phase: 15-self-healing-dynamic-scripting
plan: 04
subsystem: autonomous-fix-generation
tags: [llm, sandbox, remediation, template, code-fix]

requires:
  - phase: 15-self-healing-dynamic-scripting
    plan: 01
    provides: "sandbox verifier"
  - phase: 15-self-healing-dynamic-scripting
    plan: 02
    provides: "session context and memory loader"
  - phase: 15-self-healing-dynamic-scripting
    plan: 03
    provides: "failure classification"
provides:
  - "Centralized LLMClient for OpenRouter/Gemini"
  - "FixGenerator with template-first strategy and LLM fallback"
  - "LLMRemediator with sandbox-gated routing (auto-apply vs approval)"
  - "Comprehensive fix generation test suite"
affects:
  - src/graph/remediation_registry.py (via auto-discovery)

tech-stack:
  added: []
  patterns:
    - "template-first deterministic fix matching"
    - "LLM fallback with adaptive model selection (Flash vs Sonnet)"
    - "sandbox-gated remediation (GREEN + high confidence -> auto-apply ready)"
    - "centralized LLM client abstraction"

key-files:
  created:
    - src/core/llm_client.py
    - src/graph/fix_generator.py
    - src/graph/remediators/llm_remediator.py
    - tests/graph/test_fix_generation.py

key-decisions:
  - "Created `src/core/llm_client.py` as a centralized abstraction for OpenRouter, fulfilling the need for `get_llm_client()` across modules."
  - "Implemented adaptive model selection in `FixGenerator`: Gemini Flash for simple/config fixes, Claude Sonnet for complex/multi-file fixes (>1000 tokens)."
  - "Overrode `service_name` in `LLMRemediator` to `llm_code_remediator` to avoid collision with the base `CodeRemediator` in the registry."
  - "Maintained synchronous `run_verification` usage in `LLMRemediator` to align with the plan's deterministic-first flow while preserving sandbox gates."

duration: in-session
completed: 2026-03-02
---

# Phase 15 Plan 04 Summary

Implemented autonomous fix generation using template-first strategy with LLM fallback and sandbox verification.

## What Was Built

1. **Centralized LLM Client** ([src/core/llm_client.py](/C:/Users/Hp/Documents/Shopify Scraping Script/src/core/llm_client.py))
   - Unified interface for OpenRouter completions.
   - Configurable models, temperature, and tokens.
   - Fail-fast validation of API keys.

2. **Fix Generator** ([src/graph/fix_generator.py](/C:/Users/Hp/Documents/Shopify Scraping Script/src/graph/fix_generator.py))
   - Template-first matching using `RemedyTemplate` (from Plan 02).
   - LLM fallback for novel failures.
   - Session context injection for high-quality fix generation.
   - Adaptive model selection based on module type and failure complexity.

3. **LLM Remediator** ([src/graph/remediators/llm_remediator.py](/C:/Users/Hp/Documents/Shopify Scraping Script/src/graph/remediators/llm_remediator.py))
   - Integrates `FixGenerator` with `SandboxRunner`.
   - Routes fixes based on sandbox verdict and LLM confidence:
     - GREEN + Confidence >= 0.9 -> `auto_apply_ready`
     - GREEN + Confidence >= 0.7 -> `approval_required`
     - RED or Confidence < 0.7 -> `blocked`
   - Automatically registered via NullClaw-inspired `RemediationRegistry`.

4. **Verification Suite** ([tests/graph/test_fix_generation.py](/C:/Users/Hp/Documents/Shopify Scraping Script/tests/graph/test_fix_generation.py))
   - Validates template matching, LLM fallback, and model selection.
   - Validates remediator routing logic (auto-apply vs approval vs blocked).

## Verification Evidence

1. `python -m pytest tests/graph/test_fix_generation.py -v`
   - Result: `6 passed`
2. `python -c "from src.graph.remediation_registry import registry; assert 'llm_code_remediator' in registry.list_tools()"`
   - Result: Registry correctly discovered and loaded the new remediator.

## KISS / Size Check

- `llm_client.py`: 55 LOC
- `fix_generator.py`: 165 LOC
- `llm_remediator.py`: 105 LOC
- All files well within the 400 LOC target.
