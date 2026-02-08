# Phase 3: Database Migration (SQLite to PostgreSQL) - Context

**Gathered:** 2026-02-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Set up production PostgreSQL database to replace the temporary Pentart catalog SQLite. Design schema from requirements to support multi-user platform with products, vendors, users, jobs, and Shopify store integration. This is a fresh setup, not a traditional migration.

</domain>

<decisions>
## Implementation Decisions

### Migration Approach
- **Fresh PostgreSQL setup** - Not a true migration from SQLite structure
- Current SQLite is temporary (Pentart catalog only) and NOT the basis for production schema
- Design production schema from scratch based on v1.0 requirements
- Import Pentart data (barcode, SKU, weight only - 3 of 10 columns) as initial vendor catalog data
- Titles were in Hungarian and other columns not applicable - don't rely on full Pentart structure

### Database Schema Design
- Design schema from requirements analysis (Products, Users, Vendors, Jobs, Shopify stores, etc.)
- **Single Shopify store per user** for v1.0 (multi-store deferred to v2.0 per requirements)
- **Vendor catalogs parsed into tables** - Extract CSV data into database tables for fast SQL searching
- Product enrichment data organization (SEO, descriptions, tags) - Claude's discretion

### Credentials and Security
- Investigate current credential storage (user knows they're in .env and Docker secrets per Phase 2)
- Ensure Shopify OAuth tokens and API keys remain decryptable after migration (success criteria)
- Align with Phase 2's Docker secrets implementation

### Connection Pooling
- **Development-friendly configuration** - Small pool sizes, easier debugging, lower resource usage
- Can be adjusted later (production scaling deferred to Phase 13)
- Currently 0 users (still building), optimize for development workflow
- Prevent PostgreSQL max_connections exhaustion (success criteria)

### Backup and Recovery
- **Disaster recovery focus** - Whole database restore if PostgreSQL fails (NOT product version history)
- Product version history is separate concern (Phase 11: SEARCH-05)
- Backup method (pg_dump vs Docker volume snapshots) - Claude's discretion, research tradeoffs
- Automation approach (manual vs scheduled) - Claude's discretion, research best practices
- Storage location (local filesystem vs cloud) - Claude's discretion, research development workflow fit
- Target: Developer can restore database from backup within 5 minutes (success criteria)
- Zero data loss verified by row counts (success criteria)

### Schema Versioning
- Migration tool approach (Alembic vs simple SQL scripts) - Claude's discretion

### Claude's Discretion
- Specific backup method (research pg_dump vs Docker volumes, recommend best for development)
- Backup automation (research manual vs scheduled for dev phase, defer production automation to Phase 13 if appropriate)
- Backup storage location (research local vs cloud options for development)
- Database schema details (table structure, relationships, indexes)
- Product enrichment data organization (same table vs separate tables)
- Schema migration tool selection (Alembic or alternative)
- Connection pool specific sizing (just keep development-friendly)
- PostgreSQL version and configuration settings

</decisions>

<specifics>
## Specific Ideas

- User is cost-conscious about backup storage - research retention policies and compression
- User is "orchestrator" role here, Claude is "developer" - make technical recommendations backed by research
- Pentart CSV had 10 columns, only 3 useful (barcode, SKU, weight) - titles in Hungarian, other columns not applicable
- Success criteria requires encryption preservation and 5-minute restore time

</specifics>

<deferred>
## Deferred Ideas

- Product version history (save data before changes, download images before deletion) - **Phase 11: Product Search & Discovery** (SEARCH-05)
- Automated production backups with cloud storage - **Phase 13: Integration Hardening & Deployment** (DEPLOY-03)
- Production connection pool optimization for scale - **Phase 13: Deployment** or when needed
- Multi-store support - **v2.0** per requirements (out of v1.0 scope)

</deferred>

---

*Phase: 03-database-migration-sqlite-to-postgresql*
*Context gathered: 2026-02-08*
