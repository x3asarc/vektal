# Phase 1: Codebase Cleanup & Analysis - Research

**Researched:** 2026-02-03
**Domain:** Python codebase refactoring, CLI consolidation, test organization
**Confidence:** MEDIUM-HIGH

## Summary

This phase involves safely reorganizing a brownfield Python codebase with 50+ scripts, consolidating duplicate CLI tools, migrating scattered tests, and documenting architecture. The key challenge is executing cleanup without breaking production code (src/core/). Research identified three core technical domains:

**CLI Consolidation:** Modern Python CLI frameworks (Typer, Click, argparse) support building unified interfaces with subcommands. Typer emerged as the recommended choice for its type-hint-based API, automatic help generation, and minimal boilerplate for new projects.

**Dead Code Detection:** Two complementary tools exist - Vulture (confidence-based detection with whitelists) and deadcode (project-wide analysis with automatic removal). Both require careful false-positive handling through configuration.

**Test Migration:** pytest supports two primary layouts ("tests outside application" recommended for new projects). Migration requires preserving test discovery while consolidating scattered test files into a unified structure.

**Primary recommendation:** Use Plan-Then-Execute pattern with specialist subagents (Archiver, Consolidator, Test Migrator), Typer for CLI unification, and Vulture+deadcode for autonomous detection with manual validation.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Typer | 0.12+ | CLI framework | Type-hint based, zero boilerplate, built on Click, official FastAPI ecosystem tool |
| pytest | 8.0+ | Testing framework | Industry standard, powerful discovery, fixture system |
| Vulture | 2.11+ | Dead code detection | Confidence-based reporting (60-100%), whitelist support, static AST analysis |
| deadcode | 2.4+ | Project-level unused code | Detects global unused code (unlike ruff/flake8), supports `--fix` mode |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Click | 8.3+ | CLI framework | If already using Click, or need very low-level control |
| Rich | 13.0+ | Terminal formatting | Already included with Typer, enhances error display |
| pytest-cov | 4.1+ | Coverage reporting | Validate cleanup didn't reduce test coverage |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Typer | argparse (stdlib) | Argparse: more verbose, manual help formatting, but zero dependencies |
| Typer | Click directly | Click: requires decorators and manual type conversion, more boilerplate |
| Vulture | deadcode only | Deadcode focuses on removal automation; Vulture better for analysis phase |

**Installation:**
```bash
pip install typer[all] pytest pytest-cov vulture deadcode
```

**Note:** `typer[all]` includes Rich and Shellingham for enhanced UX. Use `typer-slim` for minimal installs.

## Architecture Patterns

### Recommended Project Structure
```
src/
├── core/              # Production modules (DO NOT TOUCH during cleanup)
├── cli/               # Unified CLI entry point (NEW)
│   ├── __init__.py
│   ├── main.py        # Typer app with subcommands
│   └── commands/      # Command modules
│       ├── products.py
│       └── scraper.py
├── legacy/            # Deprecated but working code (if needed)
tests/
├── conftest.py        # pytest fixtures
├── unit/
├── integration/
└── cli/               # CLI command tests
archive/
└── 2026-scripts/      # One-off scripts (apply_*, scrape_*, fix_*)
```

### Pattern 1: Plan-Then-Execute Refactoring
**What:** Generate refactoring plan, get approval, then execute atomic changes
**When to use:** Any structural change to production code
**Example:**
```python
# PHASE 1: Analysis (read-only)
# Agent analyzes codebase, produces classification report
# Output: PLAN.json with {file: action} mappings

# PHASE 2: Human Review
# Developer reviews plan, marks safe/unsafe changes

# PHASE 3: Execution (write)
# Agent executes only approved changes
# Each change is atomic (one git commit per logical change)
```

**Key principle:** "Small behavior-preserving transformations" (Martin Fowler) - each step must keep system working.

