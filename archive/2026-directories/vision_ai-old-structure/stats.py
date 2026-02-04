"""
Usage tracking and cost calculation helpers.
"""
from typing import Optional, Dict
from src.core.vision_cache import VisionAltTextCache


def get_stats(cache_db_path: Optional[str] = None) -> Dict:
    """Return aggregated usage statistics."""
    cache = VisionAltTextCache(db_path=cache_db_path)
    return cache.get_stats()


def get_stats_today(cache_db_path: Optional[str] = None) -> Dict:
    """Return today's usage statistics."""
    cache = VisionAltTextCache(db_path=cache_db_path)
    return cache.get_stats_for_date()
