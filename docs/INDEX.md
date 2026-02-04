# Documentation Index

**Last updated:** 2026-02-04 (Phase 1.1 - Root Documentation Organization)

This index provides navigation to all project documentation. For project architecture, see [ARCHITECTURE.md](../ARCHITECTURE.md) in the root directory.

## Quick Links

- **Getting Started:** [guides/QUICK_START.md](guides/QUICK_START.md)
- **Architecture Overview:** [../ARCHITECTURE.md](../ARCHITECTURE.md)
- **Directory Structure:** [DIRECTORY_STRUCTURE.md](DIRECTORY_STRUCTURE.md)
- **Critical Safeguards:** [guides/CRITICAL_SAFEGUARDS.md](guides/CRITICAL_SAFEGUARDS.md)

## Documentation Categories

### User Guides (`docs/guides/`)

Documentation for end users and operators of the platform:

- **[QUICK_START.md](guides/QUICK_START.md)** - Getting started with the platform
- **[PRODUCT_CREATION_GUIDE.md](guides/PRODUCT_CREATION_GUIDE.md)** - How to create and update products
- **[CRITICAL_SAFEGUARDS.md](guides/CRITICAL_SAFEGUARDS.md)** - Safety mechanisms and approval workflows

### Reference Documentation (`docs/reference/`)

Technical reference materials for developers:

- **[FRAMEWORK_QUICK_REFERENCE.md](reference/FRAMEWORK_QUICK_REFERENCE.md)** - Framework patterns and conventions
- **[README_VISION_AI.md](reference/README_VISION_AI.md)** - Vision AI integration reference
- **[VERIFICATION_CHECKLIST.md](reference/VERIFICATION_CHECKLIST.md)** - Quality verification checklist
- **[hybrid_naming_example.md](reference/hybrid_naming_example.md)** - Image naming convention examples

### Technical Documentation (`docs/`)

Core technical documentation:

- **[SCRAPER_STRATEGY.md](SCRAPER_STRATEGY.md)** - Python vs JavaScript scraper decision criteria and vendor assignments
- **[IMAGE_PROCESSING_FRAMEWORK.md](IMAGE_PROCESSING_FRAMEWORK.md)** - Image transformation framework documentation
- **[IMAGE_VERIFICATION_SYSTEM.md](IMAGE_VERIFICATION_SYSTEM.md)** - Image verification system documentation
- **[IMAGE_FINDING_SYSTEM.md](IMAGE_FINDING_SYSTEM.md)** - Image finding and resolution system
- **[RALPH_WIGGUM_INTEGRATION.md](RALPH_WIGGUM_INTEGRATION.md)** - Ralph Wiggum AI bot integration
- **[PAYLOAD_SCHEMA.md](PAYLOAD_SCHEMA.md)** - Data payload schema documentation
- **[QA_CHECKLIST.md](QA_CHECKLIST.md)** - Quality assurance checklist
- **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Project summary and overview
- **[NEXT_PHASE_PLAN.md](NEXT_PHASE_PLAN.md)** - Next phase planning documentation
- **[CRITICAL_BUG_FIX.md](CRITICAL_BUG_FIX.md)** - Critical bug fix documentation
- **[galaxy_flakes_image_plan_summary.md](galaxy_flakes_image_plan_summary.md)** - Galaxy Flakes image processing summary

### Implementation Guides (`docs/implementation/`)

Implementation documentation:

- **[Implementation documentation](implementation/)** - Phase-specific implementation notes

### Requirements (`docs/requirements/`)

Project requirements and specifications:

- **[Requirements documentation](requirements/)** - Functional and technical requirements

### Setup Documentation (`docs/setup/`)

Environment setup and configuration:

- **[Setup guides](setup/)** - Development environment setup instructions

### Phase Reports (`docs/phase-reports/`)

Execution reports from completed development phases:

