# Architecture Research: Agent-Driven Brownfield Python Cleanup

**Domain:** Brownfield Python codebase cleanup automation with Claude Code agents
**Researched:** 2026-02-03
**Confidence:** HIGH

## Standard Architecture

### System Overview: Agent-Driven Cleanup Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    DISCOVERY & CLASSIFICATION                     │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ AST Analysis │  │ Import Graph │  │ Usage Stats  │           │
│  │  (vulture)   │  │  (deadcode)  │  │  (coverage)  │           │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘           │
│         │                 │                 │                     │
│         └─────────────────┴─────────────────┘                     │
│                           ↓                                       │
├─────────────────────────────────────────────────────────────────┤
│                       AGENT EXECUTION LAYER                       │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐    │
│  │           Plan Mode (Read-only Analysis)                 │    │
│  │  • Classify scripts (one-off vs production)              │    │
│  │  • Map duplicate consolidation targets                   │    │
│  │  • Generate safety verification plan                     │    │
│  └──────────────────────────┬──────────────────────────────┘    │
│                             ↓                                     │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │      Specialist Subagents (Execution Mode)               │    │
│  │  ┌──────────┐  ┌────────────┐  ┌──────────────┐         │    │
│  │  │ Archiver │  │Consolidator│  │ Test Migrator│         │    │
│  │  └──────────┘  └────────────┘  └──────────────┘         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                             ↓                                     │
├─────────────────────────────────────────────────────────────────┤
│                     SAFETY VERIFICATION LAYER                     │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ Import Check │  │  Test Suite  │  │ Production   │           │
│  │ (no breaks)  │  │   Validation │  │ Core Shield  │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **Discovery Agents** | Classify scripts, detect duplicates, map dependencies | Static analysis tools (vulture, deadcode) + Plan Mode analysis |
| **Plan Mode Orchestrator** | Create comprehensive cleanup roadmap without touching files | Claude Code `--permission-mode plan` with AskUserQuestion for validation |
| **Archiver Subagent** | Move one-off scripts to archive/ with metadata preservation | Specialized subagent with git-aware file operations |
| **Consolidator Subagent** | Merge duplicate CLI tools into unified interface | Code-aware merging with functionality preservation |
| **Test Migrator Subagent** | Restructure tests to pytest conventions | Pattern-based test discovery and migration |
| **Safety Verifier** | Validate no production breakage occurred | Import validation, test execution, core module checks |

## Recommended Project Structure

### Current State (Brownfield)
```
shopify-scraping/
├── src/
│   └── core/                    # 18 production modules (PROTECTED)
│       ├── pipeline.py
│       ├── scrape_engine.py
│       ├── shopify_apply.py
│       └── ... (14 more)
├── apply_*.py                   # 3 one-off application scripts
├── scrape_*.py                  # 6 scraping experiments
├── fix_*.py                     # 5 fix scripts
├── dry_run_*.py                 # 4 dry run scripts
├── update_*.py                  # 2 update scripts
├── cli/                         # 5 duplicate product update CLIs
│   ├── products/
│   ├── pentart/
│   └── ...
└── tests/ (scattered)           # Tests mixed with implementation
```

### Target State (Post-Cleanup)
```
shopify-scraping/
├── src/
│   └── core/                    # 18 production modules (UNCHANGED)
├── cli/
│   ├── products.py              # Consolidated product CLI (unified interface)
│   ├── update.py                # Consolidated update operations
│   └── README.md                # CLI usage documentation
├── tests/
│   ├── conftest.py              # pytest configuration
│   ├── unit/                    # Unit tests by module
│   ├── integration/             # Integration tests
│   └── fixtures/                # Shared test fixtures
├── archive/
│   ├── 2026-02-scripts/         # Timestamped archive batch
│   │   ├── apply_*.py           # One-off scripts with preservation metadata
│   │   ├── scrape_*.py
│   │   ├── fix_*.py
│   │   ├── dry_run_*.py
│   │   └── ARCHIVE_MANIFEST.md  # What was archived and why
│   └── README.md                # Archive policy and retrieval instructions
├── docs/
│   └── ARCHITECTURE.md          # Post-cleanup architecture documentation
└── requirements.txt             # Pruned dependencies
```

### Structure Rationale

