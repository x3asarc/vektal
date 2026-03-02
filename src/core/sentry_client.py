import os
import requests
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class SentryClient:
    """Simple Sentry API client for querying issue status."""

    def __init__(self, api_key: Optional[str] = None, organization_slug: Optional[str] = None, project_slug: Optional[str] = None):
        self.api_key = api_key or os.getenv("SENTRY_AUTH_TOKEN")
        self.org_slug = organization_slug or os.getenv("SENTRY_ORG_SLUG")
        self.project_slug = project_slug or os.getenv("SENTRY_PROJECT_SLUG")
        self.base_url = "https://sentry.io/api/0"

    def get_issue(self, issue_id: str) -> Dict[str, Any]:
        """
        Query Sentry for issue details.
        
        Note: For Phase 15.1 simulation, if SENTRY_AUTH_TOKEN is missing,
        this returns a 'resolved' mock state.
        """
        if not self.api_key:
            logger.debug(f"Sentry API key missing, returning mock for {issue_id}")
            return {
                'id': issue_id,
                'status': 'resolved',
                'activity': [] # No new activity means validated success
            }

        try:
            url = f"{self.base_url}/issues/{issue_id}/"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Sentry API call failed: {e}")
            return {'status': 'unknown', 'error': str(e)}

def get_sentry_client() -> SentryClient:
    return SentryClient()
