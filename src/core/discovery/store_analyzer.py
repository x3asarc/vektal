"""
Store Profile Analyzer

Analyzes existing Shopify catalog to build store intelligence profile.
Follows catalog-first approach from CONTEXT.md:
- 50+ products: High confidence, catalog is source of truth
- 10-49 products: Medium confidence, hybrid approach
- <10 products: Low confidence, questionnaire needed
"""

from datetime import datetime
from typing import Optional
import logging

from src.core.config.store_profile_schema import (
    StoreProfile, KnownVendor, CatalogStats, DiscoverySettings
)
from .catalog_extractor import (
    extract_keywords, detect_niche, learn_sku_patterns, extract_vendors
)

logger = logging.getLogger(__name__)


class StoreProfileAnalyzer:
    """
    Analyze Shopify catalog to build store profile.

    Usage:
        analyzer = StoreProfileAnalyzer(store_id="shop.myshopify.com")
        profile = analyzer.analyze(shopify_products)
    """

    # Confidence thresholds from CONTEXT.md
    CATALOG_SIZE_HIGH = 50      # High confidence, catalog-first
    CATALOG_SIZE_MEDIUM = 10    # Medium confidence, hybrid
    # Below 10 = low confidence, questionnaire-primary

    def __init__(
        self,
        store_id: str,
        language: str = "de",
        country: str = "AT"
    ):
        """
        Initialize analyzer.

        Args:
            store_id: Shopify store identifier
            language: Primary language code
            country: Country code
        """
        self.store_id = store_id
        self.language = language
        self.country = country

    def analyze(
        self,
        products: list[dict],
        existing_profile: Optional[StoreProfile] = None
    ) -> StoreProfile:
        """
        Analyze Shopify products and create store profile.

        Args:
            products: List of Shopify product dicts
            existing_profile: Optional existing profile to update

        Returns:
            StoreProfile with detected intelligence
        """
        catalog_size = len(products)
        logger.info(f"Analyzing catalog with {catalog_size} products")

        # Determine confidence level based on catalog size
        if catalog_size >= self.CATALOG_SIZE_HIGH:
            confidence_level = "high"
            needs_questionnaire = False
        elif catalog_size >= self.CATALOG_SIZE_MEDIUM:
            confidence_level = "medium"
            needs_questionnaire = True  # Fill gaps
        else:
            confidence_level = "low"
            needs_questionnaire = True  # Primary source

        # Extract keywords
        keywords = extract_keywords(
            products,
            top_n=20,
            language="german" if self.language == "de" else "english"
        )
        logger.info(f"Extracted {len(keywords)} keywords")

        # Detect niche
        niche, niche_confidence, niche_evidence = detect_niche(products, keywords)
        logger.info(f"Detected niche: {niche} (confidence: {niche_confidence})")

        # Learn SKU patterns
        sku_patterns = learn_sku_patterns(products)
        logger.info(f"Learned {len(sku_patterns)} SKU patterns")

        # Extract vendors
        vendors_raw = extract_vendors(products)
        known_vendors = [
            KnownVendor(
                name=v['name'],
                sku_pattern=self._infer_vendor_sku_pattern(v, sku_patterns),
                product_count=v['product_count']
            )
            for v in vendors_raw
        ]
        logger.info(f"Found {len(known_vendors)} vendors")

        # Build catalog stats
        categories = self._extract_categories(products)
        catalog_stats = CatalogStats(
            total_products=catalog_size,
            total_vendors=len(known_vendors),
            avg_products_per_vendor=(
                catalog_size / len(known_vendors) if known_vendors else 0
            ),
            most_common_categories=categories
        )

        # Determine discovery settings based on confidence
        discovery_settings = DiscoverySettings(
            require_confirmation_if_confidence_below=0.70,
            reject_vendor_if_niche_mismatch=(confidence_level == "high"),
            allow_cross_niche_products=(confidence_level != "high")
        )

        # Build profile
        profile = StoreProfile(
            store_id=self.store_id,
            created=existing_profile.created if existing_profile else datetime.utcnow(),
            last_updated=datetime.utcnow(),
            niche_primary=niche,
            niche_sub_niches=self._extract_sub_niches(niche, products),
            niche_confidence=niche_confidence,
            language=self.language,
            country=self.country,
            vendor_scope="focused" if confidence_level == "high" else "flexible",
            keywords=keywords[:10],  # Top 10 keywords
            known_vendors=known_vendors,
            catalog_stats=catalog_stats,
            discovery_settings=discovery_settings
        )

        # Add metadata
        profile.content_framework = self._build_content_framework(
            products
        ) if catalog_size >= self.CATALOG_SIZE_HIGH else None

        return profile

    def get_confidence_level(self, catalog_size: int) -> str:
        """Get confidence level string for catalog size."""
        if catalog_size >= self.CATALOG_SIZE_HIGH:
            return "high"
        elif catalog_size >= self.CATALOG_SIZE_MEDIUM:
            return "medium"
        return "low"

    def needs_questionnaire(self, catalog_size: int) -> bool:
        """Check if questionnaire is needed for catalog size."""
        return catalog_size < self.CATALOG_SIZE_HIGH

    def _infer_vendor_sku_pattern(
        self,
        vendor: dict,
        sku_patterns: dict
    ) -> Optional[str]:
        """Infer SKU pattern for a vendor from learned patterns."""
        vendor_name = vendor['name']
        sample_skus = vendor.get('sample_skus', [])

        # Find pattern that matches vendor's SKUs
        for pattern_regex, pattern_data in sku_patterns.items():
            if pattern_data.get('vendor_hint') == vendor_name:
                return pattern_regex

        return None

    def _extract_categories(self, products: list[dict]) -> dict[str, int]:
        """Extract category distribution from products."""
        categories = {}
        for p in products:
            product_type = p.get('product_type', '').strip()
            if product_type:
                categories[product_type] = categories.get(product_type, 0) + 1
        return dict(sorted(categories.items(), key=lambda x: -x[1])[:10])

    def _extract_sub_niches(
        self,
        primary_niche: str,
        products: list[dict]
    ) -> list[str]:
        """Extract sub-niches from product tags and types."""
        sub_niches = set()
        sub_niche_keywords = {
            "arts_and_crafts": [
                "decoupage", "scrapbooking", "painting", "mixed media",
                "card making", "resin art", "furniture upcycling"
            ]
        }

        keywords = sub_niche_keywords.get(primary_niche, [])
        all_text = ' '.join([
            p.get('title', '') + ' ' + ' '.join(p.get('tags', []) or [])
            for p in products
        ]).lower()

        for kw in keywords:
            if kw in all_text:
                sub_niches.add(kw)

        return list(sub_niches)[:5]

    def _build_content_framework(self, products: list[dict]) -> dict:
        """
        Build content framework from catalog patterns.
        Only called for high-confidence catalogs (50+ products).
        """
        # Analyze title patterns
        titles = [p.get('title', '') for p in products if p.get('title')]
        avg_title_length = sum(len(t) for t in titles) / len(titles) if titles else 0

        # Analyze description patterns
        descriptions = [
            p.get('body_html', '') for p in products if p.get('body_html')
        ]
        avg_desc_length = sum(len(d) for d in descriptions) / len(descriptions) if descriptions else 0

        return {
            "title_patterns": {
                "avg_length": int(avg_title_length),
                "sample_count": len(titles)
            },
            "description_patterns": {
                "avg_length": int(avg_desc_length),
                "sample_count": len(descriptions)
            },
            "generated_at": datetime.utcnow().isoformat()
        }
