---
status: investigating
trigger: "chat-unfilled-template-and-ingest-broken"
created: 2026-02-18T00:00:00Z
updated: 2026-02-18T00:00:00Z
---

## Current Focus

hypothesis: The chat response pipeline does NOT call the AI to generate conversational replies — it uses static handler functions that return hardcoded messages. When any message fails pattern/local classification, APILLMClassifier sends it to OpenRouter for INTENT CLASSIFICATION ONLY (not reply generation). The chat response is assembled from handler return values. The garbled text the user sees is the handle_unknown() return value mixed with a failed AI response attempt, OR (more likely) a MISSING AI-GENERATED REPLY LAYER — the system was designed expecting a tier-routed AI response but none is wired up end-to-end for conversational replies.
test: traced full call chain from routes.py create_message → _CHAT_ROUTER.route() → handlers → _build_assistant_blocks()
expecting: The root cause is that the system shows static handler text (not AI responses) because no conversational LLM call is made in the create_message path
next_action: Write fixes — (1) chat response is from static handlers, not AI; (2) ingest queue routing mismatch

## Symptoms

expected: User sends a chat message → AI processes it and returns a meaningful natural language response about their Shopify products
actual: AI responds with something like "Did not understand your response. {subject} {task} {product_id} {sku}" — literal unfilled template placeholders in the response
errors: No visible crash. UI loads, message sends (with delay), response arrives but contains garbled template text
reproduction: Install app on Shopify dev store via Cloudflare tunnel → open chat → send any message → receive garbled template response
timeline: First noticed when testing live on Shopify dev store. App was never confirmed working end-to-end.
ingest: Ingest function also broken — no product data being pulled/synced. Likely a Celery worker issue.
setup: Docker Compose stack (backend, celery_worker, celery_scraper, flower, db, redis, nginx). OPENROUTER_API_KEY is set in .env.

## Eliminated

- hypothesis: Template placeholders {subject} {task} {product_id} {sku} are from a backend Python template
  evidence: Searched all .py, .ts, .tsx, .yaml files — these specific variable names do not appear in any backend template string
  timestamp: 2026-02-18

- hypothesis: The garbled text comes from a Shopify extension/Liquid template
  evidence: No extensions/ or .liquid files exist in the repo
  timestamp: 2026-02-18

- hypothesis: The frontend is generating this text from a buggy JS template
  evidence: Searched frontend/src/ — "Did not understand" and the variable names do not appear anywhere in frontend code
  timestamp: 2026-02-18

- hypothesis: The ingest task is on the wrong queue topology
  evidence: queueing.py TASK_ROUTES and docker-compose.yml queues are actually aligned — start_ingest_task goes to control queue, celery_worker handles control queue; chunk tasks go to batch.t1-3, celery_scraper handles those. Queue routing itself is correct.
  timestamp: 2026-02-18

## Evidence

- timestamp: 2026-02-18
  checked: src/api/v1/chat/routes.py create_message() — the full message handling flow
  found: |
    Line 612: route_result = _CHAT_ROUTER.route(payload.content)
    Line 615-622: route_summary = resolve_route_decision(...) — separate, returns metadata not response text
    Line 736: assistant_blocks = _build_assistant_blocks(route_result, ...)
    Line 262-264 in _build_assistant_blocks: primary_text = response_payload.get("message") OR f"Intent classified as `{route_result.intent.type.value}`."
    The response TEXT comes ENTIRELY from static handler functions, never from an LLM.
    NO AI API call is made for the actual conversational reply in the create_message path.
  implication: The chat system is missing the conversational AI response layer. It only classifies intent and returns static handler text.

- timestamp: 2026-02-18
  checked: src/core/chat/handlers/generic.py handle_unknown()
  found: Returns {"status": "unknown", "message": f"I didn't understand: '{intent.raw_message}'", "suggestions": [...]}
  implication: For any unclassified message, the response is literally "I didn't understand: 'hello world'" — not an AI response.

- timestamp: 2026-02-18
  checked: src/core/chat/router.py APILLMClassifier.classify()
  found: |
    Sends message to OpenRouter model google/gemini-flash-1.5 for INTENT CLASSIFICATION only.
    Expects JSON {"intent": "...", "confidence": 0-100, "sku": "..."} back.
    If the API returns non-JSON (e.g., conversational text), json.loads() fails.
    Exception caught → returns IntentType.UNKNOWN with confidence=0.0.
    This is only for routing, not for generating the reply.
  implication: OpenRouter IS called but only to classify intent. The API response is parsed as JSON and discarded (only intent/confidence extracted). The model's actual text output is never shown to the user.

