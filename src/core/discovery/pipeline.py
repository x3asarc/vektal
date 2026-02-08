"""
Vendor Discovery Pipeline

Orchestrates the complete discovery flow:
1. Local pattern matching (free, instant)
2. Web search with context (free, 1-2s)
3. Local LLM classification (free, <100ms)
4. API LLM inference (paid, 2-3s)

Early exit when confidence >= 0.90.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

from src.core.config.store_profile_schema import StoreProfile
from .local_patterns import LocalPatternMatcher, PatternMatchResult
from .web_search import WebSearchClient, WebSearchResponse
from .local_classifier import LocalVendorClassifier, ClassificationResult
from .ai_inference import OpenRouterInference, InferenceResult
from .niche_validator import validate_niche_match

logger = logging.getLogger(__name__)


@dataclass
class DiscoveryResult:
    """Complete discovery result."""
    sku: str
    vendor_name: Optional[str]
    vendor_slug: Optional[str]
    confidence: float
    requires_confirmation: bool

    # Stage information
    discovery_method: str  # local_pattern, web_search, local_llm, api_llm
    stages_executed: list[str] = field(default_factory=list)

    # Additional data
    vendor_website: Optional[str] = None
    vendor_niche: Optional[str] = None
    niche_match: bool = True
    sku_info: Optional[dict] = None

    # Timing
    discovery_time_ms: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Messages for user
    message: Optional[str] = None
    suggestions: list[str] = field(default_factory=list)


class VendorDiscoveryPipeline:
    """
    Orchestrates vendor discovery across multiple stages.

    Flow:
    1. Try local pattern matching (instant, free)
       - If confidence >= 0.90: return immediately
    2. Try web search with store context
       - If confidence >= 0.80: return
    3. Try local LLM classification
       - If confidence >= 0.85: return
    4. Try API LLM inference (paid)
       - Return result regardless of confidence
    """

    # Confidence thresholds for early exit
    PATTERN_CONFIDENCE = 0.90    # High confidence for known patterns
    SEARCH_CONFIDENCE = 0.80     # Good enough from web search
    LOCAL_LLM_CONFIDENCE = 0.85  # Trust local classification
    CONFIRMATION_THRESHOLD = 0.70  # Below this, require user confirmation

    def __init__(
        self,
        store_profile: Optional[StoreProfile] = None,
        vendor_config_dir: str = "config/vendors",
        enable_api_inference: bool = True
    ):
        """
        Initialize discovery pipeline.

        Args:
            store_profile: Store profile for context
            vendor_config_dir: Directory with vendor YAML configs
            enable_api_inference: Whether to use paid API as last resort
        """
        self.store_profile = store_profile
        self.enable_api_inference = enable_api_inference

        # Initialize components
        self.pattern_matcher = LocalPatternMatcher(
            vendor_config_dir=vendor_config_dir,
            store_profile=store_profile
        )
        self.web_search = WebSearchClient(store_profile=store_profile)
        self.local_classifier = LocalVendorClassifier()
        self.api_inference = OpenRouterInference()

    def discover(
        self,
        sku: str,
        skip_patterns: bool = False,
        skip_search: bool = False,
        force_api: bool = False
    ) -> DiscoveryResult:
        """
        Discover vendor for a SKU.

        Args:
            sku: SKU to discover vendor for
            skip_patterns: Skip local pattern matching
            skip_search: Skip web search
            force_api: Force API inference regardless of other results

        Returns:
            DiscoveryResult with vendor information
        """
        import time
        start_time = time.time()

        stages_executed = []
        result = None

        # Stage 1: Local Pattern Matching
        if not skip_patterns and not force_api:
            pattern_result = self.pattern_matcher.match(sku)
            stages_executed.append("local_pattern")

            if pattern_result.matched and pattern_result.confidence >= self.PATTERN_CONFIDENCE:
                logger.info(
                    f"Pattern match: {pattern_result.vendor_name} "
                    f"(confidence: {pattern_result.confidence})"
                )
                result = self._build_result(
                    sku=sku,
                    vendor_name=pattern_result.vendor_name,
                    vendor_slug=pattern_result.vendor_slug,
                    confidence=pattern_result.confidence,
                    method="local_pattern",
                    stages=stages_executed,
                    sku_info=pattern_result.sku_info,
                    start_time=start_time
                )
                return result

        # Stage 2: Web Search
        if not skip_search and not force_api:
            search_response = self.web_search.search(sku)
            stages_executed.append("web_search")

            if search_response.success and search_response.top_vendor:
                # Apply niche validation
                confidence = search_response.top_vendor_confidence

                if search_response.niche_validation:
                    confidence *= search_response.niche_validation.get(
                        "confidence_modifier", 1.0
                    )

                if confidence >= self.SEARCH_CONFIDENCE:
                    logger.info(
                        f"Web search match: {search_response.top_vendor} "
                        f"(confidence: {confidence})"
                    )
                    result = self._build_result(
                        sku=sku,
                        vendor_name=search_response.top_vendor,
                        vendor_slug=self._to_slug(search_response.top_vendor),
                        confidence=confidence,
                        method="web_search",
                        stages=stages_executed,
                        niche_match=search_response.niche_validation.get(
                            "is_compatible", True
                        ) if search_response.niche_validation else True,
                        start_time=start_time
                    )
                    return result

        # Stage 3: Local LLM Classification
        if not force_api:
            # Build text from search results if available
            search_text = ""
            if 'search_response' in dir() and search_response.results:
                search_text = " ".join([
                    f"{r.title} {r.snippet}"
                    for r in search_response.results[:5]
                ])

            if search_text:
                context = " ".join(self.store_profile.keywords[:5]) if self.store_profile else ""
                class_result = self.local_classifier.classify(search_text, context)
                stages_executed.append("local_llm")

                if class_result.vendor_name and class_result.confidence >= self.LOCAL_LLM_CONFIDENCE:
                    logger.info(
                        f"Local LLM match: {class_result.vendor_name} "
                        f"(confidence: {class_result.confidence})"
                    )
                    result = self._build_result(
                        sku=sku,
                        vendor_name=class_result.vendor_name,
                        vendor_slug=self._to_slug(class_result.vendor_name),
                        confidence=class_result.confidence,
                        method="local_llm",
                        stages=stages_executed,
                        start_time=start_time
                    )
                    return result

        # Stage 4: API LLM Inference (paid, last resort)
        if self.enable_api_inference and self.api_inference.is_available:
            stages_executed.append("api_llm")

            # Build search results tuple for caching
            search_results = tuple()
            if 'search_response' in dir() and search_response.results:
                search_results = tuple([
                    f"{r.title}: {r.snippet}" for r in search_response.results[:10]
                ])

            known_vendors = tuple()
            if self.store_profile:
                known_vendors = tuple([v.name for v in self.store_profile.known_vendors])

            store_niche = self.store_profile.niche_primary if self.store_profile else "other"
            context = " ".join(self.store_profile.keywords[:5]) if self.store_profile else ""

            api_result = self.api_inference.infer_vendor(
                sku=sku,
                search_results=search_results,
                store_niche=store_niche,
                known_vendors=known_vendors,
                additional_context=context
            )

            if api_result.vendor_name:
                logger.info(
                    f"API inference: {api_result.vendor_name} "
                    f"(confidence: {api_result.confidence})"
                )
                result = self._build_result(
                    sku=sku,
                    vendor_name=api_result.vendor_name,
                    vendor_slug=self._to_slug(api_result.vendor_name),
                    confidence=api_result.confidence,
                    method="api_llm",
                    stages=stages_executed,
                    vendor_website=api_result.vendor_website,
                    vendor_niche=api_result.vendor_niche,
                    niche_match=api_result.niche_match,
                    message=api_result.reasoning,
                    start_time=start_time
                )
                return result

        # No result found
        elapsed = int((time.time() - start_time) * 1000)
        return DiscoveryResult(
            sku=sku,
            vendor_name=None,
            vendor_slug=None,
            confidence=0.0,
            requires_confirmation=True,
            discovery_method="none",
            stages_executed=stages_executed,
            discovery_time_ms=elapsed,
            message="Could not identify vendor",
            suggestions=[
                "Try providing more context (vendor name, keywords)",
                "Check if SKU is correct",
                "Manual vendor configuration may be needed"
            ]
        )

    def _build_result(
        self,
        sku: str,
        vendor_name: str,
        vendor_slug: str,
        confidence: float,
        method: str,
        stages: list,
        start_time: float,
        **kwargs
    ) -> DiscoveryResult:
        """Build discovery result with timing."""
        import time
        elapsed = int((time.time() - start_time) * 1000)

        return DiscoveryResult(
            sku=sku,
            vendor_name=vendor_name,
            vendor_slug=vendor_slug,
            confidence=round(confidence, 2),
            requires_confirmation=confidence < self.CONFIRMATION_THRESHOLD,
            discovery_method=method,
            stages_executed=stages,
            discovery_time_ms=elapsed,
            **kwargs
        )

    def _to_slug(self, name: str) -> str:
        """Convert vendor name to slug."""
        import re
        slug = name.lower()
        slug = re.sub(r'[^a-z0-9]+', '_', slug)
        slug = slug.strip('_')
        return slug