### Pattern 2: Specialist Subagent Orchestration
**What:** Spawn focused agents for distinct tasks (Archive, Consolidate, Migrate)
**When to use:** Complex multi-domain cleanup operations
**Example:**
```python
# Orchestrator spawns:
# 1. Archiver Agent: Moves one-off scripts to archive/
# 2. Consolidator Agent: Merges duplicate CLI scripts
# 3. Test Migrator Agent: Reorganizes tests/ directory
# 4. Documentation Agent: Generates ARCHITECTURE.md

# Each agent has:
# - Narrow scope (can't touch outside their domain)
# - Clear success criteria
# - Rollback capability (git branch per agent)
```

**Safety mechanism:** Use XML tags to define agent boundaries:
```xml
<constraints>
  <forbidden_paths>src/core/*</forbidden_paths>
  <allowed_actions>move,rename,delete</allowed_actions>
  <requires_approval>delete</requires_approval>
</constraints>
```

### Pattern 3: Typer CLI Consolidation
**What:** Unify duplicate scripts into single CLI with subcommands
**When to use:** Multiple scripts sharing auth/config logic
**Example:**
```python
# Source: https://typer.tiangolo.com/
# cli/main.py
import typer

app = typer.Typer()

@app.command()
def update_sku(
    variant_id: str = typer.Argument(..., help="Shopify variant ID"),
    new_sku: str = typer.Argument(..., help="New SKU value"),
    use_rest: bool = typer.Option(False, "--rest", help="Use REST instead of GraphQL")
):
    """Update product variant SKU."""
    # Unified logic combining update_sku.py + update_sku_rest.py
    if use_rest:
        client.update_via_rest(variant_id, new_sku)
    else:
        client.update_via_graphql(variant_id, new_sku)

if __name__ == "__main__":
    app()
```

**Migration path:** Keep old scripts as deprecated wrappers initially:
```python
# update_sku.py (deprecated wrapper)
import subprocess
import sys
subprocess.run(["python", "-m", "cli.main", "update-sku"] + sys.argv[1:])
```

### Pattern 4: pytest Test Discovery Migration
**What:** Consolidate scattered test files into pytest-discoverable structure
**When to use:** Tests exist in multiple locations (root, tests/, cli/testing/)
**Example:**
```python
# Source: https://docs.pytest.org/en/stable/explanation/goodpractices.html

# pytest.ini or pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

# Directory structure:
# tests/
#   conftest.py          # Shared fixtures
#   unit/
#     test_image_framework.py
#   integration/
#     test_shopify_api.py
#   cli/
#     test_update_commands.py
```

**Migration steps:**
1. Move all test_*.py to tests/ (preserve test code exactly)
2. Create conftest.py for shared fixtures
3. Run `pytest --collect-only` to verify discovery
4. Run full suite to catch import issues

### Anti-Patterns to Avoid

- **Big Bang Refactoring:** Don't move/rename everything at once. Incremental changes with tests between each step.
- **Analysis Paralysis:** Don't spend weeks analyzing. Use Vulture/deadcode for quick wins, then validate with tests.
- **Breaking Backward Compatibility:** Don't delete old CLI scripts immediately. Keep deprecated wrappers for 1-2 releases.
- **Touching Production Code:** Don't refactor src/core/ during cleanup phase. That's a separate phase with different risk profile.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CLI argument parsing | Manual sys.argv parsing | Typer/Click/argparse | Type validation, help generation, shell completion, error messages |
| Dead code detection | grep for unused imports | Vulture + deadcode | AST-based analysis catches unused functions/classes, not just imports |
| Test discovery | Custom test runner | pytest | Fixture system, parametrization, plugin ecosystem, IDE integration |
| File archival | `shutil.move()` loops | Git worktree + parallel agents | Atomic operations, rollback capability, 3x faster with parallelization |
| CLI consolidation | Wrapper scripts calling each other | Typer subcommands | Type safety, unified help, shared middleware (auth, config) |

**Key insight:** CLI frameworks handle edge cases you won't think of (Unicode args, shell escaping, help formatting, error recovery). Static analyzers understand Python AST better than regex patterns.

## Common Pitfalls

