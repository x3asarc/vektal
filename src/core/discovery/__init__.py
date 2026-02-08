"""
Discovery Module

Vendor discovery and SKU pattern matching.
"""

# Placeholder for existing imports that might be referenced
try:
    from .store_analyzer import StoreProfileAnalyzer
    from .catalog_extractor import (
        extract_keywords,
        detect_niche,
        learn_sku_patterns,
        extract_vendors
    )
except ImportError:
    # These will be implemented in future plans
    pass

from .sku_validator import (
    validate_sku,
    normalize_sku,
    extract_sku_info,
    infer_size_from_sku,
    SKUInfo
)
from .local_patterns import LocalPatternMatcher, PatternMatchResult
from .niche_validator import (
    validate_niche_match,
    detect_niche_from_text,
    get_niche_keywords,
    NicheValidationResult
)
from .web_search import WebSearchClient, SearchResult, WebSearchResponse
from .local_classifier import LocalVendorClassifier, ClassificationResult
from .ai_inference import OpenRouterInference, InferenceResult
from .pipeline import VendorDiscoveryPipeline, DiscoveryResult

__all__ = [
    "validate_sku",
    "normalize_sku",
    "extract_sku_info",
    "infer_size_from_sku",
    "SKUInfo",
    "LocalPatternMatcher",
    "PatternMatchResult",
    "validate_niche_match",
    "detect_niche_from_text",
    "get_niche_keywords",
    "NicheValidationResult",
    "WebSearchClient",
    "SearchResult",
    "WebSearchResponse",
    "LocalVendorClassifier",
    "ClassificationResult",
    "OpenRouterInference",
    "InferenceResult",
    "VendorDiscoveryPipeline",
    "DiscoveryResult"
]
