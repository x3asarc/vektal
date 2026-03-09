"""LLM Client for project-wide LLM interaction."""
import os
import json
import logging
import requests
import sys
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

class LLMClient:
    """Simple client for OpenRouter/Gemini interaction."""

    def __init__(self, api_key: Optional[str] = None, default_model: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.default_model = default_model or os.getenv("OPENROUTER_TEXT_MODEL", "google/gemini-2.0-flash-001")
        
        if not self.api_key:
            logger.warning("OPENROUTER_API_KEY not set. LLM completions will fail.")

    def complete(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4000,
        **kwargs
    ) -> str:
        """Get completion from OpenRouter with fallback on model errors."""
        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY missing")

        model = model or self.default_model
        fallback_model = os.getenv("OPENROUTER_TEXT_FALLBACK_MODEL", "google/gemini-flash-1.5")

        # Try primary model first
        result = self._attempt_completion(prompt, model, temperature, max_tokens, **kwargs)
        if result is not None:
            return result

        # Fallback to known-good model on 404 or model errors
        if model != fallback_model:
            print(f"Warning: Model '{model}' failed, falling back to '{fallback_model}'", file=sys.stderr)
            result = self._attempt_completion(prompt, fallback_model, temperature, max_tokens, **kwargs)
            if result is not None:
                return result

        # Both failed - raise
        raise RuntimeError(f"LLM completion failed for both primary and fallback models")

    def _attempt_completion(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> Optional[str]:
        """Attempt a single completion, return None on retryable errors."""
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }

        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=120  # Long timeout for large code generation
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except requests.exceptions.HTTPError as e:
            # 404 = invalid model, 401 = auth issue - both retryable with fallback
            if e.response is not None and e.response.status_code in [404, 401]:
                logger.warning(f"Retryable error for model '{model}': {e.response.status_code} {e.response.text[:200]}")
                return None  # Signal fallback
            else:
                logger.error(f"Non-retryable HTTP error: {e}")
                raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            logger.error(f"Invalid response format: {e}")
            raise

def get_llm_client() -> LLMClient:
    """Helper for singleton or fresh client instance."""
    # For now, return a new instance
    return LLMClient()
