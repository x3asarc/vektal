"""
Ops Dashboard API (Phase 17.4).

Surfaces catalog-wide completeness metrics and activity summaries.
"""
from flask import Blueprint, jsonify
from flask_login import current_user, login_required
from sqlalchemy import func
from src.models import db, Product, ShopifyStore
from src.api.core.errors import ProblemDetails

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/summary', methods=['GET'])
@login_required
def get_dashboard_summary():
    """Return catalog health and ingest watermarks."""
    store = ShopifyStore.query.filter_by(user_id=current_user.id, is_active=True).first()
    if not store:
        return ProblemDetails.business_error(
            "store-not-connected", "Store Not Connected",
            "Connect a Shopify store to view dashboard metrics.", 409
        )

    # 1. Aggregate basic product counts
    total_skus = Product.query.filter_by(store_id=store.id).count()
    
    if total_skus == 0:
        return jsonify({
            "total_skus": 0,
            "avg_completeness": 0,
            "healthy_skus": 0,
            "last_ingest_at": store.last_full_ingest_at.isoformat() if store.last_full_ingest_at else None,
            "coverage_matrix": {}
        }), 200

    # 2. Average completeness
    avg_completeness = db.session.query(
        func.avg(Product.completeness_score)
    ).filter(Product.store_id == store.id).scalar()

    # 3. Healthy SKUs (Score > 90%)
    healthy_skus = Product.query.filter(
        Product.store_id == store.id,
        Product.completeness_score >= 90
    ).count()

    # 4. Field-level coverage (Sampling for Phase 17.4)
    # In a production environment with millions of SKUs, we'd use a materialized view.
    # For 4,000 SKUs, these counts are fast.
    field_coverage = {
        "title": Product.query.filter(Product.store_id == store.id, Product.title != None).count(),
        "description": Product.query.filter(Product.store_id == store.id, Product.description != None).count(),
        "sku": Product.query.filter(Product.store_id == store.id, Product.sku != None).count(),
        "price": Product.query.filter(Product.store_id == store.id, Product.price != None).count(),
    }

    return jsonify({
        "total_skus": total_skus,
        "avg_completeness": float(avg_completeness or 0),
        "healthy_skus": healthy_skus,
        "unhealthy_skus": total_skus - healthy_skus,
        "last_ingest_at": store.last_full_ingest_at.isoformat() if store.last_full_ingest_at else None,
        "field_coverage": field_coverage,
        "store_domain": store.shop_domain
    }), 200
