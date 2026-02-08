"""
Local Pattern Matcher

Stage 1 of discovery pipeline: instant, free pattern matching.
No API calls - purely local regex matching against known vendor patterns.
"""

import re
import logging
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

from src.core.config import load_vendor_config, list_vendor_configs
from src.core.config.store_profile_schema import StoreProfile
from .sku_validator import normalize_sku, extract_sku_info

logger = logging.getLogger(__name__)


@dataclass
class PatternMatchResult:
    """Result of pattern matching."""
    matched: bool
    vendor_name: Optional[str]
    vendor_slug: Optional[str]
    confidence: float  # 0.0 to 1.0
    pattern_matched: Optional[str]
    method: str = "local_pattern"

    # Additional context
    sku_info: Optional[dict] = None
    requires_confirmation: bool = False
    message: Optional[str] = None


class LocalPatternMatcher:
    """
    Match SKUs against known vendor patterns.

    Flow:
    1. Check store profile's known vendors first (highest priority)
    2. Check all vendor config files
    3. Return best match with confidence

    Confidence scores:
    - 0.90+: High confidence, can auto-proceed
    - 0.70-0.90: Medium confidence, suggest confirmation
    - <0.70: Low confidence, require confirmation
    """

    # Built-in patterns for common vendors (fallback if no YAML)
    BUILTIN_PATTERNS = {
        'itd_collection': {
            'name': 'ITD Collection',
            'patterns': [
                (r'^R\d{4}[A-Z]?$', 0.95, 'Standard rice paper (R####)'),
                (r'^RP\d{4}[A-Z]?$', 0.95, 'Premium rice paper (RP####)'),
            ]
        },
        'pentart': {
            'name': 'Pentart',
            'patterns': [
                (r'^P[-]?\d{5}$', 0.90, 'Pentart product (P-#####)'),
            ]
        },
        'aisticraft': {
            'name': 'Aisticraft',
            'patterns': [
                (r'^AC\d{4}$', 0.90, 'Aisticraft (AC####)'),
            ]
        },
        'fn_deco': {
            'name': 'FN Deco',
            'patterns': [
                (r'^FN\d{4,5}$', 0.85, 'FN Deco (FN####)'),
            ]
        },
        'paper_designs': {
            'name': 'Paper Designs',
            'patterns': [
                (r'^PD\d{4}$', 0.85, 'Paper Designs (PD####)'),
            ]
        }
    }

    def __init__(
        self,
        vendor_config_dir: str = "config/vendors",
        store_profile: Optional[StoreProfile] = None
    ):
        """
        Initialize pattern matcher.

        Args:
            vendor_config_dir: Directory containing vendor YAML configs
            store_profile: Optional store profile with known vendors
        """
        self.vendor_config_dir = Path(vendor_config_dir)
        self.store_profile = store_profile
        self._vendor_patterns: dict = {}
        self._load_patterns()

    def _load_patterns(self):
        """Load patterns from vendor config files and built-in patterns."""
        # Start with built-in patterns
        self._vendor_patterns = dict(self.BUILTIN_PATTERNS)

        # Load from YAML configs
        try:
            for config_path in list_vendor_configs(self.vendor_config_dir):
                try:
                    config = load_vendor_config(config_path)
                    slug = config.vendor.slug

                    patterns = []
                    for p in config.sku_patterns:
                        boost = p.confidence_boost if hasattr(p, 'confidence_boost') else 0.0
                        patterns.append((
                            p.regex,
                            0.85 + boost,  # Base confidence + boost
                            p.description
                        ))

                    if patterns:
                        self._vendor_patterns[slug] = {
                            'name': config.vendor.name,
                            'patterns': patterns
                        }
                        logger.debug(f"Loaded {len(patterns)} patterns for {config.vendor.name}")

                except Exception as e:
                    logger.warning(f"Could not load vendor config {config_path}: {e}")

        except Exception as e:
            logger.warning(f"Could not load vendor configs: {e}")

        logger.info(f"Loaded patterns for {len(self._vendor_patterns)} vendors")

    def match(self, sku: str) -> PatternMatchResult:
        """
        Match SKU against known vendor patterns.

        Args:
            sku: SKU to match

        Returns:
            PatternMatchResult with best match
        """
        normalized = normalize_sku(sku)
        sku_info = extract_sku_info(sku)

        if not sku_info.is_valid:
            return PatternMatchResult(
                matched=False,
                vendor_name=None,
                vendor_slug=None,
                confidence=0.0,
                pattern_matched=None,
                message=f"Invalid SKU: {', '.join(sku_info.validation_errors)}"
            )

        best_match = None
        best_confidence = 0.0

        # Priority 1: Check store profile's known vendors
        if self.store_profile:
            for known_vendor in self.store_profile.known_vendors:
                if known_vendor.sku_pattern:
                    try:
                        if re.match(known_vendor.sku_pattern, normalized, re.IGNORECASE):
                            # High confidence for store's known vendors
                            confidence = 0.95
                            if confidence > best_confidence:
                                best_match = {
                                    'vendor_name': known_vendor.name,
                                    'vendor_slug': known_vendor.name.lower().replace(' ', '_'),
                                    'pattern': known_vendor.sku_pattern,
                                    'confidence': confidence,
                                    'source': 'store_profile'
                                }
                                best_confidence = confidence
                    except re.error:
                        pass

        # Priority 2: Check all vendor patterns
        for slug, vendor_data in self._vendor_patterns.items():
            for pattern, base_confidence, desc in vendor_data['patterns']:
                try:
                    if re.match(pattern, normalized, re.IGNORECASE):
                        # Boost confidence if in store's known vendors
                        confidence = base_confidence
                        if self.store_profile:
                            known_names = [v.name.lower() for v in self.store_profile.known_vendors]
                            if vendor_data['name'].lower() in known_names:
                                confidence = min(confidence + 0.05, 0.99)

                        if confidence > best_confidence:
                            best_match = {
                                'vendor_name': vendor_data['name'],
                                'vendor_slug': slug,
                                'pattern': pattern,
                                'confidence': confidence,
                                'description': desc,
                                'source': 'vendor_config'
                            }
                            best_confidence = confidence
                except re.error:
                    logger.warning(f"Invalid regex pattern: {pattern}")

        if best_match:
            return PatternMatchResult(
                matched=True,
                vendor_name=best_match['vendor_name'],
                vendor_slug=best_match['vendor_slug'],
                confidence=best_match['confidence'],
                pattern_matched=best_match['pattern'],
                requires_confirmation=best_match['confidence'] < 0.90,
                sku_info={
                    'normalized': sku_info.normalized,
                    'base_sku': sku_info.base_sku,
                    'size_suffix': sku_info.size_suffix,
                    'product_line': sku_info.product_line
                },
                message=f"Matched {best_match['vendor_name']} pattern"
            )

        return PatternMatchResult(
            matched=False,
            vendor_name=None,
            vendor_slug=None,
            confidence=0.0,
            pattern_matched=None,
            sku_info={
                'normalized': sku_info.normalized,
                'base_sku': sku_info.base_sku,
                'product_line': sku_info.product_line
            },
            message="No matching pattern found"
        )

    def get_vendor_patterns(self, vendor_slug: str) -> list[tuple[str, float, str]]:
        """Get all patterns for a specific vendor."""
        vendor = self._vendor_patterns.get(vendor_slug)
        if vendor:
            return vendor['patterns']
        return []

    def list_vendors(self) -> list[str]:
        """List all vendors with loaded patterns."""
        return list(self._vendor_patterns.keys())