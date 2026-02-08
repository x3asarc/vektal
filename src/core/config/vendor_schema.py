"""Pydantic schemas for vendor YAML configuration validation.

Matches the 22-section vendor template structure from config/vendors/_template.yaml.
Provides type-safe validation for vendor discovery, scraping, and enrichment configuration.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Optional
import re

from pydantic import BaseModel, Field, field_validator, model_validator


# ============================================================================
# SECTION 1: METADATA
# ============================================================================

class VerificationCheck(BaseModel):
    """Results from a single verification check."""
    status: str = Field(description="passed | failed | warning")
    tested: Optional[int] = None
    passed: Optional[int] = None
    failed: Optional[int] = None
    warnings: Optional[int] = None
    details: Optional[str] = None
    issues: Optional[list[dict[str, Any]]] = None
    sample_results: Optional[list[dict[str, Any]]] = None
    requires_javascript: Optional[bool] = None
    requires_cookies: Optional[bool] = None
    cloudflare_detected: Optional[bool] = None


class UserPrompt(BaseModel):
    """User prompt shown during verification."""
    prompt_id: str
    question: str
    options: list[str]
    user_response: Optional[str] = None
    user_input: Optional[str] = None
    responded_at: Optional[datetime] = None


class PendingIssue(BaseModel):
    """Unresolved issue needing user input."""
    issue_id: str
    severity: str
    question: str
    required: bool
    user_resolved: bool = False


class VendorVerification(BaseModel):
    """LLM verification results after auto-generation."""
    status: str = Field(default="pending", description="pending | verified | failed | needs_review")
    verified_at: Optional[datetime] = None
    verified_by: Optional[str] = Field(default=None, description="Model used (e.g., gemini-flash)")
    overall_score: float = Field(default=0.0, ge=0.0, le=1.0)

    checks: dict[str, VerificationCheck] = Field(default_factory=dict)
    recommendations: list[str] = Field(default_factory=list)
    user_prompts: list[UserPrompt] = Field(default_factory=list)
    pending_issues: list[PendingIssue] = Field(default_factory=list)
    user_notes: Optional[str] = None


class Confidence(BaseModel):
    """Confidence tracking for auto-inferred config."""
    overall: float = Field(default=0.85, ge=0.0, le=1.0)
    scraping: float = Field(default=0.90, ge=0.0, le=1.0)
    enrichment: float = Field(default=0.80, ge=0.0, le=1.0)


class Stats(BaseModel):
    """Performance statistics."""
    total_products_scraped: int = 0
    successful_scrapes: int = 0
    failed_scrapes: int = 0
    success_rate: float = 0.0
    avg_scrape_time_ms: int = 0
    total_products_enriched: int = 0
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None


class ChangelogEntry(BaseModel):
    """Version history entry."""
    version: int
    date: str
    author: str = Field(description="system | user:{email}")
    changes: str


class VendorMeta(BaseModel):
    """Metadata for tracking, versioning, and performance monitoring."""
    schema_version: str = "1.0"
    version: int = 1
    created: datetime = Field(default_factory=lambda: datetime.now())
    last_modified: datetime = Field(default_factory=lambda: datetime.now())
    last_verified: Optional[datetime] = None
    discovery_method: str = Field(default="auto_inferred", description="auto_inferred | manual | hybrid")

    confidence: Confidence = Field(default_factory=Confidence)
    verification: VendorVerification = Field(default_factory=VendorVerification)
    stats: Stats = Field(default_factory=Stats)
    changelog: list[ChangelogEntry] = Field(default_factory=list)


# ============================================================================
# SECTION 2: VENDOR IDENTITY
# ============================================================================

class ContactInfo(BaseModel):
    """Vendor contact information."""
    website: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class Branding(BaseModel):
    """Brand assets for rich content."""
    logo_url: Optional[str] = None
    brand_color: Optional[str] = None


class VendorIdentity(BaseModel):
    """Core vendor information for identification."""
    name: str = Field(description="Full display name")
    name_short: str = Field(description="Abbreviated name for filenames")
    slug: str = Field(description="Lowercase with underscores")

    domain: str = Field(description="Primary domain (no protocol)")
    domains_alt: list[str] = Field(default_factory=list)
    country: str = Field(default="PL", description="ISO country code")
    language: str = Field(default="en", description="Primary site language")

    business_type: str = Field(default="b2c", description="b2c | b2b | hybrid")
    requires_login: bool = False
    wholesale_available: bool = False

    contact: Optional[ContactInfo] = None
    branding: Optional[Branding] = None


# ============================================================================
# SECTION 3: NICHE & CATEGORIZATION
# ============================================================================

class VendorNiche(BaseModel):
    """Vendor's market positioning for niche matching."""
    primary: str = Field(description="arts_and_crafts, automotive, electronics, etc.")
    sub_categories: list[str] = Field(default_factory=list)
    product_types: list[str] = Field(default_factory=list)
    techniques: list[str] = Field(default_factory=list)


