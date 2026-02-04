# Project Directory Structure

**Last updated:** 2026-02-04 (Phase 1.1 - Root Documentation Organization)

This document explains the purpose and organization of root-level directories and files.

## Root Directory Overview

The root directory contains only essential files and core directories. All other files are organized into subdirectories by purpose.

### Essential Files

| File | Purpose |
|------|---------|
| `README.md` | Project overview and quick start |
| `ARCHITECTURE.md` | System architecture documentation |
| `requirements.txt` | Python dependencies |
| `pyproject.toml` | Python project configuration (pytest, etc.) |
| `.env` | Environment variables (gitignored) |
| `.env.example` | Example environment configuration |
| `.gitignore` | Git ignore patterns |
| `demo_framework.py` | Framework demonstration script (documentation) |

### Core Directories

#### Source Code

- **`src/`** - Main application source code
  - `core/` - Core pipeline and processing logic
  - `cli/` - Typer-based CLI interface (Phase 1 - replaces old `cli/`)
  - `utils/` - Shared utility functions
  - `models/` - Data models
  - `scrapers/` - Web scraping implementations

- **`tests/`** - Test suite (pytest-based, organized in Phase 1)
  - `unit/` - Unit tests
  - `integration/` - Integration tests
  - `cli/` - CLI tests

- **`config/`** - Configuration files
  - Vendor configurations
  - Pipeline settings
  - Environment-specific configs

#### Data Directories

- **`data/`** - Input data and shared resources
  - `csv/` - Input CSV files for processing
  - `test/` - Test data files (consolidated from old `test_data/`)
  - `input/` - Input data files
  - `output/` - Output data files
  - `backups/` - Data backups
  - `shared_images/` - Shared product images
  - `supplier_images/` - Supplier-provided images

- **`results/`** - Processing results and outputs
  - `csv/` - Output CSV files (processing results, search results, etc.)
  - `scraping/` - Web scraping results (JSON)
  - Additional result subdirectories as needed

#### Documentation

- **`docs/`** - All project documentation
  - `guides/` - User and operator guides
  - `reference/` - Technical reference documentation
  - `implementation/` - Implementation guides
  - `requirements/` - Project requirements
  - `setup/` - Setup and configuration guides
  - `phase-reports/` - Phase completion reports
  - `tasks/` - Task tracking and session notes
  - `legacy/` - Historical documentation (pre-.planning/)
  - `INDEX.md` - Central documentation navigation hub
  - `DIRECTORY_STRUCTURE.md` - This file
  - Technical documentation files (SCRAPER_STRATEGY.md, IMAGE_*.md, etc.)

#### Archive

- **`archive/`** - Archived code and historical artifacts
  - `2026-scripts/` - One-off scripts from Phase 1 cleanup
    - `apply/` - Product application scripts
    - `scrape/` - Scraping scripts
    - `fix/` - Fix/correction scripts
    - `dry-run/` - Dry-run preview scripts
    - `debug/` - Debugging scripts
    - `analysis/` - Analysis scripts
    - `test-scripts/` - Test scripts
    - `misc/` - Miscellaneous scripts
    - `tool-output/` - Dead code analysis and tool outputs
  - `2026-directories/` - Deprecated directories from Phase 1.1
    - `cli-old-argparse/` - Old CLI (replaced by src/cli/)
    - `test_data-original/` - Original test_data directory (consolidated to data/test/)
    - `tasks-original/` - Original tasks directory (moved to docs/tasks/)
    - `temp-snapshot-2026-02-04/` - Temporary files snapshot before cleanup

#### Build Artifacts (Gitignored)

- **`__pycache__/`** - Python bytecode cache
- **`.pytest_cache/`** - Pytest cache
- **`venv/`** - Python virtual environment

#### Active Modules

- **`seo/`** - SEO generation module (standalone with own docs)
- **`utils/`** - Utility modules (shopify_utils, pentart_db, etc.)
- **`web/`** - Web interface components
- **`universal_vendor_scraper/`** - JavaScript-based vendor scraper (documented in ARCHITECTURE.md)

#### Temporary/Debug (Gitignored)

- **`temp/`** - Temporary processing files (gitignored)
- **`screenshots/`** - Web scraper debugging screenshots (gitignored, Feb 2026)
- **`logs/`** - Application logs

#### Development Tools

- **`.claude/`** - Claude Code configuration and workflows
- **`awesome-claude-code/`** - Claude Code integration tools
- **`.planning/`** - GSD (Get Shit Done) planning system
  - `PROJECT.md` - Project overview and requirements
  - `ROADMAP.md` - Development roadmap
  - `STATE.md` - Current project state
  - `phases/` - Phase plans and summaries
  - `codebase/` - Codebase maps (if generated)

## Organization Principles

### Files Belong In Subdirectories

The root directory should contain:
- Essential project files (README, ARCHITECTURE, requirements, etc.)
- Core directory structure
- Demo/example scripts for documentation

The root directory should NOT contain:
- Loose CSV files → Move to `data/csv/` or `results/csv/`
- Loose JSON results → Move to `results/` or `data/`
- Loose documentation → Move to `docs/` subdirectories
- One-off scripts → Archive to `archive/2026-scripts/`
- Temporary files → Use `temp/` (gitignored)

### Git Tracking

**Tracked in Git:**
- All source code (`src/`, `tests/`, `config/`)
- Documentation (`docs/`, `README.md`, `ARCHITECTURE.md`)
- Configuration (`requirements.txt`, `pyproject.toml`, `.gitignore`)
- Planning artifacts (`.planning/`, `.claude/`)

**Gitignored:**
- Data files (`*.csv` - except sample/test data if needed)
- Results (`results/` may be gitignored depending on size)
- Environment variables (`.env`)
- Build artifacts (`__pycache__/`, `venv/`)
- Temporary files (`temp/`, `screenshots/`)
- Logs (`*.log`)

### Module Organization

**Standalone modules** (seo/, utils/, web/):
- Have their own README/documentation or are self-contained
- Can be developed/tested independently
- Referenced by core pipeline but loosely coupled

**Core modules** (src/):
- Tightly integrated application code
- Follow project-wide conventions
- Shared utilities and models

## Migration History

**Phase 1 (Codebase Cleanup):**
- Archived 50+ one-off scripts to `archive/2026-scripts/`
- Consolidated tests to `tests/` directory
- Created new Typer CLI in `src/cli/`
- Documented architecture in `ARCHITECTURE.md`

**Phase 1.1 (Root Documentation Organization):**
- **Plan 01 (Data Files):** Moved 11 CSV files to `data/csv/` and `results/csv/`, moved 6 JSON files to `results/scraping/` and `data/test/`
- **Plan 02 (Documentation & Directories):** Archived deprecated directories (cli/, test_data/, tasks/, temp/) to `archive/2026-directories/`, created docs/ subdirectories (guides/, reference/, legacy/), moved 12 markdown docs to appropriate subdirectories
- **Plan 03 (Documentation Index):** Created documentation index (`docs/INDEX.md`) and this directory structure guide

## Finding What You Need

For detailed navigation to specific documents, see [docs/INDEX.md](INDEX.md).

| I need to... | Look in |
|--------------|---------|
| **Write production code** | `src/` |
| **Write tests** | `tests/` |
| **Add configuration** | `config/` |
| **Process data** | Input: `data/csv/`, Output: `results/csv/` |
| **Read documentation** | `docs/` (start with `docs/INDEX.md`) |
| **Understand architecture** | `ARCHITECTURE.md` |
| **Check project planning** | `.planning/` |
| **Find archived code** | `archive/` |

---

*Organized in Phase 1.1: Root Documentation Organization*