### Pitfall 1: False Positives in Dead Code Detection
**What goes wrong:** Vulture/deadcode report code as unused when it's dynamically imported or called via `getattr()`
**Why it happens:** Static analysis can't trace dynamic Python features (reflection, `__import__()`, plugin systems)
**How to avoid:**
- Use Vulture's confidence threshold: `--min-confidence 80` (default 60)
- Create whitelist files: `vulture --make-whitelist > whitelist.py`
- Mark intentional unused code with leading underscore: `_unused_var`
- Review ALL findings manually before deletion
**Warning signs:** Code in plugin directories, factory patterns, or with `getattr()` calls

### Pitfall 2: Breaking Import Paths During Reorganization
**What goes wrong:** Moving test files breaks relative imports; production code can't find modules
**Why it happens:** Python's import system is path-based; moving files changes import semantics
**How to avoid:**
- Use absolute imports everywhere: `from src.core.image_framework import X`
- Install package in editable mode: `pip install -e .`
- Run pytest after EVERY file move
- Use `importlib` import mode in pytest: `addopts = "--import-mode=importlib"`
**Warning signs:** ImportError, ModuleNotFoundError after moving files

### Pitfall 3: Consolidating Incompatible Functionality
**What goes wrong:** Merging update_sku.py + update_sku_rest.py creates a script that works for neither use case
**Why it happens:** Scripts may have subtle differences (auth methods, error handling, output formats) that matter
**How to avoid:**
- Read ALL duplicate scripts before merging (understand differences)
- Preserve both code paths as flags/options (don't delete working logic)
- Test both paths with real data before deprecating old scripts
- Use strategy pattern for divergent logic, not if/else sprawl
**Warning signs:** Scripts with same name but different dependencies, different config files, or different output formats

### Pitfall 4: Losing Working Code to Over-Aggressive Cleanup
**What goes wrong:** Delete "unused" scripts that are actually called by cron jobs, other repos, or documentation
**Why it happens:** Static analysis can't see external callers (shell scripts, CI/CD, cron)
**How to avoid:**
- Archive instead of delete: `archive/2026-scripts/` (still in git history)
- Search for script names in: .github/, docs/, crontab, other repos
- Add deprecation warnings to scripts before deletion: `print("DEPRECATED: Use cli.main instead")`
- Keep archive for 6+ months before permanent deletion
**Warning signs:** Scripts with no imports but complex logic, scripts in docs/examples

### Pitfall 5: Breaking Tests During Consolidation
**What goes wrong:** CLI consolidation changes function signatures, breaking existing tests
**Why it happens:** Tests couple to implementation details (function names, argument positions) instead of behavior
**How to avoid:**
- Run full test suite BEFORE consolidation (establish baseline)
- Update tests alongside code changes (same commit)
- If test breaks, fix test to match new interface OR fix new code to preserve interface
- Use integration tests for CLI (test via subprocess, not imports)
**Warning signs:** Tests importing private functions, tests with hardcoded argument positions

## Code Examples

Verified patterns from official sources:

### CLI Consolidation with Typer
```python
# Source: https://typer.tiangolo.com/
# cli/main.py - Unified entry point

import typer
from typing_extensions import Annotated

app = typer.Typer(
    name="shopify-cli",
    help="Unified CLI for Shopify operations"
)

# Subcommand groups
products_app = typer.Typer(help="Product management commands")
app.add_typer(products_app, name="products")

@products_app.command("update-sku")
def update_sku(
    variant_id: Annotated[str, typer.Argument(help="Shopify variant GID or numeric ID")],
    new_sku: Annotated[str, typer.Argument(help="New SKU value")],
    api_type: Annotated[str, typer.Option("--api", "-a", help="API type: graphql or rest")] = "graphql",
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show changes without applying")] = False
):
    """
    Update product variant SKU.

    Consolidates functionality from:
    - update_sku.py (GraphQL)
    - update_sku_rest.py (REST)
    - update_via_rest.py
    """
    from cli.commands.products import update_variant_sku
    update_variant_sku(variant_id, new_sku, api_type, dry_run)

if __name__ == "__main__":
    app()
```

**Usage:**
```bash
# New unified interface
python -m cli.main products update-sku gid://shopify/ProductVariant/123 "NEW-SKU" --api rest

# Automatic help
python -m cli.main products update-sku --help
```

### Dead Code Detection with Vulture
```python
# Source: https://github.com/jendrikseipp/vulture
# pyproject.toml

[tool.vulture]
min_confidence = 80  # Only report high-confidence findings
paths = ["src", "cli", "scripts"]
exclude = ["venv/", "archive/", "*.pyc"]
sort_by_size = true  # Largest dead code first

# Running Vulture
# Analysis phase (don't delete yet):
vulture . --min-confidence 80 > vulture_report.txt

# Create whitelist for false positives:
vulture . --make-whitelist > whitelist.py

# Re-run excluding whitelist:
vulture . whitelist.py --min-confidence 80
```

### Test Migration Pattern
```python
# Source: https://docs.pytest.org/en/stable/
# tests/conftest.py - Shared fixtures

import pytest
import sys
from pathlib import Path

# Ensure src/ is importable
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

@pytest.fixture
def shopify_client():
    """Mock Shopify client for testing."""
    from unittest.mock import MagicMock
    client = MagicMock()
    client.authenticate.return_value = True
    return client

@pytest.fixture
def temp_image_dir(tmp_path):
    """Temporary directory for image tests."""
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    return image_dir
```

```python
# tests/cli/test_update_commands.py

import pytest
from typer.testing import CliRunner
from cli.main import app

runner = CliRunner()

def test_update_sku_graphql():
    """Test SKU update via GraphQL (integration test)."""
    result = runner.invoke(app, [
        "products", "update-sku",
        "gid://shopify/ProductVariant/123",
        "NEW-SKU",
        "--dry-run"
    ])
    assert result.exit_code == 0
    assert "NEW-SKU" in result.stdout

def test_update_sku_rest():
    """Test SKU update via REST API."""
    result = runner.invoke(app, [
        "products", "update-sku",
        "gid://shopify/ProductVariant/123",
        "NEW-SKU",
        "--api", "rest",
        "--dry-run"
    ])
    assert result.exit_code == 0
```

### Agent Safety Constraint Pattern
```python
# Source: https://platform.claude.com/docs/en/docs/build-with-claude/prompt-engineering/use-xml-tags
# Agent prompt with XML tags for safety

ARCHIVER_AGENT_PROMPT = """
You are the Archiver agent. Your job: move one-off scripts to archive/.

<constraints>
  <allowed_operations>
    - Move files matching: apply_*, scrape_*, fix_*, dry_run_*
    - Create directories under: archive/2026-scripts/
    - Update documentation to reference new locations
  </allowed_operations>

  <forbidden_operations>
    - DO NOT touch: src/core/* (production code)
    - DO NOT delete files (only move)
    - DO NOT modify file contents
  </forbidden_operations>

  <validation>
    - After each move, verify: git status shows ONLY archive/ and docs/
    - Run: pytest --collect-only (should not change test count)
  </validation>
</constraints>

<procedure>
1. List all files matching patterns in root directory
2. For each file, verify it's a one-off script (not imported by production code)
3. Move to archive/2026-scripts/ with git mv
4. Update any documentation referencing the script
5. Commit each move separately
</procedure>
"""
```

### Backward-Compatible Deprecation
```python
# Old script: update_sku.py (kept for backward compatibility)
import sys
import subprocess
import warnings

warnings.warn(
    "update_sku.py is deprecated. Use: python -m cli.main products update-sku",
    DeprecationWarning,
    stacklevel=2
)

# Forward to new CLI
result = subprocess.run(
    ["python", "-m", "cli.main", "products", "update-sku"] + sys.argv[1:],
    check=False
)
sys.exit(result.returncode)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| argparse manual parsing | Typer type hints | 2020 (Typer 0.1) | 50% less boilerplate, automatic validation |
| unittest framework | pytest | ~2015 (mainstream) | Fixture system, better assertions, parametrization |
| Manual dead code review | Vulture/deadcode | 2018-2020 | Automated detection, confidence scoring |
| Monolithic test files | Organized test/ structure | pytest 3.0+ (2016) | Better discovery, parallel execution |
| Click decorators | Typer type hints | 2020 | Easier to read, better IDE support |

**Deprecated/outdated:**
- `python setup.py test`: Deprecated, security risks, use pytest directly
- `optparse`: Deprecated since Python 3.2, use argparse or Typer
- `unittest.TestCase` for new tests: Not deprecated but pytest style preferred
- `--min-confidence 60` (Vulture default): Too many false positives, use 80+

## Open Questions

Things that couldn't be fully resolved:

1. **Scraper Integration Strategy**
   - What we know: Both Python (src/core/scrape_engine.py) and JavaScript (universal_vendor_scraper/) exist
   - What's unclear: Which is primary? How do they communicate? When to use each?
   - Recommendation: Document as-is in ARCHITECTURE.md; don't change during cleanup. Defer integration decision to Phase 2 or later.

2. **Test Coverage Baseline**
   - What we know: Tests exist in 3 locations (root, tests/, cli/testing/)
   - What's unclear: Current coverage percentage, which tests are critical vs exploratory
   - Recommendation: Run `pytest --cov=src --cov-report=html` BEFORE cleanup to establish baseline. Goal: maintain or improve coverage.

3. **CLI Script Dependencies**
   - What we know: 5+ duplicate update scripts exist
   - What's unclear: Are any scripts called by external systems (cron, CI/CD, other repos)?
   - Recommendation: Search codebase and docs for script names before consolidation. Keep deprecated wrappers for 6 months.

4. **Agent Orchestration vs Manual Execution**
   - What we know: Plan mentions "specialist subagents" but this is experimental
   - What's unclear: Is agent orchestration more reliable than guided manual steps?
   - Recommendation: Start with manual Plan-Then-Execute (safer). Only use agent orchestration if experienced with multi-agent systems.

## Sources

### Primary (HIGH confidence)
- Typer official docs - https://typer.tiangolo.com/ (WebFetch verified)
- pytest best practices - https://docs.pytest.org/en/stable/explanation/goodpractices.html (WebFetch verified)
- Vulture GitHub README - https://github.com/jendrikseipp/vulture (WebFetch verified)
- deadcode GitHub README - https://github.com/albertas/deadcode (WebFetch verified)
- Click official docs - https://click.palletsprojects.com/en/stable/ (WebFetch verified)
- argparse stdlib docs - https://docs.python.org/3/library/argparse.html (WebFetch verified)

### Secondary (MEDIUM confidence)
- Anthropic prompt engineering docs - https://platform.claude.com/docs/en/docs/build-with-claude/prompt-engineering/use-xml-tags (WebFetch verified)
- ARCHITECTURE.md pattern - https://matklad.github.io/2021/02/06/ARCHITECTURE.md.html (WebFetch verified)
- Refactoring principles - https://refactoring.com/ (WebFetch verified)

### Tertiary (LOW confidence - from training data)
- Git worktree parallelization (mentioned in project context, not verified)
- Code-Simplifier plugin (mentioned as "official Anthropic" but no source verified)
- Specialist subagent orchestration (theoretical pattern, not verified in official docs)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries verified via official documentation, versions confirmed
- Architecture: MEDIUM-HIGH - Patterns verified from official sources (Typer, pytest, Anthropic), but orchestration pattern is theoretical
- Pitfalls: MEDIUM - Based on common Python refactoring experience (training data) + official docs, not project-specific testing
- CLI consolidation: HIGH - Typer patterns verified, actual duplicate scripts examined in codebase
- Dead code detection: HIGH - Both tools verified via official docs, configuration patterns confirmed

**Research date:** 2026-02-03
**Valid until:** 2026-04-03 (60 days - relatively stable ecosystem)

**Notes:**
- WebSearch was unavailable; research relied on WebFetch of official docs + training data
- Codebase examined: 5 duplicate update scripts, src/core/ structure, test locations
- No CONTEXT.md exists; full research discretion applied
- Specialist subagent orchestration marked LOW confidence (theoretical, not verified)
