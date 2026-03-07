"""
Shopify Webhook Receiver (Phase 17.3).

Handles products/create, products/update, and products/delete topics.
Ensures signature verification and idempotent processing.
"""
import hmac
import hashlib
import base64
import json
from flask import Blueprint, request, jsonify, current_app
from src.models import db, ShopifyStore, ShopifyCredential, Product, ProductChangeEvent
from src.models.job import JobType
from datetime import datetime, timezone

shopify_webhooks_bp = Blueprint('shopify_webhooks', __name__)

def verify_shopify_webhook(data, hmac_header, secret):
    """Verify that the webhook request came from Shopify."""
    digest = hmac.new(secret.encode('utf-8'), data, hashlib.sha256).digest()
    computed_hmac = base64.b64encode(digest)
    return hmac.compare_digest(computed_hmac, hmac_header.encode('utf-8'))

@shopify_webhooks_bp.route('/webhooks/products', methods=['POST'])
def handle_product_webhook():
    """Unified receiver for products/* webhooks."""
    data = request.get_data()
    hmac_header = request.headers.get('X-Shopify-Hmac-Sha256')
    topic = request.headers.get('X-Shopify-Topic')
    shop_domain = request.headers.get('X-Shopify-Shop-Domain')
    webhook_id = request.headers.get('X-Shopify-Webhook-Id')

    if not hmac_header or not shop_domain:
        return jsonify({"error": "Missing headers"}), 401

    # 1. Lookup store and webhook secret
    store = ShopifyStore.query.filter_by(shop_domain=shop_domain).first()
    if not store:
        return jsonify({"error": "Store not found"}), 404

    # We expect the webhook secret to be stored in ShopifyCredential
    credential = ShopifyCredential.query.filter_by(
        store_id=store.id, 
        credential_type='webhook_secret'
    ).first()
    
    # Fallback to env secret if not in DB for early dev/testing
    secret = credential.get_credential() if credential else current_app.config.get('SHOPIFY_API_SECRET')
    
    if not secret:
        return jsonify({"error": "Webhook secret not configured"}), 500

    # 2. Verify signature
    if not verify_shopify_webhook(data, hmac_header, secret):
        return jsonify({"error": "Invalid signature"}), 401

    # 3. Idempotency Check (Check if this webhook_id was already processed)
    # For Phase 17.3 we use ProductChangeEvent metadata to track webhook_id
    existing_event = ProductChangeEvent.query.filter(
        ProductChangeEvent.metadata_json['webhook_id'].astext == webhook_id
    ).first()
    if existing_event:
        return jsonify({"status": "already-processed"}), 200

    # 4. Process payload (Async recommended for production, sync for now)
    payload = json.loads(data)
    
    # 5. Picoclaw: Observe for 'Alien DNA' (Phase 18.1)
    try:
        from src.core.evolution.observer import SchemaObserver
        observer = SchemaObserver()
        anomalies = observer.detect_anomalies(payload)
        for anomaly in anomalies:
            # For now, we just log. Nanoclaw will later consume these as events.
            print(f"NANOCLAW: Alien DNA detected in {topic}! Field: {anomaly.field_name}, Type: {anomaly.inferred_type}")
    except Exception as e:
        print(f"NANOCLAW ERROR: Observer failed: {e}")

    try:
        from src.tasks.shopify_sync import process_webhook_task
        process_webhook_task.delay(
            store_id=store.id, 
            topic=topic, 
            payload=payload, 
            webhook_id=webhook_id
        )
    except Exception as e:
        # Fallback to sync if celery is down or not configured
        print(f"Webhook task error: {e}")
        return jsonify({"error": "Internal processing error"}), 500

    return jsonify({"status": "queued", "webhook_id": webhook_id}), 200
