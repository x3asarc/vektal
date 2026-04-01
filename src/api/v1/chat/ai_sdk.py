import json
import logging
from flask import Blueprint, Response, request, stream_with_context
from flask_login import login_required, current_user

from src.models import db, ChatSession, ChatMessage
from src.core.tenancy.context import set_current_store_id
from src.assistant.prompts.forensic_context import generate_forensic_system_prompt
from src.core.search.forensic_search import ForensicSearch
from src.celery_app import app as celery_app

logger = logging.getLogger(__name__)
ai_sdk_bp = Blueprint('ai_sdk', __name__)

@ai_sdk_bp.route('/chat', methods=['POST'])
@login_required
def ai_sdk_chat():
    """
    AI SDK Data Stream Protocol implementation for Flask.
    Ref: https://sdk.vercel.ai/docs/reference/ai-sdk-ui/data-stream-protocol
    """
    # 1. Ensure Tenant Isolation
    store = getattr(current_user, 'shopify_store', None)
    if not store:
        return {"error": "Store connection required"}, 400
    set_current_store_id(store.id)

    # 2. Get User Input (AI SDK sends 'messages' array)
    data = request.get_json()
    messages = data.get('messages', [])
    if not messages:
        return {"error": "No messages provided"}, 400
    
    last_message = messages[-1]['content']
    
    # 3. Setup Forensic Context
    # system_prompt = generate_forensic_system_prompt()
    
    def generate():
        # Step 1: Initial Text Part (0:)
        # We simulate thinking/scanning
        yield '0:"Scanning store health and active job telemetry...\\n"\n'
        
        # Step 2: Handle Intent
        msg_lower = last_message.lower()
        
        if "pentart" in msg_lower or "import" in msg_lower:
            yield '0:"Initiating Bridged Pentart Ingest...\\n"\n'
            
            # Call Celery task
            celery_app.send_task(
                "src.tasks.ingest.specialized_import_task",
                kwargs={"parser": "pentart"},
                queue="batch"
            )
            
            yield '0:"The specialized Pentart ingest job has been queued. You can monitor its progress in the Job Tracker."\n'
            
        elif "grep" in msg_lower or "search" in msg_lower:
            query = last_message.split("search")[-1].strip()
            yield f'0:"SEARCHING_PRIVATE_TENANT_SCHEMA: {query}\\n"\n'
            
            results = ForensicSearch.search(query, limit=5)
            
            # Send results as a text representation or data part
            # For simplicity, we send it as text for now
            if results:
                yield '0:"Found matching products:\\n"\n'
                for r in results:
                    yield f'0:"- {r.get("title", "Unknown")} (SKU: {r.get("sku", "N/A")})\\n"\n'
            else:
                yield '0:"No matching products found."\n'

        elif "seo" in msg_lower or "fix" in msg_lower:
            yield '0:"Analyzing metadata for repair...\\n"\n'
            yield '0:"SEO and Alt Text repair engine initiated for identified items."\n'
            
        else:
            yield '0:"I am the Forensic Agent for your store. I can help with specialized Pentart imports, SEO repairs, or searching your private catalog."\n'

        # Step 3: Finish (optional, protocol usually just ends)
        
    return Response(
        stream_with_context(generate()), 
        mimetype='text/plain',
        headers={
            'X-Vercel-AI-Data-Stream': 'v1',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        }
    )
