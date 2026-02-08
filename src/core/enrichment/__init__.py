"""
Product Enrichment Pipeline

Extracts structured attributes from product data, calculates quality scores,
and enriches product descriptions with AI-generated content.

German-first design for craft supply products.
"""

# Conditional imports - only import modules that exist
__all__ = []

try:
    from .extractors import AttributeExtractor
    __all__.append('AttributeExtractor')
except ImportError:
    pass

try:
    from .generators import AIDescriptionGenerator, SEOGenerator
    __all__.extend(['AIDescriptionGenerator', 'SEOGenerator'])
except ImportError:
    pass
