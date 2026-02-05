"""
Vision AI Client for Image Alt Text Generation
Supports OpenRouter API (OpenAI-compatible) and Google Gemini Vision
"""
import os
import time
import logging
from typing import Optional
from dotenv import load_dotenv

try:
    from openai import OpenAI  # For OpenRouter
except ImportError:
    OpenAI = None

try:
    from google import genai  # For Gemini Vision
except ImportError:
    genai = None

from src.core.vision_prompts import VISION_SYSTEM_INSTRUCTION, get_vision_prompt, get_vision_metadata_prompt
from src.core.secrets import get_secret

load_dotenv()

logger = logging.getLogger(__name__)

class VisionAIClient:
    """Vision AI client with OpenRouter/Gemini support."""

    _cooldown_until = None  # Class-level cooldown (like SEOContentGenerator)

    def __init__(self, api_key: str = None, model: str = None, provider: str = "openrouter"):
        """
        Initialize vision AI client.

        Args:
            api_key: API key (defaults to env var)
            model: Model ID (defaults to gemini-flash-1.5-8b for OpenRouter)
            provider: 'openrouter' or 'gemini'
        """
        self.provider = provider
        self.model = model or os.getenv("VISION_AI_MODEL", "google/gemini-flash-1.5-8b")

        if provider == "openrouter":
            self.api_key = api_key or get_secret("OPENROUTER_API_KEY")
            if OpenAI and self.api_key:
                self.client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=self.api_key
                )
            else:
                self.client = None
        elif provider == "gemini":
            self.api_key = api_key or get_secret("GEMINI_API_KEY")
            if genai and self.api_key:
                self.client = genai.Client(api_key=self.api_key)
            else:
                self.client = None
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def generate_alt_text(self, image_url: str, product_title: str, vendor: str,
                          product_type: str = "", tags: Optional[list[str]] = None,
                          max_retries: Optional[int] = None) -> Optional[str]:
        """
        Generate alt text for image using vision AI.

        Args:
            image_url: URL of product image
            product_title: Product title
            vendor: Brand/vendor name
            product_type: Product category (optional)
            tags: Product tags (optional)
            max_retries: Number of retry attempts (defaults to env VISION_AI_MAX_RETRIES)

        Returns:
            Generated alt text (max 125 chars) or None if failed
        """
        # Check cooldown
        if VisionAIClient._cooldown_until and time.time() < VisionAIClient._cooldown_until:
            return None

        if not self.client:
            return None

        if max_retries is None:
            try:
                max_retries = int(os.getenv("VISION_AI_MAX_RETRIES", "3"))
            except ValueError:
                max_retries = 3

        prompt = get_vision_prompt(product_title, vendor, product_type, tags)

        for attempt in range(max_retries):
            try:
                if self.provider == "openrouter":
                    return self._call_openrouter(image_url, prompt)
                elif self.provider == "gemini":
                    return self._call_gemini(image_url, prompt)
            except Exception as e:
                logger.warning("Vision AI attempt %s failed: %s", attempt + 1, str(e))
                if attempt == max_retries - 1:
                    # Final attempt failed
                    logger.error("Vision AI failed after %s attempts", max_retries)
                    return None

                # Exponential backoff: 2s, 4s, 8s
                wait_time = 2 ** attempt
                time.sleep(wait_time)

        return None

    def _call_openrouter(self, image_url: str, prompt: str) -> str:
        """Call OpenRouter vision API."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": VISION_SYSTEM_INSTRUCTION},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
            ],
            max_tokens=150,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()[:125]

    def _call_gemini(self, image_url: str, prompt: str) -> str:
        """Call Gemini Vision API."""
        import requests
        from io import BytesIO
        from PIL import Image

        # Download image
        img_response = requests.get(image_url, timeout=10)
        img_response.raise_for_status()
        image = Image.open(BytesIO(img_response.content))

        # Call Gemini with image
        full_prompt = f"{VISION_SYSTEM_INSTRUCTION}\n\n{prompt}"
        response = self.client.models.generate_content(
            model=self.model,
            contents=[full_prompt, image],
            config=genai.types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=150
            )
        )
        return response.text.strip()[:125]

    def generate_metadata(self, image_url: str, product_title: str, vendor: str,
                         product_type: str = "", tags: Optional[list[str]] = None,
                         max_retries: Optional[int] = None) -> Optional[dict]:
        """
        Generate image metadata (type + description) using vision AI.
        Used for hybrid naming system.

        Args:
            image_url: URL of product image
            product_title: Product title
            vendor: Brand/vendor name
            product_type: Product category (optional)
            tags: Product tags (optional)
            max_retries: Number of retry attempts (defaults to env VISION_AI_MAX_RETRIES)

        Returns:
            Dict with keys: type, description
            Example: {"type": "groupshot", "description": "Mehrere Dosen mit Galaxy Flakes..."}
            Returns None if failed
        """
        # Check cooldown
        if VisionAIClient._cooldown_until and time.time() < VisionAIClient._cooldown_until:
            return None

        if not self.client:
            return None

        if max_retries is None:
            try:
                max_retries = int(os.getenv("VISION_AI_MAX_RETRIES", "3"))
            except ValueError:
                max_retries = 3

        prompt = get_vision_metadata_prompt(product_title, vendor, product_type, tags)

        for attempt in range(max_retries):
            try:
                if self.provider == "openrouter":
                    response_text = self._call_openrouter_raw(image_url, prompt)
                elif self.provider == "gemini":
                    response_text = self._call_gemini_raw(image_url, prompt)
                else:
                    return None

                # Parse structured response
                metadata = self._parse_metadata_response(response_text)
                if metadata:
                    return metadata

            except Exception as e:
                logger.warning("Vision metadata attempt %s failed: %s", attempt + 1, str(e))
                if attempt == max_retries - 1:
                    logger.error("Vision metadata failed after %s attempts", max_retries)
                    return None

                # Exponential backoff
                wait_time = 2 ** attempt
                time.sleep(wait_time)

        return None

    def _call_openrouter_raw(self, image_url: str, prompt: str) -> str:
        """Call OpenRouter vision API (returns raw response)."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
            ],
            max_tokens=300,
            temperature=0.3  # Lower temperature for more consistent formatting
        )
        return response.choices[0].message.content.strip()

    def _call_gemini_raw(self, image_url: str, prompt: str) -> str:
        """Call Gemini Vision API (returns raw response)."""
        import requests
        from io import BytesIO
        from PIL import Image

        # Download image
        img_response = requests.get(image_url, timeout=10)
        img_response.raise_for_status()
        image = Image.open(BytesIO(img_response.content))

        # Call Gemini with image
        response = self.client.models.generate_content(
            model=self.model,
            contents=[prompt, image],
            config=genai.types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=300
            )
        )
        return response.text.strip()

    def _parse_metadata_response(self, response_text: str) -> Optional[dict]:
        """
        Parse structured metadata response from vision AI.

        Expected format:
        TYPE: groupshot
        DESCRIPTION: Mehrere Dosen mit Galaxy Flakes in verschiedenen Farben

        Returns:
            Dict with type and description, or None if parse failed
        """
        try:
            lines = response_text.strip().split('\n')
            metadata = {}

            for line in lines:
                line = line.strip()
                if line.startswith('TYPE:'):
                    metadata['type'] = line.replace('TYPE:', '').strip().lower()
                elif line.startswith('DESCRIPTION:'):
                    metadata['description'] = line.replace('DESCRIPTION:', '').strip()

            # Validate required fields
            if 'type' in metadata and 'description' in metadata:
                # Normalize type to allowed values
                allowed_types = {'packshot', 'groupshot', 'detail', 'lifestyle'}
                if metadata['type'] not in allowed_types:
                    # Default to detail if unrecognized
                    logger.warning(f"Unrecognized image type '{metadata['type']}', defaulting to 'detail'")
                    metadata['type'] = 'detail'

                return metadata

            logger.warning(f"Failed to parse metadata from response: {response_text}")
            return None

        except Exception as e:
            logger.error(f"Error parsing metadata response: {e}")
            return None
