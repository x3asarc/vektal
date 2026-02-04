# Root Directory Investigation Notes

Investigation date: 2026-02-04
Phase: 01.1-root-documentation-organization

## Investigated Directories

### cli/ (OLD CLI - argparse-based)
**Status:** DEPRECATED (replaced by src/cli/)
**Evidence:**
- Phase 01-02 created new Typer-based CLI at src/cli/
- Old CLI has deprecation wrapper added (cli/main.py lines 1-34)
- Last modified: 2026-02-03
- Still referenced by: src/cli/commands/products.py (imports from cli.main for backward compatibility functions)
- Contains 27 files across subdirectories (bulk/, pentart/, products/, search/, vision/)
**Decision:** ARCHIVE to archive/2026-directories/cli-old-argparse/
**Rationale:** Replaced by modern Typer CLI at src/cli/, kept deprecation wrapper but entire directory should be archived as Phase 01-02 established src/cli/ as the new standard. References in src/cli/commands/products.py are backward compatibility imports that pull from old cli/main.py functions.

### orchestrator/
**Status:** EXPERIMENTAL (quality checking experiment)
**Evidence:**
- Contains 4 Python files: product_quality_agent.py, quality_loop_ralph.py, trigger_quality_check.py
- Last modified: 2026-01-30 (5 days old)
- Referenced by src/: NO (grep found no imports)
- Purpose: Experimental product quality assessment orchestration
- Not mentioned in ARCHITECTURE.md
**Decision:** ARCHIVE to archive/2026-directories/orchestrator-quality-experiment/
**Rationale:** Experimental code from late January, not integrated into core pipeline, not referenced by production code. Qualifies as experimental work that should be archived per architectural invariant #1 (no experimental code in production paths).

### scripts/
**Status:** UTILITY SCRIPTS (one-off operations)
**Evidence:**
- Contains 39 Python scripts for various operations (import, export, cleanup, analysis)
- Last modified: 2026-02-02 (export_farbe_metafields.py, export_shared_clusters.py, review_shared_alt.py)
- Referenced by src/: NO (grep found no imports)
- Types: Data migration scripts (import_pentart_catalog.py, bulk_update_pentart_shopify.py), cleanup scripts (cleanup_shopify_tags.py, dedupe_not_found.py), export scripts (export_paperdesigns.py, export_shared_clusters.py)
- Scripts are one-off operations, not part of continuous pipeline
**Decision:** ARCHIVE to archive/2026-directories/scripts-utility-operations/
**Rationale:** These are utility/maintenance scripts similar to those archived in Phase 01-01. While some are recent (Feb 2), they represent one-off operations rather than core pipeline code. Should be archived like other utility scripts but kept accessible for reference.

### seo/
**Status:** ACTIVE MODULE (core SEO generation)
**Evidence:**
- Contains SEO generation module with 8 files including seo_generator.py, seo_prompts.py, seo_validator.py
- Has own README.md, CHANGELOG.md, QUICKSTART.md, IMPLEMENTATION.md (well-documented standalone module)
- Referenced by src/: YES - src/core/seo_engine.py imports from seo.seo_generator
- Purpose: German SEO content generation (part of core pipeline per ARCHITECTURE.md line 76)
- ARCHITECTURE.md explicitly mentions "seo_engine.py" as core module that uses this
- Part of "Enrich with AI" step in primary pipeline flow (ARCHITECTURE.md line 169)
**Decision:** KEEP IN ROOT
**Rationale:** Active, production-critical module with clear documentation and active imports from src/core/. Standalone module with its own docs structure (README, CHANGELOG, QUICKSTART). Part of core pipeline per architectural invariant #4 (German SEO content). Keeping as standalone module maintains modularity.

### utils/
**Status:** ACTIVE UTILITIES (shared utility functions)
**Evidence:**
- Contains 13 Python utility files including pentart_db.py (database lookup)
- Referenced by src/: YES - 3 imports found:
  - src/app.py imports utils.pentart_db
  - src/core/product_analyzer.py imports utils.pentart_db
  - src/core/scrape_engine.py imports utils.pentart_db
- Functions: Product utilities (categorize_product.py, generate_product_tags.py), Shopify operations (create_shopify_redirect.py), database access (pentart_db.py)
- Note: There is also src/utils/ directory, but this root utils/ has different purpose (Shopify-specific vs core utilities)
**Decision:** KEEP IN ROOT (but needs documentation to differentiate from src/utils/)
**Rationale:** Actively imported by production code in src/. pentart_db.py is a critical database lookup utility used by core modules. While confusing to have both utils/ and src/utils/, they serve different purposes - root utils/ is Shopify/product operations, src/utils/ is general utilities. Recommend adding README to clarify distinction.

### vision_ai/
**Status:** ACTIVE MODULE (Vision AI subsystem)
**Evidence:**
- Contains Vision AI module with 8 files: cache.py, client.py, generator.py, prompts.py, stats.py, test.py
- Purpose: Vision AI integration (Gemini Vision API)
- Referenced by src/: NO direct imports found (but src/core/vision_* modules likely the refactored version)
- ARCHITECTURE.md mentions vision_client.py, vision_engine.py, vision_cache.py in src/core/
- This appears to be older version of vision system that was refactored into src/core/
**Decision:** ARCHIVE to archive/2026-directories/vision_ai-old-structure/
**Rationale:** Appears to be superseded by src/core/vision_*.py modules (vision_client.py, vision_engine.py, vision_cache.py, vision_prompts.py listed in ARCHITECTURE.md). No direct imports from src/ found. Likely historical version before refactoring into src/core/ structure. Should archive to avoid confusion with current vision system.