# ============================================================================
# SECTION 4: SKU PATTERNS
# ============================================================================

class SKUPattern(BaseModel):
    """SKU format pattern with regex validation."""
    name: str
    regex: str
    description: str
    examples: list[str] = Field(default_factory=list)
    confidence_boost: float = Field(default=0.30, ge=0.0, le=1.0)
    extract_info: Optional[dict[str, bool]] = None

    @field_validator('regex')
    @classmethod
    def validate_regex_compiles(cls, v: str) -> str:
        """Ensure regex pattern is valid."""
        try:
            re.compile(v)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")
        return v


# ============================================================================
# SECTION 5: SIZE & VARIANT ENCODING
# ============================================================================

class SizeEncoding(BaseModel):
    """Size encoding in SKUs."""
    enabled: bool = True
    method: str = Field(default="suffix", description="suffix | prefix | separate_field")
    default: str = "A4"
    mappings: dict[str, str] = Field(default_factory=dict)


class SizeVariant(BaseModel):
    """Size and variant configuration."""
    size_encoding: SizeEncoding = Field(default_factory=SizeEncoding)
    size_display: dict[str, str] = Field(default_factory=dict)
    variant_strategy: str = Field(default="separate_products", description="separate_products | shopify_variants")


# ============================================================================
# SECTION 6: URL TEMPLATES
# ============================================================================

class ProductURL(BaseModel):
    """Product URL template."""
    template: str
    fallback_templates: list[str] = Field(default_factory=list)

    @field_validator('template')
    @classmethod
    def validate_sku_placeholder(cls, v: str) -> str:
        """Ensure template contains SKU placeholder."""
        if '{sku' not in v.lower():
            raise ValueError("Product URL template must contain {sku} placeholder (e.g., {sku}, {sku_lower}, {sku_upper})")
        return v


class SearchURL(BaseModel):
    """Search URL configuration."""
    template: str
    results_selector: Optional[str] = None


class CollectionURL(BaseModel):
    """Collection page URL."""
    name: str
    url: str
    filter_size: Optional[str] = None


class URLNormalization(BaseModel):
    """URL normalization rules."""
    lowercase_sku: bool = True
    strip_size_suffix: bool = False
    replace_chars: dict[str, str] = Field(default_factory=dict)


class VendorURLs(BaseModel):
    """URL templates for products and collections."""
    product: dict[str, Any] = Field(description="ProductURL as dict")
    search: Optional[dict[str, Any]] = None
    collections: list[dict[str, Any]] = Field(default_factory=list)
    normalization: Optional[URLNormalization] = None

    @model_validator(mode='after')
    def validate_product_template(self):
        """Ensure product template has SKU placeholder."""
        template = self.product.get('template', '')
        if '{sku' not in template.lower():
            raise ValueError("Product URL template must contain {sku} placeholder")
        return self


# ============================================================================
# SECTION 7: SCRAPING STRATEGY
# ============================================================================

class StrategyConfig(BaseModel):
    """Scraping strategy configuration."""
    primary: str = Field(description="playwright | selenium | requests")
    fallback: list[str] = Field(default_factory=list)
    discovery: str = Field(default="firecrawl")


class BrowserConfig(BaseModel):
    """Browser configuration."""
    headless: bool = True
    viewport: dict[str, int] = Field(default_factory=lambda: {"width": 1920, "height": 1080})
    user_agent: Optional[str] = None
    locale: str = "de-AT"
    timezone: str = "Europe/Vienna"


class TimingConfig(BaseModel):
    """Page timing configuration."""
    page_load_wait_ms: int = 3000
    dynamic_content_wait_ms: int = 1500
    selector_timeout_ms: int = 5000


class RateLimits(BaseModel):
    """Rate limiting configuration."""
    delay_between_requests_ms: int = 3000
    delay_jitter_ms: int = 1000
    max_concurrent_requests: int = 2
    batch_size: int = 50
    batch_delay_ms: int = 10000


