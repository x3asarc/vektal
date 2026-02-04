"""
Main alt text generation logic with caching and retries.
"""
from __future__ import annotations

import os
import logging
from typing import Dict, List, Optional

from src.core.image_scraper import clean_product_name, validate_alt_text
from src.core.vision_cache import VisionAltTextCache, BudgetExceededError
from src.core.vision_client import VisionAIClient

logger = logging.getLogger(__name__)


class AltTextGenerator:
    """Generate German SEO-friendly alt text with intelligent caching."""

    def __init__(
        self,
        cache_db_path: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        max_retries: Optional[int] = None,
    ):
        self.cache = VisionAltTextCache(db_path=cache_db_path)
        self.provider = provider or os.getenv("VISION_AI_PROVIDER", "openrouter")
        self.model = model or os.getenv("VISION_AI_MODEL", "google/gemini-flash-1.5-8b")
        self.max_retries = max_retries

    def generate(self, image_url: str, product_context: Dict) -> str:
        """Generate alt text for a single image URL."""
        if not image_url:
            raise ValueError("image_url is required")

        cached = self.cache.get(image_url)
        if cached:
            return cached

        try:
            self.cache.ensure_within_budget()
        except BudgetExceededError as exc:
            logger.error("Vision AI budget exceeded, using fallback: %s", str(exc))
            return self._generate_fallback(product_context)

        title = (product_context.get("title") or "Produkt").strip()
        vendor = (product_context.get("vendor") or "").strip()
        product_type = (product_context.get("product_type") or "").strip()
        tags_value = product_context.get("tags") or []
        if isinstance(tags_value, str):
            tags = [tag.strip() for tag in tags_value.split(",") if tag.strip()]
        elif isinstance(tags_value, list):
            tags = tags_value
        else:
            tags = []

        cleaned_title = clean_product_name(title) or title

        client = VisionAIClient(provider=self.provider, model=self.model)
        alt_text = client.generate_alt_text(
            image_url=image_url,
            product_title=cleaned_title,
            vendor=vendor,
            product_type=product_type,
            tags=tags,
            max_retries=self.max_retries,
        )

        if not alt_text:
            return self._generate_fallback(product_context)

        validated, warning = validate_alt_text(alt_text)
        if warning:
            logger.warning("Alt text validation warning: %s", warning)

        cache_context = {
            "title": title,
            "vendor": vendor,
            "product_type": product_type,
            "tags": tags,
        }
        self.cache.set(image_url, validated, cache_context, client.model)
        return validated

    def generate_batch(self, items: List[Dict]) -> List[Dict]:
        """Generate alt text for a batch of images."""
        results = []
        for item in items:
            image_url = item.get("image_url")
            context = item.get("product_context", {})
            alt_text = self.generate(image_url, context)
            results.append({
                "image_url": image_url,
                "alt_text": alt_text,
            })
        return results

    def get_stats(self) -> Dict:
        """Return aggregated and daily usage statistics."""
        total = self.cache.get_stats()
        today = self.cache.get_stats_for_date()
        return {
            **total,
            "today": today,
            "cost_today": today.get("cost_eur", 0.0),
        }

    @staticmethod
    def _generate_fallback(product_context: Dict) -> str:
        """Fallback when AI fails: construct from product data."""
        title = product_context.get("title") or "Produkt"
        vendor = product_context.get("vendor") or ""
        if vendor:
            return f"{title} von {vendor}"[:125]
        return str(title)[:125]
