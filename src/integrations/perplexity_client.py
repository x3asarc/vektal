"""
Perplexity AI client wrapper for research automation.
"""
import httpx
import os
import logging
from functools import lru_cache
from typing import Any, Dict

logger = logging.getLogger(__name__)

class PerplexityClient:
    """Wrapper for Perplexity AI API."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        self.base_url = "https://api.perplexity.ai"

    async def search(
        self,
        query: str,
        max_results: int = 5
    ) -> Dict[str, Any]:
        """Execute AI-powered search with citations."""
        if not self.api_key:
            logger.warning("PERPLEXITY_API_KEY not set")
            return {"status": "skipped", "reason": "no_api_key"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": "sonar",
                        "messages": [
                            {
                                "role": "system",
                                "content": "Be precise and concise. Provide sources."
                            },
                            {
                                "role": "user",
                                "content": query
                            }
                        ],
                        "max_tokens": 1000,
                        "temperature": 0.2
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()

                return {
                    "status": "success",
                    "answer": data["choices"][0]["message"]["content"],
                    "citations": data.get("citations", []),
                    "usage": data.get("usage", {})
                }

        except Exception as e:
            logger.error(f"Perplexity API error: {e}")
            return {"status": "error", "error": str(e)}


@lru_cache(maxsize=1)
def get_perplexity_client() -> PerplexityClient:
    """Get singleton Perplexity client."""
    return PerplexityClient()
