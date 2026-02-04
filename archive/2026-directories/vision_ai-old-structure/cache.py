"""
SQLite caching layer for vision-generated alt text.
"""
from src.core.vision_cache import VisionAltTextCache, BudgetExceededError

__all__ = ["VisionAltTextCache", "BudgetExceededError"]
