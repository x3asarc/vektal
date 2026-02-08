"""
Vendor Config Generator

Auto-generates vendor YAML configuration from site reconnaissance.
Uses patterns from template and adapts to specific vendor.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from pathlib import Path

from .vendor_schema import (
    VendorConfig, VendorMeta, VendorIdentity, VendorNiche,
    SKUPattern, VendorURLs, ScrapingConfig, Selectors
)
from .loader import save_vendor_config

logger = logging.getLogger(__name__)


@dataclass
class SiteReconData:
    """Data gathered from site reconnaissance."""
    domain: str
    vendor_name: str
    detected_niche: str

    # Discovered patterns
    sku_patterns: list[dict] = field(default_factory=list)
    url_patterns: dict = field(default_factory=dict)
    selectors: dict = field(default_factory=dict)

    # Site characteristics
    requires_javascript: bool = True
    has_lazy_loading: bool = False
    has_collection_pages: list[str] = field(default_factory=list)

    # Sample products for testing
    sample_products: list[dict] = field(default_factory=list)


@dataclass
class GeneratedConfig:
    """Result of config generation."""
    config: VendorConfig
    yaml_path: Path
    confidence: float
    needs_verification: bool
    warnings: list[str] = field(default_factory=list)
    missing_fields: list[str] = field(default_factory=list)


class VendorConfigGenerator:
    """
    Generate vendor YAML configs from site reconnaissance.

    Usage:
        generator = VendorConfigGenerator()
        result = generator.generate(recon_data)
        generator.save(result)
    """

    # Default selectors to try (in order of likelihood)
    DEFAULT_SELECTOR_ATTEMPTS = {
        'title': [
            'h1.product-title',
            'h1.product__title',
            '[data-product-title]',
            '.product-single__title',
            'h1'
        ],
        'price': [
            '.price__current',
            '.product-price',
            '[data-price]',
            '.price',
            '.product__price'
        ],
        'images': [
            '.product-gallery img',
            '.product__media-gallery img',
            '.product-images img',
            '[data-product-image]',
            '.product-single__photo img'
        ],
        'description': [
            '.product-description',
            '.product__description',
            '[data-description]',
            '.description',
            '.rte'
        ]
    }

    def __init__(self, output_dir: str = "config/vendors"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, recon_data: SiteReconData) -> GeneratedConfig:
        """
        Generate vendor config from reconnaissance data.

        Args:
            recon_data: Site reconnaissance results

        Returns:
            GeneratedConfig with config and metadata
        """
        warnings = []
        missing_fields = []

        # Generate slug from vendor name
        slug = self._to_slug(recon_data.vendor_name)

        # Build config sections
        meta = self._build_meta(recon_data)
        vendor = self._build_vendor(recon_data, slug)
        niche = self._build_niche(recon_data)
        sku_patterns = self._build_sku_patterns(recon_data)
        urls = self._build_urls(recon_data)
        scraping = self._build_scraping(recon_data)
        selectors = self._build_selectors(recon_data)

        # Check for missing required data
        if not sku_patterns:
            warnings.append("No SKU patterns detected - using generic pattern")
            sku_patterns = [SKUPattern(
                name="generic",
                regex=r"^[A-Z0-9-]+$",
                description="Generic alphanumeric pattern",
                examples=[]
            )]

        if not recon_data.url_patterns.get('product_template'):
            missing_fields.append("product_url_template")

        if not any(recon_data.selectors.values()):
            warnings.append("Using default selector attempts - may need manual adjustment")

        # Create config
        config = VendorConfig(
            _meta=meta,
            vendor=vendor,
            niche=niche,
            sku_patterns=sku_patterns,
            urls=urls,
            scraping=scraping,
            selectors=selectors
        )

        # Calculate confidence
        confidence = self._calculate_confidence(recon_data, warnings, missing_fields)

        yaml_path = self.output_dir / f"{slug}.yaml"

        return GeneratedConfig(
            config=config,
            yaml_path=yaml_path,
            confidence=confidence,
            needs_verification=confidence < 0.80 or len(missing_fields) > 0,
            warnings=warnings,
            missing_fields=missing_fields
        )

    def save(self, generated: GeneratedConfig) -> Path:
        """
        Save generated config to YAML file.

        Args:
            generated: GeneratedConfig to save

        Returns:
            Path to saved file
        """
        save_vendor_config(generated.config, generated.yaml_path)
        logger.info(f"Saved vendor config to {generated.yaml_path}")
        return generated.yaml_path

    def _build_meta(self, recon: SiteReconData) -> dict:
        """Build metadata section."""
        return {
            "schema_version": "1.0",
            "version": 1,
            "created": datetime.utcnow().isoformat() + "Z",
            "last_modified": datetime.utcnow().isoformat() + "Z",
            "discovery_method": "auto_inferred",
            "confidence": {
                "overall": 0.0,  # Will be updated
                "scraping": 0.0,
                "enrichment": 0.0
            },
            "verification": {
                "status": "pending",
                "verified_at": None,
                "verified_by": None
            },
            "stats": {
                "total_products_scraped": 0,
                "successful_scrapes": 0,
                "failed_scrapes": 0,
                "success_rate": 0.0
            }
        }

    def _build_vendor(self, recon: SiteReconData, slug: str) -> VendorIdentity:
        """Build vendor identity section."""
        return VendorIdentity(
            name=recon.vendor_name,
            name_short=self._to_short_name(recon.vendor_name),
            slug=slug,
            domain=recon.domain,
            business_type="b2c"
        )

    def _build_niche(self, recon: SiteReconData) -> VendorNiche:
        """Build niche section."""
        return VendorNiche(
            primary=recon.detected_niche or "other"
        )

    def _build_sku_patterns(self, recon: SiteReconData) -> list[SKUPattern]:
        """Build SKU patterns from reconnaissance."""
        patterns = []

        for p in recon.sku_patterns:
            try:
                patterns.append(SKUPattern(
                    name=p.get('name', 'primary'),
                    regex=p.get('regex', r'^[A-Z0-9]+$'),
                    description=p.get('description', 'Auto-detected pattern'),
                    examples=p.get('examples', [])
                ))
            except Exception as e:
                logger.warning(f"Invalid SKU pattern: {e}")

        return patterns

    def _build_urls(self, recon: SiteReconData) -> dict:
        """Build URL templates."""
        product_template = recon.url_patterns.get(
            'product_template',
            f"https://{recon.domain}/products/{{sku_lower}}"
        )

        urls = {
            "product": {
                "template": product_template,
                "fallback_templates": [
                    f"https://{recon.domain}/product/{{sku}}",
                    f"https://{recon.domain}/p/{{sku}}"
                ]
            },
            "search": {
                "template": f"https://{recon.domain}/search?q={{sku}}"
            },
            "collections": [
                {"name": page, "url": page}
                for page in recon.has_collection_pages[:5]
            ]
        }

        return urls

    def _build_scraping(self, recon: SiteReconData) -> dict:
        """Build scraping configuration."""
        primary = "playwright" if recon.requires_javascript else "requests"

        return {
            "strategy": {
                "primary": primary,
                "fallback": ["requests"] if primary == "playwright" else ["playwright"]
            },
            "timing": {
                "page_load_wait_ms": 3000,
                "dynamic_content_wait_ms": 1500 if recon.has_lazy_loading else 500,
                "selector_timeout_ms": 5000
            },
            "rate_limits": {
                "delay_between_requests_ms": 3000,
                "max_concurrent_requests": 2,
                "batch_size": 50
            },
            "retry": {
                "max_attempts": 4,
                "backoff_multiplier": 2.0
            }
        }

    def _build_selectors(self, recon: SiteReconData) -> dict:
        """Build CSS selectors."""
        selectors = {}

        for field, default_attempts in self.DEFAULT_SELECTOR_ATTEMPTS.items():
            detected = recon.selectors.get(field)

            if detected:
                selectors[field] = {
                    "selector": detected,
                    "fallback_selectors": [s for s in default_attempts if s != detected][:3]
                }
            else:
                selectors[field] = {
                    "selector": default_attempts[0],
                    "fallback_selectors": default_attempts[1:4]
                }

        # Special handling for images
        if 'images' in selectors:
            selectors['images']['container'] = '.product-gallery'
            selectors['images']['items'] = 'img'
            selectors['images']['src_attribute'] = 'src'
            selectors['images']['data_attributes'] = ['data-src', 'data-lazy-src']

        return selectors

    def _calculate_confidence(
        self,
        recon: SiteReconData,
        warnings: list,
        missing: list
    ) -> float:
        """Calculate confidence score for generated config."""
        confidence = 1.0

        # Penalty for missing fields
        confidence -= len(missing) * 0.15

        # Penalty for warnings
        confidence -= len(warnings) * 0.1

        # Bonus for detected patterns
        if recon.sku_patterns:
            confidence += 0.1

        # Bonus for collection pages
        if recon.has_collection_pages:
            confidence += 0.05

        # Bonus for sample products
        if recon.sample_products:
            confidence += 0.05

        return max(0.0, min(1.0, round(confidence, 2)))

    def _to_slug(self, name: str) -> str:
        """Convert vendor name to slug."""
        slug = name.lower()
        slug = re.sub(r'[^a-z0-9]+', '_', slug)
        return slug.strip('_')

    def _to_short_name(self, name: str) -> str:
        """Create short name from vendor name."""
        words = name.split()
        if len(words) == 1:
            return name[:3].upper() if len(name) > 3 else name.upper()
        return ''.join(w[0].upper() for w in words[:3])
