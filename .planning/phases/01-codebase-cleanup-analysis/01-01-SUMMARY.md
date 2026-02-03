---
phase: 01-codebase-cleanup-analysis
plan: 01
subsystem: codebase-organization
tags: [archive, cleanup, dead-code-analysis, vulture, deadcode, refactoring]

# Dependency graph
requires:
  - phase: 00-research
    provides: Roadmap and understanding of 50+ scripts cluttering root directory
provides:
  - Clean root directory with only essential files (demo_framework.py)
  - 57 scripts archived in archive/2026-scripts/ with 8 category subdirectories
  - MANIFEST.md documenting all archived scripts with original purpose
  - DEAD_CODE_REPORT.md analyzing 46 potential dead code items in src/core/ and cli/
  - Clear distinction between production code (src/core/) and experimental scripts
affects: [01-02-unified-cli, 01-03-framework-testing, future-refactoring-phases]

# Tech tracking
tech-stack:
  added: [vulture, deadcode]
  patterns: [archive-by-category, git-history-preservation]

key-files:
  created:
    - archive/2026-scripts/MANIFEST.md
    - archive/2026-scripts/DEAD_CODE_REPORT.md
    - archive/2026-scripts/apply/ (3 scripts)
    - archive/2026-scripts/scrape/ (5 scripts)
    - archive/2026-scripts/fix/ (4 scripts)
    - archive/2026-scripts/dry-run/ (4 scripts)
    - archive/2026-scripts/debug/ (4 scripts)
    - archive/2026-scripts/analysis/ (8 scripts)
    - archive/2026-scripts/test-scripts/ (3 scripts)
    - archive/2026-scripts/misc/ (26 scripts)
  modified: []

key-decisions:
  - "Archived by category (apply, scrape, fix, dry-run, debug, analysis, test-scripts, misc) for maintainability"
  - "Kept demo_framework.py in root as documentation example"
  - "Used physical file moves instead of git mv due to untracked files in fresh repo"
  - "Identified 17 false positives (Flask/Click decorators) in dead code analysis"

patterns-established:
  - "Archive pattern: archive/YYYY-scripts/{category}/ for organizing historical one-off scripts"
  - "MANIFEST.md pattern: Table with Script | Category | Original Purpose | Date Archived"
  - "Dead code analysis without deletion: Document findings, categorize by confidence, flag false positives"

# Metrics
duration: 19min
completed: 2026-02-03
---

# Phase 01 Plan 01: Codebase Cleanup Summary

**57 one-off scripts archived into 8 categories with MANIFEST.md documentation; dead code analysis identified 4 safe-to-remove unused imports and 17 false positives in Flask/Click decorators**

## Performance

- **Duration:** 19 min
- **Started:** 2026-02-03T19:18:57Z
- **Completed:** 2026-02-03T20:38:06Z
- **Tasks:** 3
- **Files modified:** 60 (57 scripts moved + MANIFEST.md + DEAD_CODE_REPORT.md + tool outputs)

## Accomplishments

- Root directory cleaned: 50 Python files + 8 JavaScript files reduced to 2 Python files (demo_framework.py + requirements.txt)
- 57 scripts organized into 8 logical categories in archive/2026-scripts/
- MANIFEST.md with 106 lines documenting every archived script's purpose
- DEAD_CODE_REPORT.md analyzing 46 potential dead code items with confidence levels and false positive identification
- src/core/ production code untouched (0 modifications as required)

## Task Commits

Each task was committed atomically:

1. **Task 1: Classify root scripts and create archive structure** - `25e6a4d` (feat)
   - Created 8 category directories
   - Created MANIFEST.md with 58 script entries

2. **Task 2: Move scripts to archive** - `42e4bbf` (chore)
   - Moved 57 scripts to categorized subdirectories
   - Preserved only demo_framework.py in root
   - Used physical file moves (fresh repo, files untracked)

3. **Task 3: Run dead code detection** - `c9a49dc` (docs)
   - Installed Vulture and deadcode
   - Ran analysis on src/, cli/ (excluded archive/, venv/)
   - Created DEAD_CODE_REPORT.md with categorized findings

**Plan metadata:** (to be committed separately)

## Files Created/Modified

