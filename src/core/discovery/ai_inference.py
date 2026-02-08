"""
OpenRouter AI Inference

LLM-powered vendor inference via OpenRouter.
Used when local patterns and web search fail.
Cost: ~$0.10/1M tokens (Gemini Flash)
"""

import os
import json
import logging
from dataclasses import dataclass
from typing import Optional
from functools import lru_cache

import requests

logger = logging.getLogger(__name__)


@dataclass
class InferenceResult:
    """Result of AI inference."""
    vendor_name: Optional[str]
    vendor_website: Optional[str]
    vendor_niche: Optional[str]
    confidence: float
    niche_match: bool
    reasoning: str
    method: str = "ai_inference"
    error: Optional[str] = None


class OpenRouterInference:
    """
    LLM-powered vendor inference via OpenRouter.

    Uses Gemini Flash by default ($0.10/1M tokens).
    Results are cached to prevent repeated API calls.
    """

    API_URL = "https://openrouter.ai/api/v1/chat/completions"
    DEFAULT_MODEL = "google/gemini-flash-1.5"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        Initialize inference client.

        Args:
            api_key: OpenRouter API key (defaults to env var)
            model: Model to use (defaults to Gemini Flash)
        """
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')
        self.model = model or self.DEFAULT_MODEL

        if not self.api_key:
            logger.warning(
                "OPENROUTER_API_KEY not set. "
                "AI inference will be unavailable."
            )

    @property
    def is_available(self) -> bool:
        """Check if API key is configured."""
        return bool(self.api_key)

    @lru_cache(maxsize=500)
    def infer_vendor(
        self,
        sku: str,
        search_results: tuple,  # Tuple for hashable cache key
        store_niche: str,
        known_vendors: tuple,
        additional_context: str = ""
    ) -> InferenceResult:
        """
        Infer vendor from search results using LLM.

        Args:
            sku: SKU being searched
            search_results: Tuple of search result strings
            store_niche: Store's primary niche
            known_vendors: Tuple of known vendor names
            additional_context: Extra context (keywords)

        Returns:
            InferenceResult with vendor analysis
        """
        if not self.is_available:
            return InferenceResult(
                vendor_name=None,
                vendor_website=None,
                vendor_niche=None,
                confidence=0.0,
                niche_match=False,
                reasoning="API key not configured",
                error="OPENROUTER_API_KEY not set"
            )

        prompt = self._build_prompt(
            sku,
            list(search_results),
            store_niche,
            list(known_vendors),
            additional_context
        )

        try:
            response = self._call_api(prompt)
            return self._parse_response(response, store_niche)

        except Exception as e:
            logger.error(f"AI inference failed: {e}")
            return InferenceResult(
                vendor_name=None,
                vendor_website=None,
                vendor_niche=None,
                confidence=0.0,
                niche_match=False,
                reasoning=f"API error: {e}",
                error=str(e)
            )

    def _build_prompt(
        self,
        sku: str,
        search_results: list,
        store_niche: str,
        known_vendors: list,
        additional_context: str
    ) -> str:
        """Build the LLM prompt."""
        results_text = "\n".join([
            f"- {r}" for r in search_results[:10]
        ])

        return f"""Analyze these search results for product SKU "{sku}":

{results_text}

Store Context:
- Store niche: {store_niche.replace('_', ' ').title()}
- Known vendors: {', '.join(known_vendors) if known_vendors else 'None'}
- Keywords: {additional_context}

Tasks:
1. Identify the most likely vendor/manufacturer for this SKU
2. Find the vendor's official website
3. Determine the vendor's primary product niche
4. Check if the vendor's niche matches the store's niche
5. Rate your confidence (0-100%)

IMPORTANT: If the vendor's niche does NOT match the store's niche (e.g., car parts vendor for a craft store), this is likely a FALSE MATCH. Set niche_match to false and lower confidence.

Return ONLY valid JSON:
{{
    "vendor_name": "Vendor Name",
    "vendor_website": "https://vendor.com",
    "vendor_niche": "arts_and_crafts or automotive or electronics or ...",
    "niche_match": true or false,
    "confidence": 0-100,
    "reasoning": "Brief explanation"
}}"""

    def _call_api(self, prompt: str) -> dict:
        """Call OpenRouter API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://shopify-platform.local",
            "X-Title": "Vendor Discovery"
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,  # Low for consistent results
            "max_tokens": 500
        }

        response = requests.post(
            self.API_URL,
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    def _parse_response(self, response: dict, store_niche: str) -> InferenceResult:
        """Parse LLM response."""
        try:
            content = response['choices'][0]['message']['content']

            # Extract JSON from response (may have markdown code blocks)
            content = content.strip()
            if content.startswith('```'):
                lines = content.split('\n')
                content = '\n'.join(lines[1:-1])  # Remove code block markers

            data = json.loads(content)

            confidence = data.get('confidence', 0) / 100.0

            # Apply niche penalty if mismatch
            niche_match = data.get('niche_match', True)
            if not niche_match:
                confidence *= 0.5  # 50% penalty for niche mismatch

            return InferenceResult(
                vendor_name=data.get('vendor_name'),
                vendor_website=data.get('vendor_website'),
                vendor_niche=data.get('vendor_niche'),
                confidence=round(confidence, 2),
                niche_match=niche_match,
                reasoning=data.get('reasoning', '')
            )

        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return InferenceResult(
                vendor_name=None,
                vendor_website=None,
                vendor_niche=None,
                confidence=0.0,
                niche_match=False,
                reasoning="Failed to parse LLM response",
                error=str(e)
            )