- **src/core/ protected:** Production code remains untouched unless explicitly directed
- **archive/ with metadata:** Preserves one-off scripts for historical reference with searchable manifest
- **Consolidated CLI:** Single entry point per domain (products, updates) with subcommands
- **pytest structure:** Industry-standard test organization for maintainability
- **Timestamped archives:** Enables batch operations while maintaining retrieval capability

## Architectural Patterns

### Pattern 1: Plan-Then-Execute with Safety Gates

**What:** Use Plan Mode for read-only analysis before any destructive operations, then execute with specialist subagents under safety verification.

**When to use:** Brownfield cleanup where production code must remain functional.

**Trade-offs:**
- **Pro:** Eliminates "oops, broke production" moments; generates human-reviewable plan
- **Pro:** Allows iterative refinement of plan before execution
- **Con:** Slower than direct execution (requires two passes)
- **Con:** Requires disciplined gate-keeping at phase boundaries

**Example:**
```bash
# Phase 1: Discovery (Plan Mode - read-only)
claude --permission-mode plan -p "
Analyze this Python codebase and create a cleanup plan:
1. Classify all root-level .py files as production, experimental, or one-off
2. Identify duplicate functionality across cli/ subdirectories
3. Map test files and their coverage of src/core/
4. Flag any dependencies in requirements.txt not imported by production code
5. Create execution plan with safety validation checkpoints

CRITICAL: src/core/ is production code. Do not modify without explicit approval.
"

# Phase 2: Human Review
# Review generated plan, refine classification

# Phase 3: Execution with Subagents (Normal Mode)
claude -p "
Execute the cleanup plan with these constraints:
- Archive one-off scripts to archive/2026-02-scripts/
- Consolidate duplicate CLIs as outlined in plan
- Migrate tests to tests/ with pytest structure
- STOP after each phase for verification
"
```

### Pattern 2: Specialist Subagent Orchestration

**What:** Create domain-specific subagents (archiver, consolidator, test-migrator) with limited scope and tools, orchestrated by a coordinator.

**When to use:** Complex multi-step refactoring requiring different expertise per phase.

**Trade-offs:**
- **Pro:** Each agent has narrow, testable responsibility
- **Pro:** Easier to debug failures (agent X failed at step Y)
- **Con:** Requires upfront agent definition
- **Con:** Inter-agent coordination complexity

**Example subagent definition (.claude/agents/archiver.md):**
```markdown
description: Archives one-off Python scripts with metadata preservation
when_to_use: When moving experimental or one-off scripts out of active codebase
tools: [Read, Write, Bash, Glob]
max_tool_calls: 100

system_prompt: |
  You are an archival specialist. Your job:
  1. Identify scripts marked for archival
  2. Create timestamped archive directory (YYYY-MM-scripts/)
  3. Move scripts preserving git history (git mv)
  4. Generate ARCHIVE_MANIFEST.md documenting:
     - What was archived
     - Why (one-off, experimental, superseded)
     - Original purpose (extracted from docstrings/comments)
     - How to resurrect if needed
  5. Verify no imports reference archived scripts

  NEVER archive anything in src/core/.
  ALWAYS verify with grep before declaring "no references."
```

### Pattern 3: Code-Simplifier Post-Consolidation

**What:** Use Anthropic's code-simplifier plugin after merging duplicates to normalize style and reduce token bloat.

**When to use:** After consolidating multiple implementations into unified interface.

**Trade-offs:**
- **Pro:** Automatically catches over-engineering from merge process
- **Pro:** Reduces future token consumption by 20-30%
- **Pro:** Safe (preserves functionality, only touches recently modified code)
- **Con:** Requires Opus model (higher cost)
- **Con:** Only works on recently modified code (not full codebase)

**Example:**
```bash
# After consolidating 5 duplicate CLIs into cli/products.py
claude -p "We just consolidated 5 product update CLIs. Run code-simplifier on cli/products.py"

# Installation if not already installed:
# claude plugin install code-simplifier
```

### Pattern 4: Git Worktree Parallel Cleanup

**What:** Use git worktrees to run multiple Claude Code instances in parallel on independent cleanup tasks.

**When to use:** Multiple independent cleanup operations (archival + test migration + consolidation).

**Trade-offs:**
- **Pro:** Massive parallelization (3x faster for independent tasks)
- **Pro:** Complete isolation prevents agents from interfering
- **Con:** Requires git worktree knowledge
- **Con:** Merge conflicts possible when recombining

