"""
Repair Tasks (Phase 20 Bridge).

Executes specialized repair logic originally found in standalone scripts.
"""
from src.celery_app import app
from src.models import db, Job, JobStatus, Product
from src.core.shopify_resolver import ShopifyResolver
import os
import requests
import json

@app.task(name="src.tasks.repair.fix_seo_alt_task")
def fix_seo_alt_task(job_id: int, product_ids: list[int]):
    """
    Refactored logic from scripts/fix_alt_and_seo.py.
    """
    job = Job.query.get(job_id)
    if not job: return
    
    job.status = JobStatus.RUNNING
    db.session.commit()
    
    # In a real run, we'd fetch the store's credentials
    # For now, following the script's pattern with env vars
    shop_domain = os.getenv("SHOP_DOMAIN", "bastelschachtel.myshopify.com")
    access_token = os.getenv("SHOPIFY_ACCESS_TOKEN")
    api_version = os.getenv("API_VERSION", "2026-01")
    
    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json"
    }
    url = f"https://{shop_domain}/admin/api/{api_version}/graphql.json"
    
    success_count = 0
    error_count = 0
    
    for pid in product_ids:
        product = Product.query.get(pid)
        if not product or not product.shopify_product_id:
            continue
            
        # 1. Update SEO
        mutation_seo = """
        mutation productUpdate($input: ProductInput!) {
          productUpdate(input: $input) {
            product { id seo { title description } }
          }
        }
        """
        variables_seo = {
            "input": {
                "id": f"gid://shopify/Product/{product.shopify_product_id}",
                "seo": {
                    "title": (product.title or "")[:70],
                    "description": (product.description or "")[:160].replace('<p>', '').replace('</p>', '').strip()
                }
            }
        }
        try:
            requests.post(url, json={"query": mutation_seo, "variables": variables_seo}, headers=headers)
            success_count += 1
        except Exception:
            error_count += 1
            
    job.status = JobStatus.COMPLETED
    job.processed_count = success_count + error_count
    job.successful_items = success_count
    job.failed_items = error_count
    db.session.commit()
    
    return {"status": "done", "success": success_count, "errors": error_count}
