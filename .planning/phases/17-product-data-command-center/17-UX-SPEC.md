# Phase 17 UX Specification

Title: Product Data Command Center (Dashboard-Home + Chat Core)
Date: 2026-03-05
Status: Planning only (no implementation in this document)

## 1) Purpose

Design the product-facing experience so the dashboard is the operational home, with chat as the primary control surface.

Primary user outcome:
- User connects Shopify once.
- Platform ingests product data immediately.
- Dashboard shows real product-data health/completeness.
- User can start any action from dashboard or chat.
- Historical states are preserved so rollback is possible.

Scope constraint for Phase 17:
- Product data only (no orders/customers/fulfillment domains).

## 2) Existing UI DNA (must be preserved)

Active implementation signals:
- Token handshake in [frontend/src/app/design-tokens.css](../../../frontend/src/app/design-tokens.css) references `images/design-tokens-v2.json`.
- Current shell/layout is in [frontend/src/shell/components/AppShell.tsx](../../../frontend/src/shell/components/AppShell.tsx) and [frontend/src/shell/components/Sidebar.tsx](../../../frontend/src/shell/components/Sidebar.tsx).
- Current dashboard and chat surfaces exist in:
  - [frontend/src/app/(app)/dashboard/page.tsx](../../../frontend/src/app/(app)/dashboard/page.tsx)
  - [frontend/src/features/chat/components/ChatWorkspace.tsx](../../../frontend/src/features/chat/components/ChatWorkspace.tsx)

Visual constraints to keep:
- Dark, dense, forensic style.
- Mono-first typography.
- 1px borders, zero-radius components.
- High information density without visual clutter.
- Sidebar-based app shell with chat always top-tier navigation.

## 3) Information architecture (Phase 17 target)

Global rule:
- Dashboard is home.
- Chat is primary action interface.
- Other pages remain specialized workspaces.

Primary nav (unchanged path model):

```text
/dashboard   -> Command center (home)
/chat        -> Conversational operations (core)
/search      -> Precision product lookup / staged actions
/enrichment  -> Dry-run/approve/apply enrichment lifecycle
/jobs        -> Long-running execution visibility
/onboarding  -> Connection + ingest bootstrap
/settings    -> Policy + strategy controls
```

Dashboard entry behavior:
- After successful auth/store connection, default route is `/dashboard`.
- Dashboard must include visible quick-jump into `/chat` and prefilled command intents.

## 4) Dashboard UX architecture

### 4.1 Block hierarchy

```text
+---------------------------------------------------------------+
| [A] Header: Store identity + sync state + emergency controls  |
+------------------------------+--------------------------------+
| [B] Data Health Scorecard    | [C] Chat Command Dock          |
| - completeness %             | - primary input                |
| - missing-critical %         | - suggested commands           |
| - trend delta                | - unresolved clarifier prompts |
+------------------------------+--------------------------------+
| [D] Field Coverage Matrix (visual)                            |
| - per-field fill-rate bars / heatmap                          |
+---------------------------------------------------------------+
| [E] Product Quality Distribution (visual)                      |
| - histogram by completeness buckets                            |
+---------------------------------------------------------------+
| [F] Change Activity + Version Timeline                         |
| - recent Shopify-origin changes                                |
| - recent platform-origin writes                                |
| - rollback entry points                                        |
+---------------------------------------------------------------+
| [G] Action Launchpad                                           |
| - Search sweep / Enrichment / Bulk update / Version restore   |
+---------------------------------------------------------------+
```

### 4.2 Desktop wireframe (ASCII)