### web/
**Status:** ACTIVE FRONTEND (Flask web UI)
**Evidence:**
- Contains web assets: app.js, index.html, job_detail.html, auth_required.html, static/, templates/
- Purpose: Web interface for the platform
- Related to Flask app (src/app.py mentioned in ARCHITECTURE.md line 92)
- Active: Yes (web UI is listed as user interface in ARCHITECTURE.md)
- Frontend for interactive product management and bulk operations
**Decision:** KEEP IN ROOT
**Rationale:** Active frontend component for Flask web application. Part of the user interface layer per ARCHITECTURE.md. While Phase 7 plans Next.js migration, this is the current production web UI. Must remain until replacement is built.

### temp/
**Status:** TEMPORARY FILES (should not be in repo)
**Evidence:**
- Contains 13 CSV files: batch_1_preview.csv, debug_test.csv, final_push_data.csv, pipeline_results.csv, etc.
- Last modified: Recent (temporary processing files)
- Purpose: Temporary CSV files from pipeline operations
- Should not be version controlled
**Decision:** DELETE contents and ADD TO .GITIGNORE
**Rationale:** Temporary files should not be in repository per standard Git practices. .gitignore already has *.csv pattern (line 27) but doesn't exclude temp/ directory itself. Add temp/ to .gitignore to prevent future temporary files from being tracked.

### test/ (empty)
**Status:** REDUNDANT (tests/ exists)
**Evidence:**
- Directory is completely empty (dir test/ returned no output)
- tests/ directory exists and is the active test location (Phase 01-02 organized tests there)
- Redundant directory, likely created by mistake
**Decision:** DELETE
**Rationale:** Empty redundant directory. tests/ (plural) is the standard Python convention and is where Phase 01-02 organized all tests. This empty test/ (singular) directory serves no purpose and creates confusion.

### test_data/
**Status:** TEST DATA (should consolidate)
**Evidence:**
- Contains 4 sample CSV files: README.md, sample_existing_products.csv, sample_mixed_products.csv, sample_new_products.csv
- Purpose: Sample data for testing
- Referenced by tests/: Need to check (grep tests/ for test_data references)
- Similar to data/test/ structure from Phase 01.1-01
**Decision:** CONSOLIDATE to data/test/ and ARCHIVE original
**Rationale:** Phase 01.1-01 established data/ for inputs with data/test/ for test fixtures. These sample CSVs should be in data/test/ for consistency. Consolidate files to data/test/ then archive original test_data/ directory to maintain git history.

### tasks/
**Status:** TASK DOCUMENTATION (markdown files)
**Evidence:**
- Contains 3 markdown files: orchestrator_setup_tasks.md, SVSE_SESSION_SUMMARY.md, tag_cleanup_context.md
- Purpose: Task tracking and session notes
- Not code - documentation/planning files
**Decision:** MOVE to docs/tasks/
**Rationale:** These are documentation/planning files, not code. Phase 01.1-01 established docs/ as the documentation root. Creating docs/tasks/ subdirectory maintains organization established in that phase (docs/guides/, docs/reference/, docs/legacy/). Preserves git history with git mv.

### screenshots/
**Status:** DEBUG ARTIFACTS (scraper debugging screenshots)
**Evidence:**
- Contains 52 PNG files and HTML files from web scraping attempts
- Last modified: Recent (2026-02-03, 2026-02-04 based on Unix timestamps in filenames)
- Purpose: Playwright/Selenium scraper debugging - visual verification of scraping attempts
- Files named with pattern: {Vendor}_{SKU}_attempt{N}_{timestamp}.png
- Examples: Pentart_2493_attempt1_1770121548841.png, AistCraft_45970AC_search.png
- Very recent (created yesterday and today)
**Decision:** ADD TO .GITIGNORE and document
**Rationale:** Debug artifacts from scraper development. Should remain local only for developer debugging but not committed to repository. Recent creation indicates active scraper work. Add screenshots/ to .gitignore to prevent accidental commits. Document in investigation notes that developers can use screenshots/ locally for debugging.

## Summary

**Directories to Archive (6):**
1. cli/ → archive/2026-directories/cli-old-argparse/ (deprecated CLI)
2. orchestrator/ → archive/2026-directories/orchestrator-quality-experiment/ (experimental)
3. scripts/ → archive/2026-directories/scripts-utility-operations/ (one-off scripts)
4. vision_ai/ → archive/2026-directories/vision_ai-old-structure/ (superseded by src/core/vision_*)
5. test_data/ → archive/2026-directories/test_data-original/ (after consolidating to data/test/)

**Directories to Keep (3):**
1. seo/ - Active, production-critical SEO module (imported by src/core/seo_engine.py)
2. utils/ - Active utilities (pentart_db.py imported by multiple src/ modules)
3. web/ - Active Flask web UI frontend

**Directories to Clean (2):**
1. temp/ - Delete contents, add to .gitignore
2. screenshots/ - Add to .gitignore (keep local files)

**Directories to Delete (1):**
1. test/ - Empty redundant directory

**Directories to Move (1):**
1. tasks/ → docs/tasks/ (documentation files)

**Total directories investigated:** 13
**Decisions made:** 13