- **[Phase completion reports](phase-reports/)** - Historical phase execution summaries

### Task Documentation (`docs/tasks/`)

Task tracking and session notes:

- **[orchestrator_setup_tasks.md](tasks/orchestrator_setup_tasks.md)** - Orchestrator setup task list
- **[SVSE_SESSION_SUMMARY.md](tasks/SVSE_SESSION_SUMMARY.md)** - SVSE session summary
- **[tag_cleanup_context.md](tasks/tag_cleanup_context.md)** - Tag cleanup context and notes

### Legacy Documentation (`docs/legacy/`)

Historical planning documents (pre-.planning/ structure):

- **[phase1-CONTEXT.md](legacy/phase1-CONTEXT.md)** - Original Phase 1 context (superseded by .planning/)
- **[phase1-PLAN.md](legacy/phase1-PLAN.md)** - Original Phase 1 plan (superseded by .planning/)
- **[IMPLEMENTATION_SUMMARY.md](legacy/IMPLEMENTATION_SUMMARY.md)** - Historical implementation summary
- **[PENTART_PRODUCTS_SUMMARY.md](legacy/PENTART_PRODUCTS_SUMMARY.md)** - Pentart products processing summary
- **[SolutionContextProfile.md](legacy/SolutionContextProfile.md)** - Historical solution context profile

**Note:** Legacy docs are kept for historical reference but are superseded by current documentation in `.planning/` directory.

### Investigation Notes (`docs/`)

- **[investigation-notes.md](investigation-notes.md)** - Phase 1.1 directory investigation findings

## Module-Specific Documentation

Some modules maintain their own documentation in root directories:

- **SEO Module:** [../seo/README.md](../seo/README.md) - SEO generation module documentation
- **Vision AI Module:** [../vision_ai/](../vision_ai/) - Vision AI module (if present)

## Development Documentation

- **Planning System:** `../.planning/` directory contains current project planning artifacts
  - `PROJECT.md` - Project overview and requirements
  - `ROADMAP.md` - Development roadmap and phases
  - `STATE.md` - Current project state and progress
  - `phases/` - Phase plans and summaries

## Archive

Historical scripts and artifacts:

- **Script Archive:** `../archive/2026-scripts/` - Archived one-off scripts from Phase 1 cleanup
- **Directory Archive:** `../archive/2026-directories/` - Archived deprecated directories from Phase 1.1

## Finding What You Need

| I want to... | Look here |
|--------------|-----------|
| **Get started using the platform** | [guides/QUICK_START.md](guides/QUICK_START.md) |
| **Understand the architecture** | [../ARCHITECTURE.md](../ARCHITECTURE.md) |
| **Understand directory structure** | [DIRECTORY_STRUCTURE.md](DIRECTORY_STRUCTURE.md) |
| **Learn about safety mechanisms** | [guides/CRITICAL_SAFEGUARDS.md](guides/CRITICAL_SAFEGUARDS.md) |
| **Look up framework patterns** | [reference/FRAMEWORK_QUICK_REFERENCE.md](reference/FRAMEWORK_QUICK_REFERENCE.md) |
| **Understand Vision AI** | [reference/README_VISION_AI.md](reference/README_VISION_AI.md) |
| **Understand scraper strategy** | [SCRAPER_STRATEGY.md](SCRAPER_STRATEGY.md) |
| **Find historical planning docs** | [legacy/](legacy/) directory |
| **Check current project state** | `../.planning/STATE.md` |
| **See development roadmap** | `../.planning/ROADMAP.md` |
| **Find archived scripts** | `../archive/2026-scripts/` |

## Contributing

When adding new documentation:

1. Place in appropriate category directory
2. Update this INDEX.md with a link
3. Follow existing naming conventions (UPPERCASE_WITH_UNDERSCORES.md)
4. Include clear headers and purpose statements

---

*Documentation organized in Phase 1.1 (Root Documentation Organization)*