```text
+====================================================================================================+
| ORBITAL FORENSICS CONSOLE                                            STORE: bastelschachtel.at      |
| Last ingest: 10:42:11   Listener: LIVE   Drift: 0.4%   API: 4/4   [Force Reconcile] [Open Chat]   |
+====================================================================================================+
| DATA HEALTH                                                                 | CHAT COMMAND DOCK        |
| ----------------------------------------                                    | ------------------------ |
| Catalog completeness: 84.2%   (+1.8/24h)                                   | [ Ask the system...    ] |
| Products missing >=1 critical: 27.6%                                        | [Send] [Bulk] [Attach]   |
| Critical field fill-rate: 91.0%                                             | Suggested:               |
| Metafield coverage: 63.4%                                                   | - Update newest 5 prices |
| SEO readiness: 58.9%                                                        | - Fill missing meta desc |
|                                                                              | Pending clarifications:  |
|                                                                              | - "Which price source?" |
+--------------------------------------------------------------------------------+-------------------------+
| FIELD COVERAGE MATRIX (critical + extended product fields)                                           |
| ---------------------------------------------------------------------------------------------------- |
| title              [####################] 100% | description      [##########----------] 51%         |
| tags               [##############------] 73%  | collections      [########------------] 41%         |
| product_type       [################----] 82%  | weight           [###########---------] 56%         |
| price              [##################--] 92%  | compare_at_price [#####---------------] 28%         |
| cost               [########------------] 44%  | price_per_unit   [####----------------] 22%         |
| seo_title          [######--------------] 33%  | seo_description  [#######-------------] 37%         |
| hs_code            [##########----------] 50%  | country_origin   [###########---------] 57%         |
| metafields         [######--------------] 34%  | colors           [########------------] 43%         |
+------------------------------------------------------------------------------------------------------+
| PRODUCT QUALITY DISTRIBUTION                 | CHANGE ACTIVITY / VERSIONS                            |
| 0-40%  ||||||                               | 10:41 Shopify edit: SKU-12033 title changed          |
| 41-60% ||||||||||||                         | 10:35 Platform apply: Enrichment run #882            |
| 61-80% ||||||||||||||||||                   | 10:22 Shopify edit: SKU-09002 price changed          |
| 81-100%|||||||||||||||                      | [Open Timeline] [Rollback Candidate List]            |
+------------------------------------------------------------------------------------------------------+
| LAUNCHPAD: [Run Search Sweep] [Start Enrichment Dry-run] [Bulk Fix Missing Fields] [Open Jobs]      |
+======================================================================================================+
```

### 4.3 Mobile wireframe (ASCII)

```text
+--------------------------------------+
| Console | Listener LIVE | Open Chat  |
+--------------------------------------+
| Completeness 84.2%  (+1.8/24h)       |
| Missing critical 27.6%               |
| SEO readiness 58.9%                  |
+--------------------------------------+
| Chat Dock                            |
| [ Ask for product operation... ]     |
| [Send] [Bulk]                        |
+--------------------------------------+
| Field Coverage                       |
| title         100%                   |
| description    51%                   |
| collections    41%                   |
| ...                                 |
| [Expand full matrix]                 |
+--------------------------------------+
| Distribution + Activity              |
| [Mini chart]                         |
| [Latest changes list]                |
+--------------------------------------+
| Launchpad                            |
| [Search] [Enrichment] [Jobs]         |
+--------------------------------------+
```

## 5) Metric definitions shown to user

### 5.1 Core percentages

1. Catalog Completeness %
- Definition: average per-product completion across selected tracked fields.

2. Missing Critical %
- Definition: `% of products missing >=1 critical field`.
- Critical defaults: title, description, price, vendor, product_type, primary image, status.

3. Field Fill Rate %
- Definition per field: `filled_count / total_products`.

4. SEO Readiness %
- Definition: `% of products meeting minimum SEO field set` (seo_title + seo_description + alt text + indexable status).

### 5.2 Data visualizations (required)

1. Field coverage matrix
- Horizontal bars (or heatmap rows) per field.
- Sorted by worst fill-rate first by default.

2. Product completeness distribution
- Bucketed histogram: `0-20`, `21-40`, `41-60`, `61-80`, `81-100`.

3. Trend deltas
- 24h and 7d small sparklines for:
  - completeness
  - missing critical
  - ingest freshness

