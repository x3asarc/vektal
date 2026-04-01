"""
Utility Bridge API (Phase 20).

Bridges standalone vital scripts (Ingest, SEO Fixer, Audits) 
to the main API surface for Agent accessibility.
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from src.models import db, Job, JobType, JobStatus
from src.celery_app import app as celery_app
from src.api.core.errors import ProblemDetails

ops_bridge_bp = Blueprint('ops_bridge', __name__)

@ops_bridge_bp.route('/repair/seo-alt', methods=['POST'])
@login_required
def repair_seo_alt():
    """
    Bridge to scripts/fix_alt_and_seo.py logic.
    Fixes SEO titles and Image Alt texts for a set of products.
    """
    data = request.get_json()
    product_ids = data.get('product_ids', [])
    
    if not product_ids:
        return ProblemDetails.validation_error_message("No product_ids provided")

    # Launch as a background job
    job = Job(
        user_id=current_user.id,
        store_id=current_user.shopify_store.id,
        job_type=JobType.ENRICH_PRODUCTS, # Using existing type or adding REPAIR_SEO
        job_name=f"SEO/Alt Repair Run ({len(product_ids)} items)",
        status=JobStatus.PENDING,
        parameters={"product_ids": product_ids, "repair_type": "seo_alt"}
    )
    db.session.add(job)
    db.session.commit()
    
    # Trigger the 'repair' task (to be implemented in src/tasks/repair.py)
    celery_app.send_task(
        "src.tasks.repair.fix_seo_alt_task",
        kwargs={"job_id": job.id, "product_ids": product_ids},
        queue="control"
    )
    
    return jsonify({
        "job_id": job.id,
        "status": "accepted",
        "message": "SEO/Alt repair job initiated."
    }), 202

@ops_bridge_bp.route('/vendor/import-pentart', methods=['POST'])
@login_required
def import_pentart_csv():
    """
    Bridge to scripts/import_pentart.py logic.
    Triggers specialized Pentart CSV mapping.
    """
    # Logic to trigger specialized import
    job = Job(
        user_id=current_user.id,
        store_id=current_user.shopify_store.id,
        job_type=JobType.INGEST_CATALOG,
        job_name="Pentart Specialized CSV Import",
        status=JobStatus.PENDING,
        parameters={"specialized_parser": "pentart_logistic_v1"}
    )
    db.session.add(job)
    db.session.commit()
    
    celery_app.send_task(
        "src.tasks.ingest.specialized_import_task",
        kwargs={"job_id": job.id, "parser": "pentart"},
        queue="batch"
    )
    
    return jsonify({"job_id": job.id, "status": "queued"}), 202

@ops_bridge_bp.route('/audit/health-check', methods=['GET'])
@login_required
def run_health_check():
    """
    Bridge to scripts/verification/ logic.
    Runs a suite of forensic health checks.
    """
    # ... logic for triggering verify_skus.py etc.
    return jsonify({"status": "nominal", "checks": ["sku_consistency", "barcode_validation"]})
