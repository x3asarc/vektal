# SVSE Session Summary (GALAXY-SYNC)

Date: 2026-01-31
Project: Shopify Scraping Script / SVSE (Semantic-Visual Sync Engine)

## What We Did
- Implemented **Phase A (Audit)** in `scripts/audit_v3.py`:
  - Shopify REST fetch + auto-download of images (no manual downloads).
  - SHA-256 + pHash + CLIP (open-clip ViT-B-32) embeddings.
  - Agglomerative clustering + label inference (extended label set).
  - HTML audit report + manifest + config scaffold.
  - Persistent cache in `data/svse/<slug>/` (originals never deleted unless explicitly requested).

- Implemented **Phase B (SEO Plan / Dry Run)** in `scripts/seo_plan_v1.py`:
  - Generates per-cluster and per-product naming/alt plan (CSV/JSON).
  - Avoids `unclassified_outlier` by fallback shot type.
  - Enforces **color in alt/filename for primary only** (position 1), non-primary excludes color.
  - Ensures unique alt text by appending handle when duplicates detected.
  - Auto-selects a primary cluster by **highest coverage**, with packshot-score tie-break.
  - Primary rows are created for **all matched products** (adds missing primary where needed).

- Ran audit for SKU `37051` using focus `galaxy flakes`:
  - 12 candidate products matched.
  - 85 images downloaded.
  - Outputs created:
    - `data/svse/galaxy-flakes-15g-juno-rose/reports/audit_report.html`
    - `data/svse/galaxy-flakes-15g-juno-rose/cache/audit_manifest.json`
    - `data/svse/galaxy-flakes-15g-juno-rose/config.yaml`

- Overrode cluster for thumbnail `eac29237a52d853b.jpg`:
  - Cluster **8** label changed to `group_shot` in config.

- Ran Phase B dry-run:
  - `data/svse/galaxy-flakes-15g-juno-rose/reports/seo_plan_clusters.csv`
  - `data/svse/galaxy-flakes-15g-juno-rose/reports/seo_plan_per_product.csv`

## Current Primary Rule
- Primary cluster chosen by **coverage** (highest count of products covered).
- Primary rows include **all products**; missing ones marked as `action=add`.
- Primary alt includes **color**; non-primary alt excludes color.

## Files Added/Updated
- `scripts/audit_v3.py`
- `scripts/seo_plan_v1.py`
- `requirements.txt` (added Pillow, ImageHash, open-clip-torch, torch, numpy, scikit-learn)
- `data/svse/.../config.yaml` (cluster overrides)

---

## Remaining Tasks (Open)
1. **Phase B Review**
   - Confirm which cluster should be primary (currently chosen by coverage).
   - Adjust `config.yaml` labels if any other cluster is misclassified.
   - Re-run Phase B after label overrides if needed.

2. **Phase C (Apply / Sync) – Not Implemented**
   - Build `apply_sync.py` to:
     - Upload canonical images per cluster.
     - Update alt/position/variant_ids (REST).
     - Mark legacy images as deprecated (alt tag update).
     - Write rollback manifest.

3. **Deletion / Cleanup (Optional)**
   - Build `cleanup.py` to delete deprecated images only on explicit confirmation.
   - Keep originals by default; delete only if user opts in.

4. **Variant Binding Rules**
   - Decide how variant_ids map to canonical images for frontend swap behavior.

5. **Primary Shot Type Policy**
   - Decide whether to force a specific shot type as primary (packshot) or keep coverage-based selection.

---

## Notes / Constraints
- No manual downloads required; audit is fully automated and cached.
- Original images must remain cached; deletion only via explicit cleanup step.
- REST updates must use numeric IDs for variants/images.

