"""Vendor-specific enrichment configuration integration."""

import yaml
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class EnrichmentKeywords:
    """Keywords from vendor YAML section 12"""
    primary: List[str] = field(default_factory=list)
    secondary: List[str] = field(default_factory=list)
    brand: List[str] = field(default_factory=list)
    techniques: List[str] = field(default_factory=list)
    materials: List[str] = field(default_factory=list)


@dataclass
class TaggingRules:
    """Auto-tagging rules from vendor YAML"""
    always_add: List[str] = field(default_factory=list)
    conditional: List[dict] = field(default_factory=list)


@dataclass
class CategoryMapping:
    """Category mapping from vendor YAML section 13"""
    default: str = ""
    product_type_rules: List[dict] = field(default_factory=list)
    collections: dict = field(default_factory=dict)


@dataclass
class ContentTemplates:
    """Content templates from vendor YAML section 14"""
    title: dict = field(default_factory=dict)
    description: dict = field(default_factory=dict)


@dataclass
class SEOConfig:
    """SEO config from vendor YAML section 15"""
    meta_title: dict = field(default_factory=dict)
    meta_description: dict = field(default_factory=dict)
    url_handle: dict = field(default_factory=dict)
    focus_keywords: dict = field(default_factory=dict)


@dataclass
class ImageConfig:
    """Image config from vendor YAML section 16"""
    naming: dict = field(default_factory=dict)
    alt_text: dict = field(default_factory=dict)
    optimization: dict = field(default_factory=dict)


@dataclass
class AttributeExtraction:
    """Attribute extraction config from vendor YAML section 17"""
    extract_from_content: dict = field(default_factory=dict)


