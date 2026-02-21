# Code Generator Agent

Agent for generating code with intent capture for knowledge graph enrichment.

## Intent Capture

When generating code, capture intent for the knowledge graph to provide semantic context for future AI assistants.

### 1. Formulate Intent (Before Writing)
Before generating any implementation, clarify your reasoning:
- What problem am I solving?
- Why choose this specific approach/pattern?
- What alternatives did I consider and reject?

### 2. Emit Intent (After Writing)
After writing code, use the `src.graph.intent_capture.capture_intent` API:

```python
from src.graph.intent_capture import capture_intent, IntentRecord

intent = IntentRecord(
    file_path="src/graph/commit_parser.py",
    entity_type="function",  # or "class", "file"
    entity_name="parse_commit_message",
    intent="Parse commit messages to extract phase/plan references",
    reasoning="Using regex patterns because commit format is well-defined. Conventional commits format (feat/fix/docs) is predictable.",
    alternatives_considered=["NLP-based parsing", "String splitting only"],
    phase="14",
    plan="04",
    agent="claude"
)
capture_intent(intent)
```

## When to Capture Intent
- **Creating new files:** Capture the high-level architecture/purpose.
- **Adding new functions or classes:** Capture the "why" behind the logic.
- **Significant refactoring:** Document why the change improves the codebase.
- **Architectural decisions:** Record reasons for choosing specific libraries/patterns.

## When NOT to Capture
- Trivial changes (typo fixes, reformatting).
- Boilerplate generation (e.g., standard `__init__.py`).
- Test files (unless the testing strategy itself is complex).

## Example Scenario
If you're creating a new parser for Phase 14-04:

```python
# [Agent implements the parser code]

# After implementation, capture intent:
capture_intent(IntentRecord(
    file_path="src/graph/commit_parser.py",
    entity_type="function",
    entity_name="parse_commit_message",
    intent="Extract metadata from conventional commit messages",
    reasoning="Regex is used for efficiency and reliability given the consistent project commit style.",
    alternatives_considered=["Simple string splitting", "LLM-based parsing (too slow/costly)"],
    phase="14",
    plan="04",
    agent="claude"
))
```
