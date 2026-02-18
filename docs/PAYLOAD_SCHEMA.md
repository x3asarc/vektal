# Dry-Run Payload Schema

## Purpose
A single immutable payload generated during dry-run, approved by user, and then used directly for push. This prevents re-runs and minimizes API calls.

## Schema (JSON)
```json
{
  "run_id": "uuid",
  "mode": "web",
  "created_at": "2026-01-30T12:34:56Z",
  "input": {
    "kind": "sku|ean|handle|title|url",
    "value": "string"
  },
  "product": {
    "id": "gid://shopify/Product/...",
    "handle": "current-handle",
    "title": "Current Title",
    "vendor": "Vendor",
    "sku": "SKU",
    "barcode": "EAN",
    "images": [
      { "id": "...", "src": "...", "position": 1 },
      { "id": "...", "src": "...", "position": 2 }
    ]
  },
  "diff": {
    "fields_to_update": { "...": "..." },
    "fields_to_scrape": ["..."],
    "requires_approval": {
      "handle_change": {
        "proposed_handle": "new-handle",
        "approved": false
      },
      "image_replace": {
        "status": "needs_approval|auto|skip",
        "current_image_1": "url",
        "scraped_image_1": "url",
        "approved": false,
        "apply_to_batch": false
      }
    },
    "redirects_to_create": [
      { "from": "/products/old-handle", "to": "/products/new-handle", "approved": false }
    ]
  },
  "scrape": {
    "sources": ["vendor_site", "fallback_v4"],
    "results": {
      "description_html": "<p>...</p>",
      "price": 12.34,
      "tags": ["..."]
    },
    "not_found": false
  },
  "apply_plan": {
    "update_fields": { "...": "..." },
    "update_images": {
      "action": "auto_add|replace|skip",
      "target_position": 1,
      "source_url": "..."
    },
    "update_handle": {
      "enabled": false,
      "new_handle": "..."
    },
    "create_redirects": [
      { "from": "/products/old-handle", "to": "/products/new-handle", "enabled": false }
    ]
  },
  "approve": {
    "finalized": false,
    "approved_by": "user_id_or_email",
    "approved_at": null
  }
}
```

## Rules
- Handle changes are **disabled** unless explicitly approved in app.
- images == 0 ? auto add image #1
- images == 1 ? approval required (app)
- images >= 2 ? approval required (app), replace only image #1
- CLI never applies handle changes or image replacements by default.
- The payload is applied as-is on approval (no re-run).