**Example:**
```bash
# Create worktrees for parallel cleanup tasks
git worktree add ../shopify-archival -b cleanup/archival
git worktree add ../shopify-tests -b cleanup/test-migration
git worktree add ../shopify-consolidation -b cleanup/cli-consolidation

# Terminal 1: Archive one-off scripts
cd ../shopify-archival
claude -p "Archive all apply_*, scrape_*, fix_*, dry_run_* scripts to archive/2026-02-scripts/"

# Terminal 2: Migrate tests
cd ../shopify-tests
claude -p "Migrate all scattered test_*.py to tests/ with pytest structure"

# Terminal 3: Consolidate CLIs
cd ../shopify-consolidation
claude -p "Consolidate 5 duplicate product update CLIs into unified cli/products.py"

# Merge results via PRs for human review before combining
```

## Data Flow

### Cleanup Execution Flow

```
[User: "Clean up this brownfield codebase"]
    ↓
[Plan Mode Agent] → Analyze codebase (read-only)
    ↓ (generates plan.md)
[Human Review] → Approve/refine plan
    ↓
[Orchestrator] → Dispatch to specialist subagents
    ↓
┌──────────────┬─────────────────┬────────────────┐
│              │                 │                │
│ [Archiver]   │ [Consolidator]  │ [Test Migrator]│
│  - Move files│  - Merge CLIs   │  - Restructure │
│  - Manifest  │  - Unify API    │  - pytest      │
│              │                 │                │
└──────┬───────┴─────────┬───────┴────────┬───────┘
       │                 │                │
       └─────────────────┴────────────────┘
                         ↓
              [Safety Verifier]
                         ↓
         ┌───────────────┴────────────────┐
         │                                │
    [Import Check]                  [Test Suite]
         │                                │
         └───────────────┬────────────────┘
                         ↓
                [Human Approval Gate]
                         ↓
                    [Git Commit]
```

### Safety Verification Flow

```
[Code Changes]
    ↓
[Import Validation]
    ├→ Grep all Python files for references to moved/deleted code
    ├→ Verify src/core/ imports still resolve
    └→ Check no circular dependencies introduced
    ↓
[Test Suite Execution]
    ├→ Run existing tests against modified code
    ├→ Verify src/core/ functionality unchanged
    └→ Check new consolidated CLIs pass tests
    ↓
[Production Core Shield]
    ├→ Verify no src/core/ files modified without approval
    ├→ Check no dependency changes affect core modules
    └→ Validate API contracts preserved
    ↓
[Human Review Checkpoint]
    ├→ Present diff summary
    ├→ Highlight any "risky" changes flagged
    └→ Await approval before proceeding
```

### Key Data Flows

1. **Discovery → Classification:** Static analysis tools (vulture, deadcode) feed Plan Mode agent with dead code candidates, which are classified by usage patterns and import relationships.

2. **Plan → Execution:** Human-approved plan becomes execution checklist for subagents, with each step having rollback instructions.

3. **Execution → Verification:** Every file operation triggers import validation and test execution before being considered complete.

## Automation Opportunities (Agent-Driven)

### Fully Autonomous (High Confidence)

| Task | Agent Strategy | Safety Mechanism |
|------|----------------|------------------|
| **Archive one-off scripts** | Archiver subagent with git mv and manifest generation | Verify no imports reference archived files before moving |
| **Migrate scattered tests** | Test migrator with pytest structure knowledge | Run migrated tests to verify no breakage |
| **Dead code detection** | Plan Mode with vulture/deadcode integration | Generate report for human review, don't delete automatically |
| **Dependency pruning** | Import graph analysis + requirements.txt comparison | Verify each unused dep in isolated venv before removal |
| **Code simplification** | code-simplifier plugin on consolidated code | Built-in functionality preservation verification |

### Semi-Autonomous (Human Checkpoints)