4. Activity timeline
- Event stream with source badges:
  - `Shopify`
  - `Platform`
  - `Chat`
  - `Automation`

## 6) Chat as primary product surface

### 6.1 UX behavior contract

1. Chat entrypoint is always visible on dashboard.
2. Dashboard quick actions can prefill chat commands.
3. If intent is ambiguous, assistant asks clarifying questions until executable.
4. Clarifier state is surfaced in dashboard as unresolved prompts.
5. Mutating actions preserve existing governance: dry-run -> approve -> apply.

### 6.2 Clarifier loop UX

```text
USER: "Update my 5 newest products with this price"
BOT:  "Which source should be authoritative: Shopify current, supplier CSV, or manual value?"
USER: "manual 12.99"
BOT:  "Understood. Should this apply to compare-at price too?"
USER: "no"
BOT:  "Prepared dry-run for 5 products. Review now? [Open Review]"
```

### 6.3 Dashboard + chat coupling

- Dashboard block `Pending Clarifications` opens chat at exact thread context.
- Dashboard block `Launchpad` can create chat starter prompts:
  - "Show products missing description and propose fixes"
  - "Update newest N products price to X"
  - "Generate SEO metadata for products missing meta description"

## 7) Version history and rollback UX

User-visible rules:
1. No silent overwrite of historical state.
2. Every product change generates/attaches a recoverable historical state.
3. Rollback entry is available from timeline and product detail.

Rollback interaction (dashboard):

```text
[Change Activity Row] -> [Inspect Diff] -> [Create Rollback Dry-run] -> [Approve] -> [Apply Rollback]
```

## 8) UX states and empty/error behavior

### 8.1 Required states per block

- Loading: skeletons + last known snapshot stamp.
- Empty: explicit message + primary next action.
- Error: actionable retry + diagnostic id.
- Stale: warning badge if listener lag exceeds threshold.

### 8.2 Error language standard

- Never raw stack traces in UI.
- Format:
  - short title
  - plain-language impact
  - immediate recovery action
  - diagnostic id

## 9) Accessibility and interaction rules

1. Keyboard-first interaction for dashboard blocks and chat dock.
2. Focus-visible rings use token focus color.
3. All graph colors remain WCAG-compliant against dark surface.
4. Reduced-motion mode disables non-essential transitions.

## 10) Non-goals in this UX spec

- No customer/order/fulfillment dashboards.
- No multi-store cross-tenant analytics.
- No redesign to light theme.

## 11) Existing files this spec is anchored to

Design and shell:
- [frontend/src/app/design-tokens.css](../../../frontend/src/app/design-tokens.css)
- [frontend/src/app/globals.css](../../../frontend/src/app/globals.css)
- [frontend/src/shell/components/AppShell.tsx](../../../frontend/src/shell/components/AppShell.tsx)
- [frontend/src/shell/components/Sidebar.tsx](../../../frontend/src/shell/components/Sidebar.tsx)

Current dashboard/chat:
- [frontend/src/app/(app)/dashboard/page.tsx](../../../frontend/src/app/(app)/dashboard/page.tsx)
- [frontend/src/app/(app)/chat/page.tsx](../../../frontend/src/app/(app)/chat/page.tsx)
- [frontend/src/features/chat/components/ChatWorkspace.tsx](../../../frontend/src/features/chat/components/ChatWorkspace.tsx)
- [frontend/src/features/chat/hooks/useChatSession.ts](../../../frontend/src/features/chat/hooks/useChatSession.ts)

Quality/evolution inputs:
- [.planning/page-audit/run-20260305-203815/structured_page_state.json](../../page-audit/run-20260305-203815/structured_page_state.json)
- [.planning/page-audit/run-20260305-203815/recommendations.json](../../page-audit/run-20260305-203815/recommendations.json)
- [.planning/page-audit/run-20260305-203815/verification_report.md](../../page-audit/run-20260305-203815/verification_report.md)

See graph-backed linkage details in [17-GRAPH-LINKS.md](./17-GRAPH-LINKS.md).