class VendorEnrichmentConfig:
    """
    Loads and applies vendor-specific enrichment configuration.

    Uses vendor YAML sections 12-22 (enrichment block).
    """

    def __init__(self, vendor_slug: str = None, config_path: str = None):
        """
        Load vendor enrichment configuration.

        Args:
            vendor_slug: Vendor identifier (e.g., 'pentart', 'itd_collection')
            config_path: Direct path to YAML file (overrides vendor_slug)
        """
        self.vendor_slug = vendor_slug
        self.config_path = config_path or self._find_config_path(vendor_slug)
        self.raw_config: dict = {}

        # Parsed enrichment sections
        self.keywords = EnrichmentKeywords()
        self.tagging = TaggingRules()
        self.categories = CategoryMapping()
        self.templates = ContentTemplates()
        self.seo = SEOConfig()
        self.images = ImageConfig()
        self.attributes = AttributeExtraction()

        if self.config_path and Path(self.config_path).exists():
            self._load_config()

    def _find_config_path(self, vendor_slug: str) -> Optional[str]:
        """Find vendor config file by slug"""
        if not vendor_slug:
            return None

        config_dir = Path('config/vendors')
        if not config_dir.exists():
            return None

        # Try exact match
        exact_path = config_dir / f'{vendor_slug}.yaml'
        if exact_path.exists():
            return str(exact_path)

        # Try case-insensitive match
        for f in config_dir.glob('*.yaml'):
            if f.stem.lower() == vendor_slug.lower():
                return str(f)

        return None

    def _load_config(self):
        """Load and parse vendor YAML config"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.raw_config = yaml.safe_load(f) or {}

        enrichment = self.raw_config.get('enrichment', {})

        # Parse keywords (section 12)
        kw = enrichment.get('keywords', {})
        self.keywords = EnrichmentKeywords(
            primary=kw.get('primary', []),
            secondary=kw.get('secondary', []),
            brand=kw.get('brand', []),
            techniques=kw.get('techniques', []),
            materials=kw.get('materials', [])
        )

        # Parse tagging (section 12 continued)
        tag = enrichment.get('tagging', {})
        self.tagging = TaggingRules(
            always_add=tag.get('always_add', []),
            conditional=tag.get('conditional', [])
        )

        # Parse categories (section 13)
        cat = enrichment.get('categories', {})
        self.categories = CategoryMapping(
            default=cat.get('default', ''),
            product_type_rules=cat.get('product_type_rules', []),
            collections=cat.get('collections', {})
        )

        # Parse templates (section 14)
        tmpl = enrichment.get('content_templates', {})
        self.templates = ContentTemplates(
            title=tmpl.get('title', {}),
            description=tmpl.get('description', {})
        )

        # Parse SEO (section 15)
        seo = enrichment.get('seo', {})
        self.seo = SEOConfig(
            meta_title=seo.get('meta_title', {}),
            meta_description=seo.get('meta_description', {}),
            url_handle=seo.get('url_handle', {}),
            focus_keywords=seo.get('focus_keywords', {})
        )

        # Parse images (section 16)
        img = enrichment.get('images', {})
        self.images = ImageConfig(
            naming=img.get('naming', {}),
            alt_text=img.get('alt_text', {}),
            optimization=img.get('optimization', {})
        )

        # Parse attributes (section 17)
        attr = enrichment.get('attributes', {})
        self.attributes = AttributeExtraction(
            extract_from_content=attr.get('extract_from_content', {})
        )

    def apply_auto_tags(self, product: dict) -> List[str]:
        """
        Apply auto-tagging rules from vendor config.

        Returns list of tags to add.
        """
        tags = list(self.tagging.always_add)

        title = str(product.get('title', '')).lower()

        for rule in self.tagging.conditional:
            condition = rule.get('condition', '')
            add_tags = rule.get('add_tags', [])

            if self._evaluate_condition(condition, title):
                tags.extend(add_tags)

        return list(set(tags))  # Deduplicate

    def _evaluate_condition(self, condition: str, title: str) -> bool:
        """
        Evaluate conditional tag rule.

        Supports: "title contains 'X'" and "title contains 'X' OR title contains 'Y'"
        """
        condition = condition.lower()

        # Handle OR conditions
        if ' or ' in condition:
            parts = condition.split(' or ')
            return any(self._evaluate_condition(p.strip(), title) for p in parts)

        # Handle "title contains 'X'"
        match = re.search(r"title contains ['\"](.+?)['\"]", condition)
        if match:
            keyword = match.group(1).lower()
            return keyword in title

        return False

    def get_product_type(self, product: dict) -> str:
        """
        Determine product_type based on category mapping rules.

        Returns mapped product_type or default.
        """
        title = str(product.get('title', '')).lower()

        for rule in self.categories.product_type_rules:
            match_text = rule.get('match', '').lower()
            product_type = rule.get('product_type', '')

            if match_text and match_text in title:
                return product_type

        return self.categories.default

    def get_collections(self, product: dict) -> List[str]:
        """
        Determine collections for product.

        Returns list of collection names.
        """
        collections = list(self.categories.collections.get('always', []))

        size = product.get('extracted_size', '')
        for rule in self.categories.collections.get('conditional', []):
            condition = rule.get('condition', '')
            rule_collections = rule.get('collections', [])

            # Simple condition evaluation for size
            if 'size ==' in condition:
                match = re.search(r"size == ['\"](.+?)['\"]", condition)
                if match and match.group(1) == size:
                    collections.extend(rule_collections)

        return list(set(collections))

    def enrich_product(self, product: dict) -> dict:
        """
        Apply all enrichment rules to a product.

        Modifies product in place and returns it.
        """
        # Apply auto-tags
        existing_tags = product.get('tags', '')
        if isinstance(existing_tags, str):
            existing_tags = [t.strip() for t in existing_tags.split(',') if t.strip()]
        auto_tags = self.apply_auto_tags(product)
        product['tags'] = ','.join(set(existing_tags + auto_tags))

        # Apply product_type
        if not product.get('product_type'):
            product['product_type'] = self.get_product_type(product)

        # Add vendor keywords
        product['vendor_keywords'] = self.keywords.primary + self.keywords.secondary

        return product


def load_vendor_enrichment_config(vendor_slug: str) -> Optional[VendorEnrichmentConfig]:
    """
    Convenience function to load vendor enrichment config.

    Returns None if config not found.
    """
    config = VendorEnrichmentConfig(vendor_slug=vendor_slug)
    if not config.config_path or not Path(config.config_path).exists():
        return None
    return config


def detect_vendor_from_product(product: dict) -> Optional[str]:
    """
    Detect vendor slug from product data.

    Checks 'vendor' field and normalizes to slug format.
    """
    vendor = product.get('vendor', '')
    if not vendor:
        return None

    # Normalize to slug: lowercase, replace spaces with underscores
    slug = str(vendor).lower().strip()
    slug = re.sub(r'[^a-z0-9]+', '_', slug)
    slug = slug.strip('_')

    return slug