| Task | Agent Strategy | Human Gate |
|------|----------------|------------|
| **Consolidate duplicate CLIs** | Consolidator subagent merges implementations | Review merged API before committing |
| **Refactor src/core/** | Explicit approval required per file | Approve each change + run integration tests |
| **Delete dead code** | Provide deletion candidates from vulture | Human selects what to delete from candidate list |
| **Update dependencies** | Agent identifies outdated deps | Human approves version bumps (breaking changes) |

### Human-Only (Too Risky for Autonomy)

| Task | Why Human-Only | Agent Support Role |
|------|----------------|-------------------|
| **Define "production" vs "experimental"** | Requires business context agents lack | Agent provides usage stats to inform decision |
| **Approve src/core/ changes** | Core system, high blast radius | Agent explains why change needed, shows tests pass |
| **Decide archive vs delete** | May need scripts for forensic purposes | Agent identifies duplicates and last-used dates |
| **Breaking API changes** | Requires understanding downstream impact | Agent maps all callers, suggests migration path |

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| **10-50 scripts** | Single Plan Mode session → manual execution works fine |
| **50-200 scripts** | Parallel worktree execution + specialist subagents required |
| **200+ scripts** | Batch processing with autonomous archival, human review of reports only |

### Scaling Priorities

1. **First bottleneck (50+ scripts):** Human review fatigue.
   - **Fix:** Batch similar operations (archive all apply_* at once), use confidence-based triage (high-confidence changes auto-approve, low-confidence human-review)

2. **Second bottleneck (complex consolidation):** Merge conflicts and API design decisions.
   - **Fix:** Use code-simplifier after merges to normalize, create API design subagent with project-specific conventions

## Anti-Patterns

### Anti-Pattern 1: "Autonomous Delete Everything"

**What people do:** Run agents in auto-accept mode to "clean up faster" without Plan Mode phase.

**Why it's wrong:**
- Deletes production code agents incorrectly classified as "unused"
- No rollback plan when things break
- Human discovers breakage in production, not during cleanup

**Do this instead:**
1. Always start with Plan Mode (read-only)
2. Generate deletion candidate list with evidence (vulture confidence scores)
3. Human reviews and approves deletion batch
4. Agent executes approved deletions with git history preservation

### Anti-Pattern 2: "One Agent Does Everything"

**What people do:** Single prompt like "clean up this entire codebase" without phase structure.

**Why it's wrong:**
- Agent context switches between archival, consolidation, testing
- Impossible to debug which phase failed
- No progress tracking or resumability

**Do this instead:**
- Create specialist subagents (archiver, consolidator, test-migrator)
- Orchestrate with clear phase boundaries
- Each phase has completion criteria and verification
- Failed phase doesn't block others (parallel worktrees)

### Anti-Pattern 3: "Ignore src/core/ Protection"

**What people do:** Trust agents to "know" what's production vs experimental without explicit guards.

**Why it's wrong:**
- Agents use heuristics (infer from file age, imports, naming)
- Heuristics fail for brownfield code (old doesn't mean unused)
- One wrong classification breaks production

**Do this instead:**
- Explicitly mark src/core/ as protected in system prompts
- Use hooks to block any edits to core without human approval
- Separate "discovery" (what might be safe to touch) from "execution" (touching it)

**Example hook (.claude/hooks/protect-core.json):**
```json
{
  "on": "tool:Write",
  "run": "bash",
  "cmd": "if [[ $FILE_PATH == src/core/* ]]; then echo '{\"approved\": false, \"message\": \"Cannot modify src/core/ without explicit approval\"}'; exit 1; fi"
}
```

### Anti-Pattern 4: "Skip Safety Verification"

**What people do:** Archive/delete/consolidate without running tests or checking imports.

**Why it's wrong:**
- Breaks production code silently
- Discovers failures when customers report issues
- No quick rollback since multiple operations happened

**Do this instead:**
- After each operation: verify imports, run tests, check core functionality
- Use git commits per phase (easy rollback to last-known-good)
- "Stop on first failure" rather than "batch everything and hope"

## Integration Points

### External Tools

| Tool | Integration Pattern | Notes |
|------|---------------------|-------|
| **vulture** | Run in Plan Mode for dead code detection | `vulture --min-confidence 80 src/` for high-confidence candidates |
| **deadcode** | Import graph analysis for orphaned modules | `deadcode --fix` for automatic removal (use with caution) |
| **pytest** | Verification after every change | Run via hook: `pytest tests/ --maxfail=1` stops on first failure |
| **pre-commit** | Enforce no core/ changes without approval | Integrate hook to block src/core/ edits |
| **git worktree** | Parallel cleanup operations | Isolates agent work, prevents interference |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| **Plan Mode ↔ Execution Mode** | plan.md file + human approval | Plan is read-only proposal, execution requires permission elevation |
| **Subagent ↔ Orchestrator** | Completion signals via file markers | Each subagent writes `.complete` marker when done |
| **Agent ↔ Safety Verifier** | Tool output (test results, import check) | Verifier blocks commit if checks fail |

## Awesome-Claude-Code Resources for Brownfield Cleanup

### Directly Applicable Skills

| Resource | Application to Brownfield Cleanup | Source |
|----------|-------------------------------------|--------|
| **code-simplifier plugin** | Post-consolidation normalization, reduces token bloat 20-30% | [Official Anthropic plugin](https://jpcaparas.medium.com/inside-claudes-code-simplifier-plugin-how-anthropic-keeps-its-own-codebase-clean-f12254787fa2) |
| **Trail of Bits Security Skills** | Audit archived scripts for security issues before deletion | [trailofbits/skills](https://github.com/trailofbits/skills) |
| **Superpowers (obra)** | Core engineering competencies including refactoring patterns | [obra/superpowers](https://github.com/obra/superpowers) |
| **TDD Guard hooks** | Block production core changes that violate TDD | [nizos/tdd-guard](https://github.com/nizos/tdd-guard) |

### Workflow Patterns

| Pattern | Application | Source |
|---------|-------------|--------|
| **RIPER Workflow** | Research → Plan → Execute phases for cleanup | [tony/claude-code-riper-5](https://github.com/tony/claude-code-riper-5) |
| **Ralph Wiggum Loop** | Autonomous iteration until cleanup complete (use with caution) | [frankbria/ralph-claude-code](https://github.com/frankbria/ralph-claude-code) |
| **Subagent Orchestration** | Pattern for archiver + consolidator + test-migrator coordination | [Agentic Workflow Patterns](https://github.com/ThibautMelen/agentic-workflow-patterns) |

### Safety Tools

| Tool | Purpose | Source |
|------|---------|--------|
| **cc-tools (Go hooks)** | High-performance pre-commit validation | [Veraticus/cc-tools](https://github.com/Veraticus/cc-tools) |
| **TypeScript Quality Hooks** | Adapt pattern for Python: run pytest + mypy pre-commit | [bartolli/claude-code-typescript-hooks](https://github.com/bartolli/claude-code-typescript-hooks) |
| **Container Use (dagger)** | Isolate agent cleanup in containers for safety | [dagger/container-use](https://github.com/dagger/container-use) |

### Orchestration

| Tool | Use Case | Source |
|------|----------|--------|
| **TSK - AI Agent Task Manager** | Parallel cleanup in sandboxed Docker environments | [dtormoen/tsk](https://github.com/dtormoen/tsk) |
| **Claude Squad** | Manage multiple Claude instances for parallel worktree cleanup | [smtg-ai/claude-squad](https://github.com/smtg-ai/claude-squad) |

## Suggested Execution Order

Based on dependency analysis and risk profiles:

### Phase 1: Discovery & Classification (Plan Mode - 100% Safe)
**Duration:** 1 session (~30 min)
**Agent:** Plan Mode orchestrator
**Output:** Cleanup plan with classified files

**Steps:**
1. Run vulture + deadcode for unused code candidates
2. Classify root-level scripts (one-off vs production)
3. Map duplicate CLI tools and their overlap
4. Identify scattered tests and coverage gaps
5. Generate human-readable plan with confidence scores

**Checkpoint:** Human reviews plan, approves classification

### Phase 2: Archive One-Off Scripts (Low Risk)
**Duration:** 1 session (~20 min)
**Agent:** Archiver subagent
**Output:** archive/2026-02-scripts/ with manifest

**Steps:**
1. Create timestamped archive directory
2. Move approved one-off scripts with git mv
3. Generate ARCHIVE_MANIFEST.md
4. Verify no imports reference archived scripts
5. Run tests to verify no breakage

**Checkpoint:** Git commit, verify tests pass

### Phase 3: Migrate Tests to pytest Structure (Medium Risk)
**Duration:** 1-2 sessions (~45 min)
**Agent:** Test migrator subagent
**Output:** tests/ directory with organized test suite

**Steps:**
1. Create pytest structure (conftest.py, unit/, integration/)
2. Move scattered test_*.py files
3. Update imports and pytest conventions
4. Run migrated tests to verify functionality
5. Update CI configuration if needed

**Checkpoint:** Git commit, verify all tests pass

### Phase 4: Consolidate Duplicate CLIs (High Risk - Requires Design)
**Duration:** 2-3 sessions (~90 min)
**Agent:** Consolidator subagent + code-simplifier
**Output:** Unified cli/products.py with subcommand structure

**Steps:**
1. Extract common functionality from 5 duplicate CLIs
2. Design unified CLI interface (argparse/click/typer)
3. Implement consolidated tool with subcommands
4. Migrate existing script callers to new interface
5. Run code-simplifier to normalize merged code
6. Create deprecation warnings for old CLIs

**Checkpoint:** Human reviews API design, approves before deletion of old CLIs

### Phase 5: Dead Code Removal (High Risk)
**Duration:** 1-2 sessions (~45 min)
**Agent:** Plan Mode for candidates, human-approved deletion
**Output:** Pruned codebase with updated requirements.txt

**Steps:**
1. Review vulture high-confidence dead code (80%+)
2. Human selects approved deletion candidates
3. Agent removes approved dead code
4. Update requirements.txt (remove unused dependencies)
5. Run full test suite
6. Verify src/core/ functionality unchanged

**Checkpoint:** Git commit, full integration test run

### Phase 6: Documentation & Architecture (Low Risk)
**Duration:** 1 session (~30 min)
**Agent:** Documentation specialist subagent
**Output:** Updated docs/ARCHITECTURE.md, README updates

**Steps:**
1. Document new CLI structure
2. Update README with consolidated tool usage
3. Create architecture diagram post-cleanup
4. Document archive policy
5. Update CONTRIBUTING.md with new structure

**Checkpoint:** Human reviews documentation for accuracy

## Safety Verification Checklist

After each phase, verify:

```bash
# Import validation
python -c "import sys; sys.path.insert(0, 'src'); from core import *"

# Test suite (fail-fast on first error)
pytest tests/ --maxfail=1 -v

# Production core unchanged (git diff src/core/)
git diff src/core/ || echo "Core modified - requires approval"

# No broken imports in scripts
python -m py_compile cli/*.py src/**/*.py

