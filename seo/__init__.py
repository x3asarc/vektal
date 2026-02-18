"""
SEO Content Generator Module

This module provides tools for generating SEO-optimized content for Shopify products
using Google Gemini AI.

Main Components:
- SEOContentGenerator: Generates SEO content using AI
- ProductFetcher: Fetches products from Shopify
- ProductUpdater: Updates products with SEO content
- SEOValidator: Validates generated content against best practices
"""

from .seo_generator import (
    SEOContentGenerator,
    ProductFetcher,
    ProductUpdater,
    ShopifyClient
)
from .seo_validator import SEOValidator
from .seo_prompts import (
    SYSTEM_INSTRUCTION,
    get_product_prompt,
    get_quick_prompt
)

__all__ = [
    'SEOContentGenerator',
    'ProductFetcher',
    'ProductUpdater',
    'ShopifyClient',
    'SEOValidator',
    'SYSTEM_INSTRUCTION',
    'get_product_prompt',
    'get_quick_prompt'
]
