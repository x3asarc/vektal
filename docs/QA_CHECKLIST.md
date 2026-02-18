# QA Checklist (Unified Pipeline)

## Resolver & Identity
- [ ] SKU/EAN ambiguity resolved safely (no wrong product updates)
- [ ] Handle/URL/SKU/EAN/Title all resolve to a product or cleanly fail
- [ ] Title search shows candidates when multiple matches exist

## Diff + Decision
- [ ] Only missing/incorrect fields are marked for update
- [ ] No unintended overwrites of existing Shopify data
- [ ] Handle changes are disabled by default and require explicit app approval

## Image Policy
- [ ] images == 0 ? auto scrape + add image #1
- [ ] images == 1 ? app approval + preview; “apply to batch” unchecked
- [ ] images >= 2 ? app approval + preview; replace only image #1
- [ ] CLI mode never shows images or prompts by default

## Redirects
- [ ] Handle change always creates redirect
- [ ] Redirects are previewed in app before approval

## Scrape + Fallback
- [ ] Scrape only missing/incorrect fields
- [ ] v4 fallback flow is preserved (`not_found.csv` remains)

## API Call Minimization
- [ ] Resolver uses cached Shopify reads within a run
- [ ] Batch queries used for CSV mode when possible
- [ ] No post-write verification calls unless explicitly requested

## Dry-Run ? Push
- [ ] Dry-run payload is the single source of truth for push
- [ ] No re-run after approval; approved payload is applied directly

## Logging / Audit
- [ ] Each product has a clear audit trail: input ? resolve ? diff ? scrape ? apply
- [ ] Errors are explicit and actionable

