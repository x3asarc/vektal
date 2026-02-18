# Next Phase: Final Pre-Implementation Document

## Scope (No Code Changes Yet)
This document consolidates all required decisions, constraints, schemas, and mappings that must be agreed before implementation begins.

---

## 1) Locked Requirements
- Any identifier input (SKU / EAN / handle / title / URL).
- Resolve -> diff -> scrape -> amend -> push.
- Keep v4 fallback system (`scripts/not_found_finder_v4_optimized.py` + `not_found.csv`).
- Image rules:
  - images == 0 -> auto scrape + add image #1.
  - images == 1 -> app approval + preview; “apply to batch” unchecked by default.
  - images >= 2 -> app approval + preview; replace only image #1.
- Handle changes only when explicitly selected in app; never in CLI.
- CLI: no image previews; no approval prompts by default.
- Minimize API calls to reduce billing.
- Dry-run payload is approved and then pushed without re-run.
- App UI will use boilerplate (v0 templates or 21st.dev).

---

## 2) UX & Approval Rules (App Only)## 2) UX & Approval Rules (App Only)
- NOTE (User): CURRENT ALLLLL ONLY SHOWS THE FIRST IMAGE BEING LARGER AND THE FOLLOWING 4 BEING SMALLER FOR UI/UX

- Show current image #1 and scraped candidate side-by-side.
- Visual shorthand for batch view (example for 5 images):
  - Current: `Lllll`
  - Scraped: `Bbbbb`
  - UI note: first image is larger; following images are smaller
- Handle change requires explicit checkbox in app (unchecked by default).
- “Apply to batch” checkbox exists for image decisions (unchecked by default).

---

## 3) SKU/EAN Ambiguity Resolution## 3) SKU/EAN Ambiguity Resolution
- NOTE (User): IF BOTH RETURN DIFFERENT PRODUCT THEN A LOOKUP ON THE VENDORS SITE SHOULD OCCUR USING THE CURRENT SCRIPTS CAPABILITIES

- If input is SKU or EAN:
  1) try SKU lookup
  2) if not found, try barcode lookup
  3) if both return different products -> app shows both for selection
  4) if same product -> proceed with one result
  5) if both return different products -> also trigger vendor-site lookup using existing scripts
- Cache resolver results per run to minimize calls.

---

## 4) Dry-Run Payload (Approved = Pushed)## 4) Dry-Run Payload (Approved = Pushed)
- NOTE (User): THE LIVE PUSH SHOULD ALWAYS BE REVERSIBLE INCASE OF FAULTY PUSH

- Use `docs/PAYLOAD_SCHEMA.md` as canonical payload spec.
- Dry-run builds payload, app approval mutates only approval flags, push uses payload as-is.
- No re-run after approval.
- Live push must be reversible in case of faulty push.

---

## 5) API Call Minimization (Best Practice)## 5) API Call Minimization (Best Practice)
- NOTE (User): I HAVE OFTEN HAD TO USE SHOPIFY'S REST API INSTEAD OF ITS GRAPHQL TO FIND RESULTS. KEEP THAT IN MIND

- Cache Shopify reads within a run.
- Batch GraphQL queries in CSV mode where possible.
- Allow REST API fallback where GraphQL does not return results.
- Avoid post-write verification calls unless requested.
- Reuse Shopify responses for diff and apply decisions.

---

## 6) New Modules + Responsibilities (Implementation Targets)
- `cli/main.py`: single recommended entry point, CLI orchestration.
- `src/core/pipeline.py`: resolve -> diff -> scrape -> apply.
- `src/core/shopify_resolver.py`: canonical Shopify lookup API.
- `src/core/diff_engine.py`: diff + decision rules.
- `src/core/scrape_engine.py`: wraps existing scrapers + v4 fallback.
- `src/core/shopify_apply.py`: applies payload without re-run.

---

## 7) Final Implementation Mapping (Existing Code Reuse)
- Shopify client: base on `src/core/image_scraper.py:ShopifyClient`.
- Resolver queries: reuse from `seo/seo_generator.py:ProductFetcher` and CLI scripts.
- Update mutations: reuse from `seo/seo_generator.py:ProductUpdater`.
- Redirect helper: `utils/create_shopify_redirect.py`.
- Scraper logic: `src/core/image_scraper.py` + v4 fallback script.

---

## 8) CLI vs App Behavior## 8) CLI vs App Behavior
- NOTE (User): IT DEPENDS ON WHAT NEEDS APPROVING. CONSULT ME HERE
- NOTE (User): HANDLES CAN BE CHANGED HERE TOO, BUT NEEDS TO BE APPROVED FIRST, JUST LIKE IMAGE CHANGE APPROVAL. IF MORE THAN 1 IMAGE IS BEING REPLACED THEN THE USER MUST APPROVE IT.

- CLI:
  - No image previews.
  - No approval prompts by default.
  - Handle changes can be approved in CLI if explicitly prompted.
  - Image changes require approval if more than 1 image would be replaced.
- App:
  - Full dry-run preview.
  - Approval required for image changes and handle changes.
  - Approved payload becomes push without re-run.

---

## 9) QA Checklist
- See `docs/QA_CHECKLIST.md` for the checklist that must pass before rollout.

---

## 10) Deployment Plan (Later)
- `src/app.py` -> GitHub -> Cloud -> Shopify.
- Add PostgreSQL, multi-user support, billing, and auth.
- Use boilerplate UI/UX template (v0 templates or 21st.dev).

---

## Confirmations Needed Before Implementation
- Confirm which boilerplate template to use (v0 or 21st.dev).
- Confirm CLI output format (table vs JSON vs summary text).
- Confirm whether CSV batch should prompt for image approvals in app only (current plan: yes).