- timestamp: 2026-02-18
  checked: src/assistant/runtime_tier1.py, runtime_tier2.py
  found: These return metadata payloads only — {"mode": "read_safe", ...} — no AI calls.
  implication: The "runtime" tier system in assistant/ is infrastructure scaffolding (reliability, routing) not actual AI generation.

- timestamp: 2026-02-18
  checked: src/tasks/assistant_runtime.py run_tier_runtime()
  found: Celery task that handles reliability/circuit breaker logic but does NOT make any AI API call. Returns {"status": "accepted", "payload": ...}.
  implication: The run_tier_runtime task is just a reliability wrapper. No AI generation happens here either.

- timestamp: 2026-02-18
  checked: docker-compose.yml celery_worker command
  found: "-Q control,interactive.t1,interactive.t2,interactive.t3" — listens on interactive queues but NOT assistant.t1/t2/t3
  implication: |
    INGEST BUG: The assistant runtime queue (assistant.t1/t2/t3) is defined in queueing.py but NO worker in docker-compose.yml listens to it.
    WORKER_QUEUE_SPLIT in queueing.py defines "celery_assistant" for assistant queues, but no "celery_assistant" service exists in docker-compose.yml.
    Any tasks sent to assistant.t1/t2/t3 will queue indefinitely and never execute.

- timestamp: 2026-02-18
  checked: src/jobs/queueing.py WORKER_QUEUE_SPLIT
  found: |
    "celery_assistant": [*ASSISTANT_RUNTIME_QUEUES.values(), ASSISTANT_TIER3_DEAD_LETTER_QUEUE]
    assistant.t1, assistant.t2, assistant.t3 queues defined but NO docker service handles them.
  implication: This confirms the assistant worker is missing from docker-compose.yml.

- timestamp: 2026-02-18
  checked: src/core/chat/router.py APILLMClassifier line 273-279
  found: |
    if not self.api_key:
        return Intent(type=IntentType.UNKNOWN, confidence=0.0, raw_message=message, method="api_llm")
    If OPENROUTER_API_KEY is missing/empty in the backend container, classification returns UNKNOWN immediately.
    Then handle_unknown() returns "I didn't understand: '{user_message}'"
  implication: |
    The CHAT SYMPTOM is explained: if OPENROUTER_API_KEY is not passing correctly to the backend container,
    or pattern matching fails (e.g., user sends "hello"), the response is the static "I didn't understand" message.
    This is NOT garbled AI output — it IS the expected fallback, just never designed to look like a proper response.

- timestamp: 2026-02-18
  checked: docker-compose.yml backend environment section
  found: "- OPENROUTER_API_KEY=${OPENROUTER_API_KEY}" — correct, reads from .env
  implication: If .env has OPENROUTER_API_KEY set correctly, the backend should have it. Need to verify the key works.

## Root Cause

### CHAT ROOT CAUSE
The chat response system has a fundamental architectural gap: it was designed to show static handler responses (pattern-matched intent → handler function → static text) but the production use case requires AI-generated conversational replies.

When a user sends a natural language message like "hello" or "what products do I have?":
1. Pattern matching in ChatRouter fails (no pattern matches conversational text)
2. Local LLM (sentence-transformers) may or may not be loaded (adds latency)
3. APILLMClassifier sends to OpenRouter to classify intent as JSON — not to generate a reply
4. If classification returns UNKNOWN (or any intent), handle_unknown() or the matched handler returns STATIC TEXT
5. The user sees "I didn't understand: 'hello'" which looks garbled

The `{subject} {task} {product_id} {sku}` variables the user reported are most likely coming from:
- The OpenRouter model responding to the JSON classification prompt with something unexpected
- When json.loads() fails, the exception is caught and UNKNOWN is returned
- The user's message itself may contain template-like tokens
- OR: the user is describing the situation loosely and the actual text is the static "I didn't understand: '...'" message

The CORE ISSUE is that the chat system lacks a conversational AI response generation layer. The create_message route in routes.py never calls the LLM to generate a human-readable reply — it only classifies intent and returns static text.

### INGEST ROOT CAUSE
The `celery_assistant` worker defined in `WORKER_QUEUE_SPLIT` in `src/jobs/queueing.py` does NOT exist as a service in `docker-compose.yml`. The assistant runtime queues `assistant.t1`, `assistant.t2`, `assistant.t3` have no worker consuming them.

Additionally, the `run_tier_runtime` Celery task (which handles assistant delegation) would never execute because no worker listens to `assistant.t1/t2/t3`.

