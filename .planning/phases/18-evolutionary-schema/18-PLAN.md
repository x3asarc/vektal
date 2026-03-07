# Phase 18 Implementation Plan: Evolutionary Schema Engine (Project Nanoclaw)

**Title:** Evolutionary Schema Engine (Self-Writing DNA)
**Date:** 2026-03-06
**Status:** Planning
**Priority:** High (Next after Deployment)

## 1. Objective
Transform the Vektal Platform from a "Static Schema" system to a "Self-Evolving" organism. The system will autonomously detect new data fields in incoming payloads (from Shopify, Suppliers, etc.), infer their data types, and safely expand its own database schema to accommodate them, without requiring human developer intervention for every new field.

## 2. Architecture: The Claw Tier

### 2.1 Picoclaw (The Sensor)
- **Role:** Lightweight, low-latency observer.
- **Location:** `src/api/v1/shopify/webhooks.py` (and other ingest points).
- **Logic:**
  - Compares incoming JSON keys against the known `Product` model columns.
  - Identifies "Alien DNA" (keys that exist in JSON but not in DB).
  - Emits a `schema_anomaly_detected` event to the message bus.
- **Constraints:** Must add < 5ms latency to the webhook response.

### 2.2 Nanoclaw (The Architect)
- **Role:** Asynchronous analyzer and code generator.
- **Location:** `src/core/evolution/architect.py`.
- **Logic:**
  - Consumes `schema_anomaly_detected` events.
  - analyzes the value of the new field (e.g., `"42.50"` -> `Numeric`, `"true"` -> `Boolean`, `[...]` -> `JSON`).
  - Checks **Field Policy** (e.g., "Do not ingest PII", "Ignore temporary tokens").
  - Generates a **Draft Model Definition** (e.g., `carbon_score = db.Column(Numeric(10,2))`).

### 2.3 The Foundry (The Builder)
- **Role:** Safe execution environment for schema changes.
- **Location:** `src/core/evolution/foundry.py`.
- **Workflow:**
  1. **Draft:** Writes the new model code to a temporary branch or file.
  2. **Migration:** Runs `flask db migrate` to generate an Alembic script.
  3. **Sandbox Test:** Applies the migration in a throwaway SQLite/Docker container.
  4. **Validation:** Runs `pytest` to ensure no regressions in core APIs.
  5. **Proposal:** Creates a `SchemaChangeProposal` in the database.

### 2.4 Governance (The Gatekeeper)
- **Role:** Human-in-the-loop control.
- **UI:** A new tab in `CommandCenter`.
- **Action:** User sees "New Field Detected: Carbon Score". User clicks "Approve".
- **Result:** System applies the migration to Production.

## 3. Implementation Waves

### Wave 18.1: The Sensor (Picoclaw)
- Implement `SchemaObserver` class.
- Hook into Webhook Receiver.
- Create `SchemaAnomaly` event model.

### Wave 18.2: The Architect (Nanoclaw)
- Implement `TypeInferenceEngine`.
- Implement `ModelWriter` (AST-based code modification).
- Define `EvolutionPolicy` (allowlist/blocklist patterns).

### Wave 18.3: The Foundry (Sandboxed Migrations)
- Automate Alembic script generation via code.
- Implement the "Test-Apply-Rollback" loop in the sandbox.

### Wave 18.4: Governance & UI
- Create `SchemaProposal` model.
- Add "Evolution" tab to Dashboard.
- Wire up the "Approve -> Apply" button.

## 4. Safety Protocols
1.  **Never blocking:** Webhooks must succeed even if schema evolution fails.
2.  **No destructive changes:** Nanoclaw can ONLY add columns, never delete or modify existing ones.
3.  **Human Gated:** Initially, ALL changes require explicit approval. (Later: auto-approve low-risk fields).

## 5. Success Criteria
- System detects a new field (`test_field`) in a webhook.
- System proposes a migration.
- User approves it.
- Database is updated.
- Subsequent webhooks successfully store `test_field`.