# Dependencies still install
pip install -r requirements.txt --dry-run
```

## Sources

### Claude Code Best Practices
- [Claude Code: Common Workflows](https://code.claude.com/docs/en/common-workflows) - Official workflows for refactoring, testing, Plan Mode
- [Claude Code: A Guide With Practical Examples | DataCamp](https://www.datacamp.com/tutorial/claude-code) - Practical brownfield refactoring patterns
- [Inside Claude's Code-Simplifier Plugin | Medium](https://jpcaparas.medium.com/inside-claudes-code-simplifier-plugin-how-anthropic-keeps-its-own-codebase-clean-f12254787fa2) - Official code-simplifier agent details
- [What is Claude Code's Code-Simplifier Agent? | Cyrus AI](https://www.atcyrus.com/stories/claude-code-code-simplifier-agent-guide) - Code-simplifier workflow patterns

### Python Static Analysis Tools
- [deadcode · PyPI](https://pypi.org/project/deadcode/) - Automatic dead code removal tool
- [GitHub - jendrikseipp/vulture](https://github.com/jendrikseipp/vulture) - Find dead Python code with confidence scores
- [Top 10 Python Code Analysis Tools in 2026 | Jit](https://www.jit.io/resources/appsec-tools/top-python-code-analysis-tools-to-improve-code-quality) - 2026 tooling landscape
- [Automating dead code cleanup - Engineering at Meta](https://engineering.fb.com/2023/10/24/data-infrastructure/automating-dead-code-cleanup/) - Industry best practices from Meta's SCARF system

### Awesome-Claude-Code Resources
- [awesome-claude-code README](https://github.com/hesreallyhim/awesome-claude-code) - Comprehensive curated list of Claude Code resources
- Community workflows, skills, and patterns for autonomous agent orchestration

---
*Architecture research for: Brownfield Python Codebase Cleanup with Agent Automation*
*Researched: 2026-02-03*
*Confidence: HIGH (verified with official Anthropic docs, Python tooling ecosystem, and awesome-claude-code community resources)*
