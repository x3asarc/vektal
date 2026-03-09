# FAILURE_JOURNEY

Purpose: capture dead ends and hard lessons so future tasks do not repeat them.

## Entry Format
1. Date and task id.
2. Tried X.
3. Failed Y.
4. Doing Z.
5. Preventive rule added.

## Entries

### 2026-02-12 | 07.1-governance-baseline-dry-run
1. Tried X: enforce full governance baseline in one pass without task-scoped evidence templates.
2. Failed Y: report schema ambiguity caused inconsistent evidence fields.
3. Doing Z: standardized four report templates and strict `N/A` policy for non-applicable fields.
4. Preventive rule added: no task closes without exact four reports and non-empty required fields.
5. Anti-drift handling: if report schema drifts from templates, stop closure and re-bootstrap from `reports/templates/`.
6. Anti-stubborn handling: after two failed closure attempts on the same task, trigger scope reset and checkpoint re-plan.

### 2026-03-01 | 14.3-self-healing
1. Tried X: Autonomous execution of knowledge graph tools.
2. Failed Y: AURA_UNREACHABLE: Neo4jError: ServiceUnavailable (Aura Paused) (Culprit: src/core/graphiti_client.py)
3. Doing Z: Triggering autonomous remediator via orchestrate_healers.py
4. Preventive rule added: none (automated ingestion)

### 2026-03-01 | 14.3-self-healing
1. Tried X: Autonomous execution of knowledge graph tools.
2. Failed Y: SNAPSHOT_CORRUPT: FileNotFoundError: .graph/local-snapshot.json missing (Culprit: src/graph/local_graph_store.py)
3. Doing Z: Triggering autonomous remediator via orchestrate_healers.py
4. Preventive rule added: none (automated ingestion)

### 2026-03-01 | 14.3-self-healing
1. Tried X: Autonomous execution of knowledge graph tools.
2. Failed Y: AURA_UNREACHABLE: Neo4jError: ServiceUnavailable (Aura Paused) (Culprit: src/core/graphiti_client.py)
3. Doing Z: Triggering autonomous remediator via orchestrate_healers.py
4. Preventive rule added: none (automated ingestion)

### 2026-03-01 | 14.3-self-healing
1. Tried X: Autonomous execution of knowledge graph tools.
2. Failed Y: SNAPSHOT_CORRUPT: FileNotFoundError: .graph/local-snapshot.json missing (Culprit: src/graph/local_graph_store.py)
3. Doing Z: Triggering autonomous remediator via orchestrate_healers.py
4. Preventive rule added: none (automated ingestion)

### 2026-03-01 | 14.3-self-healing
1. Tried X: Autonomous execution of knowledge graph tools.
2. Failed Y: AURA_UNREACHABLE: Neo4jError: ServiceUnavailable (Aura Paused) (Culprit: src/core/graphiti_client.py)
3. Doing Z: Triggering autonomous remediator via orchestrate_healers.py
4. Preventive rule added: none (automated ingestion)

### 2026-03-01 | 14.3-self-healing
1. Tried X: Autonomous execution of knowledge graph tools.
2. Failed Y: SNAPSHOT_CORRUPT: FileNotFoundError: .graph/local-snapshot.json missing (Culprit: src/graph/local_graph_store.py)
3. Doing Z: Triggering autonomous remediator via orchestrate_healers.py
4. Preventive rule added: none (automated ingestion)

### 2026-03-02 | 14.3-self-healing
1. Tried X: Autonomous execution of knowledge graph tools.
2. Failed Y: AURA_UNREACHABLE: Neo4jError: ServiceUnavailable (Aura Paused) (Culprit: src/core/graphiti_client.py)
3. Doing Z: Triggering autonomous remediator via orchestrate_healers.py
4. Preventive rule added: none (automated ingestion)

### 2026-03-02 | 14.3-self-healing
1. Tried X: Autonomous execution of knowledge graph tools.
2. Failed Y: SNAPSHOT_CORRUPT: FileNotFoundError: .graph/local-snapshot.json missing (Culprit: src/graph/local_graph_store.py)
3. Doing Z: Triggering autonomous remediator via orchestrate_healers.py
4. Preventive rule added: none (automated ingestion)

### 2026-03-02 | 14.3-self-healing
1. Tried X: Autonomous execution of knowledge graph tools.
2. Failed Y: AURA_UNREACHABLE: Neo4jError: ServiceUnavailable (Aura Paused) (Culprit: src/core/graphiti_client.py)
3. Doing Z: Triggering autonomous remediator via orchestrate_healers.py
4. Preventive rule added: none (automated ingestion)

### 2026-03-02 | 14.3-self-healing
1. Tried X: Autonomous execution of knowledge graph tools.
2. Failed Y: SNAPSHOT_CORRUPT: FileNotFoundError: .graph/local-snapshot.json missing (Culprit: src/graph/local_graph_store.py)
3. Doing Z: Triggering autonomous remediator via orchestrate_healers.py
4. Preventive rule added: none (automated ingestion)

### 2026-03-03 | 14.3-self-healing
1. Tried X: Autonomous execution of knowledge graph tools.
2. Failed Y: UNKNOWN: ProgrammingError: (psycopg.errors.UndefinedFunction) operator does not exist: json || jsonb (Culprit: alembic.operations.base in execute)
3. Doing Z: Triggering autonomous remediator via orchestrate_healers.py
4. Preventive rule added: none (automated ingestion)

