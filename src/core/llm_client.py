"""LLM Client for project-wide LLM interaction."""
import os
import json
import logging
import requests
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
        """Get completion from OpenRouter."""
        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY missing")

        model = model or self.default_model
        
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
        except Exception as e:
            logger.error(f"LLM completion failed: {e}")
            raise

def get_llm_client() -> LLMClient:
    """Helper for singleton or fresh client instance."""
    # For now, return a new instance
    return LLMClient()
