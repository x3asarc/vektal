"""AI-powered content generators for product enrichment.

This module provides generators for:
- AI descriptions via OpenRouter
- SEO meta content (titles, descriptions, URL handles)
- Image alt text for accessibility
"""

__all__ = []

# Conditional imports - only import modules that exist
try:
    from .descriptions import AIDescriptionGenerator
    __all__.append('AIDescriptionGenerator')
except ImportError:
    pass

try:
    from .seo import SEOGenerator
    __all__.append('SEOGenerator')
except ImportError:
    pass
