"""
Aura Remediator Tool (Phase 14.3).
Autonomous management for Neo4j Aura Cloud instances.
"""

import os
import time
import logging
import httpx
from typing import Dict, Any, Optional
from src.graph.universal_fixer import UniversalRemediator, RemediationResult

logger = logging.getLogger(__name__)

class AuraRemediator(UniversalRemediator):
    """
    Remediator for Neo4j Aura Cloud instances.
    Handles 'PAUSED' state remediation and health status checks.
    """
    
    _token_cache: Dict[str, Any] = {}
    TOKEN_TTL = 3600 # 1 hour TTL for OAuth tokens

    @property
    def service_name(self) -> str:
        return "aura"

    @property
    def description(self) -> str:
        return "Manages Neo4j Aura Cloud instances (resume/status)."

    async def _get_oauth_token(self) -> Optional[str]:
        """Fetches and caches an OAuth2 token for Aura Console API."""
        client_id = os.getenv("AURA_CLIENT_ID")
        client_secret = os.getenv("AURA_CLIENT_SECRET")
        tenant_id = os.getenv("AURA_TENANT_ID")

        if not all([client_id, client_secret, tenant_id]):
            logger.warning("⚠️ [AuraRemediator] Credentials missing (AURA_CLIENT_ID/SECRET/TENANT_ID).")
            return None

        # Check cache
        cached = self._token_cache.get(tenant_id)
        if cached and time.time() < cached["expires_at"]:
            return cached["token"]

        # Fetch new token
        url = "https://api.neo4j.io/oauth/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "audience": "https://api.neo4j.io"
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.post(url, data=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    token = data["access_token"]
                    # Cache token (TTL - 60s buffer)
                    self._token_cache[tenant_id] = {
                        "token": token,
                        "expires_at": time.time() + self.TOKEN_TTL - 60
                    }
                    return token
                else:
                    logger.error(f"❌ [AuraRemediator] OAuth failed with status {resp.status_code}: {resp.text}")
                    return None
            except Exception as e:
                logger.error(f"❌ [AuraRemediator] OAuth request error: {e}")
                return None

    async def validate_environment(self) -> bool:
        """Check if required environment variables are set."""
        return all([
            os.getenv("AURA_CLIENT_ID"),
            os.getenv("AURA_CLIENT_SECRET"),
            os.getenv("AURA_TENANT_ID"),
            os.getenv("AURA_INSTANCE_ID")
        ])

    async def diagnose_and_fix(self, params: Optional[Dict[str, Any]] = None) -> RemediationResult:
        actions = []
        instance_id = os.getenv("AURA_INSTANCE_ID")
        token = await self._get_oauth_token()
        
        if not token:
            return RemediationResult(False, "Failed to obtain Aura OAuth token", ["Token Acquisition"])

        headers = {"Authorization": f"Bearer {token}"}
        url = f"https://api.neo4j.io/v1/instances/{instance_id}"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                # 1. Diagnose: Check current status
                resp = await client.get(url, headers=headers)
                if resp.status_code != 200:
                    return RemediationResult(False, f"Failed to fetch instance status (HTTP {resp.status_code})", ["Status Probe"])
                
                data = resp.json().get("data", {})
                status = data.get("status", "unknown").upper()
                actions.append(f"Current Aura instance status: {status}")

                if status == "RUNNING":
                    return RemediationResult(True, "Aura instance is already running", actions)

                # 2. Fix: Attempt to resume if paused
                if status == "PAUSED" or (params and params.get("action") == "resume"):
                    actions.append("Attempting to resume Aura instance...")
                    resume_url = f"{url}/resume"
                    resume_resp = await client.post(resume_url, headers=headers)
                    
                    if resume_resp.status_code in (200, 202):
                        return RemediationResult(True, "Resume command accepted by Aura API", actions)
                    else:
                        return RemediationResult(
                            False, 
                            f"Resume command failed (HTTP {resume_resp.status_code})", 
                            actions, 
                            error_details=resume_resp.text
                        )
                
                return RemediationResult(False, f"Aura instance is in unhandled state: {status}", actions)

            except Exception as e:
                return RemediationResult(False, f"Aura API request error: {str(e)}", actions)