### 2026-03-03 | 14.3-self-healing
1. Tried X: Autonomous execution of knowledge graph tools.
2. Failed Y: UNKNOWN: ProgrammingError: (psycopg.errors.CannotCoerce) COALESCE could not convert type jsonb to json (Culprit: alembic.operations.base in execute)
3. Doing Z: Triggering autonomous remediator via orchestrate_healers.py
4. Preventive rule added: none (automated ingestion)

### 2026-03-03 | 14.3-self-healing
1. Tried X: Autonomous execution of knowledge graph tools.
2. Failed Y: UNKNOWN: ValueError: Test exception from Phase 15 - verifying error tracking (Culprit: __main__ in <module>)
3. Doing Z: Triggering autonomous remediator via orchestrate_healers.py
4. Preventive rule added: none (automated ingestion)

### 2026-03-03 | 14.3-self-healing
1. Tried X: Autonomous execution of knowledge graph tools.
2. Failed Y: UNKNOWN: OperationalError: (psycopg.OperationalError) failed to resolve host 'db': [Errno 11001] getaddrinfo failed (Culprit: env_py in run_migrations_online)
3. Doing Z: Triggering autonomous remediator via orchestrate_healers.py
4. Preventive rule added: none (automated ingestion)

### 2026-03-03 | 14.3-self-healing
1. Tried X: Autonomous execution of knowledge graph tools.
2. Failed Y: UNKNOWN: ProgrammingError: (psycopg.errors.UndefinedTable) relation "assistant_tool_registry" does not exist (Culprit: alembic.operations.base in execute)
3. Doing Z: Triggering autonomous remediator via orchestrate_healers.py
4. Preventive rule added: none (automated ingestion)

### 2026-03-03 | 14.3-self-healing
1. Tried X: Autonomous execution of knowledge graph tools.
2. Failed Y: UNKNOWN: ProgrammingError: (psycopg.errors.DuplicateColumn) column "schema_json" of relation "assistant_tool_registry" already exists (Culprit: alembic.operations.base in add_column)
3. Doing Z: Triggering autonomous remediator via orchestrate_healers.py
4. Preventive rule added: none (automated ingestion)

### 2026-03-04 | 14.3-self-healing
1. Tried X: Autonomous execution of knowledge graph tools.
2. Failed Y: AURA_UNREACHABLE: Neo4jError: ServiceUnavailable (Aura Paused) (Culprit: src/core/graphiti_client.py)
3. Doing Z: Triggering autonomous remediator via orchestrate_healers.py
4. Preventive rule added: none (automated ingestion)

### 2026-03-04 | 14.3-self-healing
1. Tried X: Autonomous execution of knowledge graph tools.
2. Failed Y: SNAPSHOT_CORRUPT: FileNotFoundError: .graph/local-snapshot.json missing (Culprit: src/graph/local_graph_store.py)
3. Doing Z: Triggering autonomous remediator via orchestrate_healers.py
4. Preventive rule added: none (automated ingestion)

### 2026-03-08 | 14.3-self-healing
1. Tried X: Autonomous execution of knowledge graph tools.
2. Failed Y: AURA_UNREACHABLE: Neo4jError: ServiceUnavailable (Aura Paused) (Culprit: src/core/graphiti_client.py)
3. Doing Z: Triggering autonomous remediator via orchestrate_healers.py
4. Preventive rule added: none (automated ingestion)

### 2026-03-08 | 14.3-self-healing
1. Tried X: Autonomous execution of knowledge graph tools.
2. Failed Y: SNAPSHOT_CORRUPT: FileNotFoundError: .graph/local-snapshot.json missing (Culprit: src/graph/local_graph_store.py)
3. Doing Z: Triggering autonomous remediator via orchestrate_healers.py
4. Preventive rule added: none (automated ingestion)
</module>
### 2026-03-09 | 14.3-self-healing
1. Tried X: Autonomous execution of knowledge graph tools.
2. Failed Y: AURA_UNREACHABLE: Neo4jError: ServiceUnavailable (Aura Paused) (Culprit: src/core/graphiti_client.py)
3. Doing Z: Triggering autonomous remediator via orchestrate_healers.py
4. Preventive rule added: none (automated ingestion)

### 2026-03-09 | 14.3-self-healing
1. Tried X: Autonomous execution of knowledge graph tools.
2. Failed Y: SNAPSHOT_CORRUPT: FileNotFoundError: .graph/local-snapshot.json missing (Culprit: src/graph/local_graph_store.py)
3. Doing Z: Triggering autonomous remediator via orchestrate_healers.py
4. Preventive rule added: none (automated ingestion)

### 2026-03-09 | 14.3-self-healing
1. Tried X: Autonomous execution of knowledge graph tools.
2. Failed Y: UNKNOWN: SystemExit: 1 (Culprit: src.api.v1.chat.routes in generate)
3. Doing Z: Triggering autonomous remediator via orchestrate_healers.py
4. Preventive rule added: none (automated ingestion)

### 2026-03-09 | 14.3-self-healing
1. Tried X: Autonomous execution of knowledge graph tools.
2. Failed Y: UNKNOWN: IntegrityError: (psycopg.errors.NotNullViolation) null value in column "access_token_encrypted" of relation "shopify_stores" violates not-null constraint (Culprit: sqlalchemy.orm.session in _prepare_impl)
3. Doing Z: Triggering autonomous remediator via orchestrate_healers.py
4. Preventive rule added: none (automated ingestion)

### 2026-03-09 | 14.3-self-healing
1. Tried X: Autonomous execution of knowledge graph tools.
2. Failed Y: UNKNOWN: ProgrammingError: (psycopg.errors.UndefinedTable) relation "users" does not exist (Culprit: auth.login)
3. Doing Z: Triggering autonomous remediator via orchestrate_healers.py
4. Preventive rule added: none (automated ingestion)