class RetryConfig(BaseModel):
    """Retry configuration."""
    max_attempts: int = 4
    backoff_multiplier: float = 2.0
    initial_delay_ms: int = 1000
    max_delay_ms: int = 30000


class RateLimitDetection(BaseModel):
    """Rate limit detection configuration."""
    status_codes: list[int] = Field(default_factory=lambda: [429, 503])
    body_patterns: list[str] = Field(default_factory=list)
    cooldown_ms: int = 60000


class ScrapingConfig(BaseModel):
    """Technical configuration for scraping."""
    strategy: StrategyConfig = Field(default_factory=StrategyConfig)
    strategy_reason: Optional[str] = None
    browser: BrowserConfig = Field(default_factory=BrowserConfig)
    timing: TimingConfig = Field(default_factory=TimingConfig)
    rate_limits: RateLimits = Field(default_factory=RateLimits)
    retry: RetryConfig = Field(default_factory=RetryConfig)
    rate_limit_detection: RateLimitDetection = Field(default_factory=RateLimitDetection)


# ============================================================================
# SECTION 8: CSS SELECTORS
# ============================================================================

class ImageSelectors(BaseModel):
    """Image extraction selectors."""
    container: str
    items: str
    src_attribute: str = "src"
    srcset_attribute: Optional[str] = "srcset"
    data_attributes: list[str] = Field(default_factory=list)
    fallback_selectors: list[str] = Field(default_factory=list)


class FieldSelector(BaseModel):
    """Generic field selector with fallbacks."""
    selector: str
    fallback_selectors: list[str] = Field(default_factory=list)


class PriceSelector(BaseModel):
    """Price selector with parsing rules."""
    selector: str
    fallback_selectors: list[str] = Field(default_factory=list)
    parsing: Optional[dict[str, str]] = None


class DescriptionSelector(BaseModel):
    """Description selector with extraction mode."""
    selector: str
    fallback_selectors: list[str] = Field(default_factory=list)
    extract_as: str = Field(default="html", description="text | html | markdown")


class AvailabilitySelector(BaseModel):
    """Stock/availability selector."""
    selector: str
    in_stock_patterns: list[str] = Field(default_factory=list)
    out_of_stock_patterns: list[str] = Field(default_factory=list)


class Selectors(BaseModel):
    """CSS selectors for product data extraction."""
    images: dict[str, Any]
    title: Optional[dict[str, Any]] = None
    price: Optional[dict[str, Any]] = None
    description: Optional[dict[str, Any]] = None
    sku: Optional[dict[str, Any]] = None
    availability: Optional[dict[str, Any]] = None
    additional: dict[str, dict[str, str]] = Field(default_factory=dict)


# ============================================================================
# SECTION 9: VALIDATION RULES
# ============================================================================

class SKUValidation(BaseModel):
    """SKU validation rules."""
    must_match_input: bool = True
    normalize_before_compare: bool = True
    allowed_variations: list[str] = Field(default_factory=list)


class ImageValidation(BaseModel):
    """Image validation rules."""
    min_count: int = 1
    max_count: int = 10
    min_width_px: int = 400
    min_height_px: int = 400
    max_file_size_mb: int = 10
    allowed_formats: list[str] = Field(default_factory=lambda: ["jpg", "jpeg", "png", "webp"])
    reject_placeholders: bool = True
    placeholder_patterns: list[str] = Field(default_factory=list)


class ContentValidation(BaseModel):
    """Content validation rules."""
    min_title_length: int = 5
    max_title_length: int = 200
    min_description_length: int = 20
    required_fields: list[str] = Field(default_factory=list)


class ValidationRules(BaseModel):
    """Data quality validation rules."""
    sku: Optional[SKUValidation] = None
    images: Optional[ImageValidation] = None
    content: Optional[ContentValidation] = None


# ============================================================================
# SECTION 10: VENDOR-SPECIFIC QUIRKS
# ============================================================================

class PreScrapeAction(BaseModel):
    """Action to perform before scraping."""
    action: str = Field(description="click | scroll | wait")
    selector: Optional[str] = None
    direction: Optional[str] = None
    amount_px: Optional[int] = None
    duration_ms: Optional[int] = None
    wait_after_ms: int = 1000


class KnownIssue(BaseModel):
    """Known issue and workaround."""
    issue: str
    workaround: str


