"""
System prompt generator for 'Forensic' agent awareness.
Provides the agent with its current identity, store context, 
and active catalog health.
"""
from datetime import datetime, timezone
from typing import Any
from src.models import db
from src.models.shopify import ShopifyStore
from src.models.job import Job, JobStatus
from src.core.tenancy.context import get_current_store_id

def generate_forensic_system_prompt() -> str:
    """
    Generate a dynamic system prompt for the AI Agent.
    
    Includes:
    - Current datetime (UTC)
    - Store Domain & Status
    - Active Job Summary (last 5 running/failed)
    - Project Knowledge Base Reference
    """
    store_id = get_current_store_id()
    if not store_id:
        return "System Warning: No active store connection detected. You are in read-only diagnostic mode."

    # 1. Fetch Store Details
    store = ShopifyStore.query.get(store_id)
    if not store:
        return "System Warning: Store record missing from current context."

    # 2. Fetch Active/Recent Jobs
    recent_jobs = Job.query.filter_by(store_id=store_id)\
        .order_by(Job.created_at.desc())\
        .limit(5).all()

    job_status_summary = ""
    for job in recent_jobs:
        job_status_summary += f"- Job {job.id} ({job.job_type}): {job.status} - {job.percent_complete}% complete\n"

    now = datetime.now(timezone.utc).isoformat()
    
    prompt = f"""
You are the Shopify Forensic Agent for {store.shop_domain}.
Current Time: {now}

STORE CONTEXT:
- Domain: {store.shop_domain}
- Name: {store.shop_name}
- Status: {"Active" if store.is_active else "Inactive"}
- Last Full Ingest: {store.last_full_ingest_at if store.last_full_ingest_at else "Never"}

ACTIVE SYSTEM STATE:
{job_status_summary if job_status_summary else "No recent background activity detected."}

YOUR CAPABILITIES:
You have high-precision access to the store's private catalog schema. 
You can search products, enrichment data, and dry-run batches. 
You are blind to all other users' data.

GOVERNANCE:
1. All SKU modifications MUST go through a Dry Run first.
2. Bulk actions require explicit user approval (approved_at) before they can be applied.
3. You are an expert in 'Forensic' attribute enrichment (German/English).

Use your tools to diagnose, enrich, and optimize the catalog.
"""
    return prompt.strip()