**Created:**
- `archive/2026-scripts/MANIFEST.md` - Index of all 58 archived scripts with original purpose
- `archive/2026-scripts/DEAD_CODE_REPORT.md` - Dead code analysis with 46 findings categorized by confidence
- `archive/2026-scripts/apply/` - 3 scripts (apply_all_galaxy_flakes_sop, apply_saturn_green variants)
- `archive/2026-scripts/scrape/` - 5 scripts (scrape_and_upload_images, scrape_paperdesigns_missing, etc.)
- `archive/2026-scripts/fix/` - 4 scripts (fix_pentart_products, auto_fix_images, etc.)
- `archive/2026-scripts/dry-run/` - 4 scripts (dry_run_pluto_yellow, dry_run_saturn_green, etc.)
- `archive/2026-scripts/debug/` - 4 scripts (debug_aistcraft.js, debug_itd.js, debug_pentart.js, debug_single_vendor.js)
- `archive/2026-scripts/analysis/` - 8 scripts (analyze_deleted_images, find_missing_products, search_broad, etc.)
- `archive/2026-scripts/test-scripts/` - 3 scripts (test_pentart_scraper, test_product_creation, test_universal_scraper)
- `archive/2026-scripts/misc/` - 26 scripts (all remaining one-off scripts)
- `vulture_output.txt` - Vulture analysis output (6 findings, 80%+ confidence)
- `deadcode_output.txt` - deadcode analysis output (46 findings across multiple categories)

**Modified:**
- None (src/core/ untouched as required by constraints)

**Moved from root:**
- 50 Python files → archive/2026-scripts/{category}/
- 8 JavaScript files → archive/2026-scripts/{category}/

## Decisions Made

1. **Archive categorization:** Used 8 categories (apply, scrape, fix, dry-run, debug, analysis, test-scripts, misc) based on script naming patterns and purpose analysis
   - Rationale: Clear functional grouping makes it easier to find scripts later if logic needs extraction

2. **Kept demo_framework.py in root:** Decided to keep as documentation example
   - Rationale: Shows developers how to use the framework; different purpose than archived experimental scripts

3. **Physical file moves instead of git mv:** Used `mv` commands instead of `git mv`
   - Rationale: Files were untracked in fresh repo; git mv only works on tracked files

4. **False positive identification in dead code report:** Explicitly categorized Flask route handlers and Click CLI commands as false positives
   - Rationale: Static analysis tools cannot detect decorator-based function registration; prevents accidental deletion of active routes

5. **Analysis-only approach:** Dead code report documents findings but does not delete code
   - Rationale: Production code constraint (src/core/ must not be modified without thorough testing)

## Deviations from Plan

None - plan executed exactly as written.

All tasks completed according to specification:
- Task 1: Archive structure and MANIFEST.md created with 8 categories
- Task 2: 57 scripts moved to archive with only demo_framework.py remaining
- Task 3: Dead code analysis completed with categorized findings

No auto-fixes were needed during execution.

## Issues Encountered

**Issue 1: git mv failed on untracked files**
- **Problem:** Initial attempt to use `git mv` failed with "not under version control" error
- **Cause:** Fresh repository with untracked files (git mv requires tracked files)
- **Resolution:** Used physical `mv` commands, then staged all changes with `git add`
- **Impact:** Preserved all file contents; git history shows files as "new" rather than "moved" (acceptable for fresh repo)

**Issue 2: Vulture exit code 3**
- **Problem:** Vulture command returned exit code 3
- **Cause:** Exit code 3 is expected when dead code is found (not an error)
- **Resolution:** Captured output successfully; interpreted exit code correctly
- **Impact:** None; output was usable

## User Setup Required

None - no external service configuration required.

This plan only reorganized existing code and ran static analysis tools.

## Next Phase Readiness

**Ready for next phase:**
- Root directory clean and organized
- Clear distinction established between production code (src/core/) and experimental scripts (archive/)
- Dead code analysis documented for future cleanup planning
- MANIFEST.md provides reference for any archived script that may need logic extraction

**Potential for future phases:**
- Plan 01-02 can build unified CLI without root directory clutter
- Plan 01-03 can test framework with clear understanding of production vs experimental code
- Future refactoring phases can reference DEAD_CODE_REPORT.md for safe cleanup opportunities

**No blockers or concerns.**

---
*Phase: 01-codebase-cleanup-analysis*
*Completed: 2026-02-03*