class VendorQuirks(BaseModel):
    """Special behaviors and workarounds."""
    cloudflare_protected: bool = False
    captcha_protected: bool = False
    requires_cookies_accept: bool = False
    lazy_loads_images: bool = True
    infinite_scroll: bool = False
    requires_javascript: bool = True
    pre_scrape_actions: list[PreScrapeAction] = Field(default_factory=list)
    known_issues: list[KnownIssue] = Field(default_factory=list)


# ============================================================================
# SECTION 11: GSD OPTIMIZATION (Direct URL Mappings)
# ============================================================================

class GSDMappings(BaseModel):
    """Pre-mapped SKU to URL relationships for fast scraping."""
    enabled: bool = True
    auto_populate: bool = True
    last_discovery_run: Optional[datetime] = None
    discovery_source: Optional[str] = Field(default=None, description="firecrawl | sitemap | manual")
    total_mapped_skus: int = 0
    mappings: dict[str, str] = Field(default_factory=dict, description="SKU: URL mappings")


# ============================================================================
# SECTIONS 12-22: PRODUCT ENRICHMENT CONFIGURATION
# ============================================================================

class EnrichmentKeywords(BaseModel):
    """Keywords for product tagging."""
    primary: list[str] = Field(default_factory=list)
    secondary: list[str] = Field(default_factory=list)
    brand: list[str] = Field(default_factory=list)
    techniques: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)


class ConditionalTag(BaseModel):
    """Conditional tagging rule."""
    condition: str
    add_tags: list[str]


class EnrichmentTagging(BaseModel):
    """Automatic tag generation rules."""
    always_add: list[str] = Field(default_factory=list)
    conditional: list[ConditionalTag] = Field(default_factory=list)


class ProductTypeRule(BaseModel):
    """Product type mapping rule."""
    match: str
    product_type: str


class CollectionRule(BaseModel):
    """Conditional collection assignment."""
    condition: str
    collections: list[str]


class EnrichmentCategories(BaseModel):
    """Category and collection mapping."""
    default: str = "Uncategorized"
    product_type_rules: list[ProductTypeRule] = Field(default_factory=list)
    collections: Optional[dict[str, Any]] = None


class TemplateSection(BaseModel):
    """Content template section."""
    template: Optional[str] = None
    format: Optional[str] = None
    bullet_char: Optional[str] = None
    items: list[str] = Field(default_factory=list)


class ContentTemplates(BaseModel):
    """Product content formatting templates."""
    title: Optional[dict[str, Any]] = None
    description: Optional[dict[str, Any]] = None


class SEOConfig(BaseModel):
    """SEO optimization templates."""
    meta_title: Optional[dict[str, Any]] = None
    meta_description: Optional[dict[str, Any]] = None
    url_handle: Optional[dict[str, Any]] = None
    focus_keywords: Optional[dict[str, Any]] = None


class ImageNaming(BaseModel):
    """Image file naming convention."""
    pattern: str
    vendor_short: str
    lowercase: bool = True
    index_start: int = 1
    examples: list[str] = Field(default_factory=list)


class AltTextConfig(BaseModel):
    """Alt text template."""
    template: str
    max_length: int = 125
    include_sku: bool = False
    examples: list[str] = Field(default_factory=list)


class ImageOptimization(BaseModel):
    """Image optimization settings."""
    max_width: int = 2048
    max_height: int = 2048
    quality: int = 85
    format: str = "jpg"
    strip_metadata: bool = True


class ImageEnrichment(BaseModel):
    """Image naming, tagging, and optimization."""
    naming: Optional[ImageNaming] = None
    alt_text: Optional[AltTextConfig] = None
    optimization: Optional[ImageOptimization] = None


class ExtractionPattern(BaseModel):
    """Pattern for extracting attributes."""
    pattern: str
    value: str


class AttributeExtractor(BaseModel):
    """Attribute extraction configuration."""
    enabled: bool = True
    patterns: list[ExtractionPattern] = Field(default_factory=list)


class AttributeExtraction(BaseModel):
    """Attribute extraction from content."""
    extract_from_content: dict[str, AttributeExtractor] = Field(default_factory=dict)
    defaults: dict[str, Any] = Field(default_factory=dict)


class MarkupConfig(BaseModel):
    """Price markup configuration."""
    enabled: bool = False
    percentage: float = 0
    round_to: float = 0.01


class PriceDisplay(BaseModel):
    """Price display settings."""
    include_tax: bool = True
    tax_rate: float = 20
    show_compare_at: bool = False


class PricingRules(BaseModel):
    """Pricing configuration."""
    source_currency: str = "EUR"
    markup: Optional[MarkupConfig] = None
    display: Optional[PriceDisplay] = None


