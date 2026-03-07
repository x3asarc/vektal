"""
Shopify Sync Tasks (Phase 17.3).

Processes webhook events and reconciliation polling for Shopify products.
Ensures non-destructive updates with full event lineage.
"""
from datetime import datetime, timezone
from src.celery_app import app
from src.models import db, Product, ProductChangeEvent, ShopifyStore
from src.core.products.completeness import calculate_completeness
import hashlib
import json

def _now() -> datetime:
    return datetime.now(timezone.utc)

def compute_payload_hash(payload: dict) -> str:
    """Stable hash of a JSON-serializable dict."""
    encoded = json.dumps(payload, sort_keys=True).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()

def dict_diff(before: dict, after: dict) -> dict:
    """Simple shallow dict diff for change logging."""
    diff = {}
    for k, v in after.items():
        if before.get(k) != v:
            diff[k] = {"before": before.get(k), "after": v}
    return diff

@app.task(name="src.tasks.shopify_sync.process_webhook_task")
def process_webhook_task(store_id: int, topic: str, payload: dict, webhook_id: str):
    """
    Idempotently process a Shopify product webhook event.
    """
    store = ShopifyStore.query.get(store_id)
    if not store:
        return {"error": "Store not found"}

    shopify_product_id = payload.get('id')
    if not shopify_product_id:
        return {"error": "No shopify_product_id in payload"}

    # Use the first variant for consistency with Phase 8 product model
    variants = payload.get('variants', [])
    variant = variants[0] if variants else {}
    shopify_variant_id = variant.get('id')

    # 1. Topic: products/delete
    if topic == 'products/delete':
        product = Product.query.filter_by(
            store_id=store_id, 
            shopify_product_id=shopify_product_id
        ).first()
        if product:
            product.is_active = False
            product.sync_status = 'deleted'
            db.session.commit()
            return {"status": "marked_inactive", "product_id": product.id}
        return {"status": "already_missing"}

    # 2. Topic: products/create or products/update
    product = Product.query.filter_by(
        store_id=store_id, 
        shopify_product_id=shopify_product_id
    ).first()

    # Capture state for diff
    before_payload = None
    if product:
        # Simple extraction of core fields from model for comparison
        before_payload = {
            "title": product.title,
            "description": product.description,
            "price": str(product.price) if product.price else None,
            "sku": product.sku,
            "tags": product.tags
        }

    # Map Shopify fields to our Product model
    new_data = {
        "title": payload.get('title'),
        "description": payload.get('body_html'),
        "product_type": payload.get('product_type'),
        "tags": [t.strip() for t in payload.get('tags', '').split(',')] if payload.get('tags') else [],
        "price": variant.get('price'),
        "sku": variant.get('sku'),
        "barcode": variant.get('barcode'),
        "compare_at_price": variant.get('compare_at_price'),
        "cost": variant.get('inventory_item', {}).get('cost'), # If available
        "weight_kg": variant.get('weight'),
        "weight_unit": variant.get('weight_unit'),
        "last_synced_at": _now(),
        "sync_status": 'synced'
    }

    if not product:
        product = Product(
            store_id=store_id,
            shopify_product_id=shopify_product_id,
            shopify_variant_id=shopify_variant_id,
            **new_data
        )
        db.session.add(product)
        db.session.flush() # Get product.id
    else:
        for key, value in new_data.items():
            setattr(product, key, value)

    # Recompute completeness
    product.completeness_score = calculate_completeness(product)["completeness_score"]

    # Record Change Event
    after_payload = {
        "title": product.title,
        "description": product.description,
        "price": str(product.price) if product.price else None,
        "sku": product.sku,
        "tags": product.tags
    }
    
    event = ProductChangeEvent(
        product_id=product.id,
        store_id=store_id,
        source='import',
        event_type='manual_edit' if topic == 'products/update' else 'bulk_stage',
        before_payload=before_payload,
        after_payload=after_payload,
        diff_payload=dict_diff(before_payload or {}, after_payload),
        metadata_json={
            "webhook_id": webhook_id,
            "topic": topic,
            "shopify_version_hash": compute_payload_hash(payload),
            "shopify_updated_at": payload.get('updated_at')
        },
        note=f"Shopify webhook sync: {topic}"
    )
    db.session.add(event)

    # Update store cursor for reconciliation safety
    if payload.get('updated_at'):
        store.last_shopify_cursor = payload.get('updated_at')

    db.session.commit()
    return {"status": "synced", "product_id": product.id}

@app.task(name="src.tasks.shopify_sync.reconcile_shopify_catalog")
def reconcile_shopify_catalog(store_id: int):
    """
    Reconciliation poller: Fetch products updated since last_shopify_cursor
    and process them as synthetic 'products/update' events.
    """
    from src.core.shopify_resolver import ShopifyResolver
    
    store = ShopifyStore.query.get(store_id)
    if not store:
        return {"error": "Store not found"}

    # Use the cursor (updated_at timestamp)
    # Default to 24h ago if no cursor exists
    since_at = store.last_shopify_cursor or (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    
    resolver = ShopifyResolver(
        shop_domain=store.shop_domain,
        access_token=store.get_access_token()
    )
    
    updated_nodes = resolver.fetch_updated_products(since_at=since_at, limit=100)
    
    synced_count = 0
    for node in updated_nodes:
        # Re-map resolver node back to the shape process_webhook_task expects
        # or call a shared mapper. For Phase 17, we'll map manually for speed.
        synthetic_payload = {
            "id": int(node['id'].split('/')[-1]),
            "title": node['title'],
            "body_html": node['description_html'],
            "product_type": node['product_type'],
            "tags": ",".join(node['tags']),
            "updated_at": _now().isoformat(), # We don't have the exact updated_at from resolver yet, but it's > since_at
            "variants": [
                {
                    "id": int(v['id'].split('/')[-1]),
                    "sku": v['sku'],
                    "barcode": v['barcode'],
                    "price": v['price'],
                    "compare_at_price": None, # Resolver might not have this
                    "weight": v.get('weight'),
                    "weight_unit": v.get('weight_unit')
                } for v in node['variants']
            ]
        }
        
        process_webhook_task(
            store_id=store.id,
            topic='products/update',
            payload=synthetic_payload,
            webhook_id=f"reconcile-{_now().timestamp()}-{synced_count}"
        )
        synced_count += 1
        
    return {"synced_count": synced_count, "since_at": since_at}