For basic ingest (not assistant-related): the ingest task itself routes correctly. The real ingest problem may be that:
1. Products have never been added to the PostgreSQL database (store is new, no products imported yet)
2. The ingest job creates chunks of existing `Product` rows — if no products exist, nothing is ingested
3. The "ingest" the user expects is likely Shopify product IMPORT (pulling from Shopify API), but `ingest_chunk` in orchestrator.py just marks existing DB rows as processed — it does NOT fetch from Shopify

## Fix

### Fix 1: CHAT — Make the system return a meaningful response
The quickest fix is to make `handle_unknown` return a more helpful message and ensure the intent classification works correctly. The deeper fix is to add an LLM response generation step.

**Immediate fix — improve handle_unknown response:**

File: `src/core/chat/handlers/generic.py`

Before (line 146-161):
```python
def handle_unknown(self, intent) -> dict:
    return {
        "status": "unknown",
        "message": f"I didn't understand: '{intent.raw_message}'",
        "suggestions": [
            "Try typing a SKU like R0530",
            ...
        ],
        ...
    }
```

After:
```python
def handle_unknown(self, intent) -> dict:
    return {
        "status": "unknown",
        "message": (
            "I can help you manage your Shopify products. "
            "Try commands like: 'add R0530', 'update SKU-100', 'list vendors', or just type a SKU."
        ),
        "suggestions": [
            "Type a SKU directly (e.g. R0530) to add it",
            "Type 'help' to see available commands",
            "Use natural language: 'find vendor for R0530'"
        ],
        "actions": [
            {
                "type": "help",
                "label": "Show help",
                "command": "help"
            }
        ]
    }
```

**Root fix — add conversational AI response generation:**
The `create_message` route in `routes.py` needs to call the AI to generate a response. This should happen as a post-classification step where the AI is given context (intent, entities, store data) and generates a human-readable reply. This is a larger architectural addition.

### Fix 2: INGEST — Add celery_assistant service or re-route assistant tasks
Since no `celery_assistant` service exists in docker-compose.yml, add it:

File: `docker-compose.yml`

Add after celery_scraper service:
```yaml
  celery_assistant:
    build:
      context: .
      dockerfile: Dockerfile.backend
    volumes:
      - ./src:/app/src
      - ./utils:/app/utils
      - ./config:/app/config
      - backend_data:/app/data
    environment:
      - APP_ENVIRONMENT=${APP_ENVIRONMENT:-development}
      - DATABASE_URL=postgresql://${DB_USER:-admin}:${DB_PASSWORD}@db:5432/${DB_NAME:-shopify_platform}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY:-QJhl0AKnrMX7UpYIreTUkFmNceOCrajUUkUce0XeSr8=}
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    command: >
      celery -A src.celery_app worker
      --loglevel=info
      --concurrency=2
      --hostname=assistant@%h
      -Q assistant.t1,assistant.t2,assistant.t3,assistant.t3.dlq
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - app-network
    logging: *common-logging
```

Alternative (simpler): Add assistant queues to existing celery_worker:
```yaml
    command: >
      celery -A src.celery_app worker
      --loglevel=info
      --concurrency=${CELERY_INTERACTIVE_CONCURRENCY:-2}
      --hostname=interactive@%h
      -Q control,interactive.t1,interactive.t2,interactive.t3,assistant.t1,assistant.t2,assistant.t3,assistant.t3.dlq
```

### Fix 3: INGEST — Shopify product sync is not implemented in ingest pipeline
The `ingest_chunk` function in `orchestrator.py` only marks EXISTING `Product` DB rows as processed. It does NOT fetch products from Shopify. If the user expects "ingest" to PULL product data from their Shopify store, a separate Shopify sync task needs to be implemented that:
1. Calls Shopify Admin API to list products
2. Creates/updates Product rows in the PostgreSQL database
3. Then triggers the ingest pipeline

## Ingest Investigation

### What ingest does vs what user expects:
- `start_ingest` / `ingest_chunk` functions process EXISTING Product rows in DB
- They mark rows as processed and record results — no Shopify API call
- If user's store has never had products imported, the DB has 0 Product rows → ingest processes 0 items → appears broken
- The ACTUAL Shopify product sync (pulling from Shopify API) would need to be implemented separately

### Queue topology confirmation:
- `start_ingest_task` → `control` queue → `celery_worker` ✓
- `ingest_chunk_t1/t2/t3` → `batch.t1/t2/t3` → `celery_scraper` ✓
- `run_tier_runtime` → `assistant.t1/t2/t3` → NO WORKER ✗ (missing celery_assistant service)

### Auth prerequisite for ingest:
The ingest API requires `@login_required`. The user must be authenticated via Flask-Login session cookie before triggering ingest. If the Shopify embedded app is making requests without a valid session, all API calls will fail with 401/403.