class QualityWeights(BaseModel):
    """Quality scoring weights."""
    title_quality: int = 15
    description_length: int = 25
    description_keywords: int = 15
    images_count: int = 15
    images_quality: int = 10
    attributes_completeness: int = 10
    seo_optimization: int = 10


class QualityThresholds(BaseModel):
    """Quality score thresholds."""
    minimum_acceptable: int = 50
    good: int = 70
    excellent: int = 85


class QualityScoring(BaseModel):
    """Product quality scoring configuration."""
    weights: QualityWeights = Field(default_factory=QualityWeights)
    thresholds: QualityThresholds = Field(default_factory=QualityThresholds)
    requirements: dict[str, list[str]] = Field(default_factory=dict)


class RelatedProductStrategy(BaseModel):
    """Related product matching strategy."""
    name: str
    weight: float
    description: str


class RelatedProducts(BaseModel):
    """Related product suggestions."""
    enabled: bool = True
    strategies: list[RelatedProductStrategy] = Field(default_factory=list)
    complements: dict[str, list[str]] = Field(default_factory=dict)
    display: dict[str, Any] = Field(default_factory=dict)


class MinimumOrder(BaseModel):
    """Minimum order configuration."""
    enabled: bool = False
    amount: float = 0
    currency: str = "EUR"


class StockHandling(BaseModel):
    """Stock handling configuration."""
    assume_in_stock: bool = True
    low_stock_threshold: int = 5


class DiscontinuedHandling(BaseModel):
    """Discontinued product handling."""
    check_for_discontinued: bool = True
    discontinued_patterns: list[str] = Field(default_factory=list)
    action: str = Field(default="mark_draft", description="mark_draft | archive | delete")


class BusinessRules(BaseModel):
    """Vendor-specific business rules."""
    minimum_order: Optional[MinimumOrder] = None
    stock: Optional[StockHandling] = None
    discontinued: Optional[DiscontinuedHandling] = None
    special: list[dict[str, str]] = Field(default_factory=list)


class Webhooks(BaseModel):
    """Webhook configuration."""
    on_new_product: Optional[str] = None
    on_price_change: Optional[str] = None
    on_stock_change: Optional[str] = None


class ExternalData(BaseModel):
    """External data source configuration."""
    catalog_csv: Optional[str] = None
    catalog_sku_column: str = "sku"
    barcode_lookup: bool = True


class Integrations(BaseModel):
    """External integrations and webhooks."""
    webhooks: Optional[Webhooks] = None
    external_data: Optional[ExternalData] = None


class Enrichment(BaseModel):
    """All product enrichment configuration."""
    keywords: Optional[EnrichmentKeywords] = None
    tagging: Optional[EnrichmentTagging] = None
    categories: Optional[EnrichmentCategories] = None
    content_templates: Optional[ContentTemplates] = None
    seo: Optional[SEOConfig] = None
    images: Optional[ImageEnrichment] = None
    attributes: Optional[AttributeExtraction] = None
    pricing: Optional[PricingRules] = None
    quality: Optional[QualityScoring] = None
    related_products: Optional[RelatedProducts] = None
    business_rules: Optional[BusinessRules] = None
    integrations: Optional[Integrations] = None


# ============================================================================
# ROOT MODEL: VENDOR CONFIG
# ============================================================================

class VendorConfig(BaseModel):
    """Complete vendor configuration matching _template.yaml structure.

    Combines all 22 sections for vendor scraping and product enrichment.
    """

    # Core configuration (Sections 1-11: Scraping)
    meta: VendorMeta = Field(default_factory=VendorMeta, alias="_meta")
    vendor: VendorIdentity
    niche: VendorNiche
    sku_patterns: list[SKUPattern]
    variants: Optional[SizeVariant] = None
    urls: VendorURLs
    scraping: Optional[ScrapingConfig] = None
    selectors: Selectors
    validation: Optional[ValidationRules] = None
    quirks: Optional[VendorQuirks] = None
    gsd_mappings: Optional[GSDMappings] = None

    # Enrichment configuration (Sections 12-22)
    enrichment: Optional[Enrichment] = None

    model_config = {
        'populate_by_name': True,
        'str_strip_whitespace': True,
    }

    @model_validator(mode='after')
    def validate_cross_fields(self):
        """Cross-field validation."""
        # Ensure at least one SKU pattern exists
        if not self.sku_patterns:
            raise ValueError("At least one SKU pattern is required")

        return self
