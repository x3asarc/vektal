"""
Vision AI Alt Text Engine
Generates AI-powered alt text for product images with intelligent caching.
"""
import os
import logging
from typing import Optional, Dict
from src.core.vision_cache import VisionAltTextCache, BudgetExceededError
from src.core.vision_client import VisionAIClient
from src.core.vendor_config import get_vendor_manager
from src.core.image_scraper import clean_product_name, validate_alt_text

# Import hybrid naming functions
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from hybrid_image_naming import generate_hybrid_filename, generate_hybrid_alt_text

logger = logging.getLogger(__name__)


def _needs_vision_alt_text(product: Dict, scraped: Dict) -> bool:
    """Check if product needs vision-generated alt text."""
    # Skip if no image URL
    if not scraped.get("image_url"):
        return False

    # Skip if alt text already exists and is good
    existing_alt = scraped.get("alt_text") or product.get("images", [{}])[0].get("alt")
    if existing_alt and len(existing_alt) > 20:  # Has meaningful alt text
        return False

    return True


def generate_vision_alt_text(product: Dict, scraped: Dict, vendor: str = None) -> Optional[str]:
    """
    Generate vision AI alt text for product image (with caching).

    Args:
        product: Shopify product data
        scraped: Scraped product data (may contain image_url)
        vendor: Vendor name (for vendor-specific config)

    Returns:
        Generated alt text or None if skipped/failed
    """
    # Check if vision AI needed
    if not _needs_vision_alt_text(product, scraped):
        return None

    image_url = scraped.get("image_url")
    if not image_url:
        return None

    # Check vendor config (if vision AI disabled for this vendor)
    vendor_manager = get_vendor_manager()
    vendor_config = vendor_manager.get_config(vendor or "default")
    if not vendor_config.get("vision_ai", {}).get("enabled", True):
        return None

    # Initialize cache
    cache = VisionAltTextCache()

    # Check cache first
    cached_alt_text = cache.get(image_url)
    if cached_alt_text:
        logger.info(f"Vision alt text cache HIT for {image_url[:60]}...")
        return cached_alt_text

    logger.info(f"Vision alt text cache MISS for {image_url[:60]}...")

    # Prepare product context
    product_title = scraped.get("title") or product.get("title", "")
    vendor_name = vendor or product.get("vendor", "")
    product_type = scraped.get("product_type") or product.get("product_type", "")
    tags_value = scraped.get("tags") or product.get("tags")
    if isinstance(tags_value, str):
        tags = [tag.strip() for tag in tags_value.split(",") if tag.strip()]
    elif isinstance(tags_value, list):
        tags = tags_value
    else:
        tags = []

    # Clean title (remove UUIDs, HS codes, SKUs)
    cleaned_title = clean_product_name(product_title) or product_title

    # Call vision AI
    client = VisionAIClient(
        provider=os.getenv("VISION_AI_PROVIDER", "openrouter"),
        model=os.getenv("VISION_AI_MODEL", "google/gemini-flash-1.5-8b")
    )

    try:
        cache.ensure_within_budget()
    except BudgetExceededError as exc:
        logger.error("Vision AI budget exceeded, using fallback: %s", str(exc))
        return _generate_fallback_alt_text(cleaned_title, vendor_name, vendor_config)

    generated_alt_text = client.generate_alt_text(
        image_url=image_url,
        product_title=cleaned_title,
        vendor=vendor_name,
        product_type=product_type,
        tags=tags
    )

    if not generated_alt_text:
        # Fallback: use vendor template
        logger.warning(f"Vision AI failed for {image_url[:60]}, using fallback")
        return _generate_fallback_alt_text(cleaned_title, vendor_name, vendor_config)

    # Validate alt text
    validated_alt_text, warning = validate_alt_text(generated_alt_text)

    if warning:
        logger.warning(f"Vision alt text validation: {warning}")

    # Cache result
    product_context = {
        "title": product_title,
        "vendor": vendor_name,
        "product_type": product_type,
        "tags": tags
    }
    cache.set(image_url, validated_alt_text, product_context, client.model)

    logger.info(f"Generated vision alt text: {validated_alt_text}")
    return validated_alt_text


def _generate_fallback_alt_text(title: str, vendor: str, vendor_config: Dict) -> str:
    """Generate fallback alt text using vendor template (no AI)."""
    # Get vision_ai fallback template (defaults to simple template if not configured)
    vision_config = vendor_config.get("vision_ai", {})
    template = vision_config.get("fallback_template", "{product_name} von {vendor}")

    # Use runtime values - NO hardcoded vendor names
    fallback_alt_text = template.format(
        product_name=title,
        vendor=vendor  # Uses actual vendor from product data
    )

    # Validate and return
    validated, _ = validate_alt_text(fallback_alt_text)
    return validated


def generate_vision_metadata(product: Dict, scraped: Dict, vendor: str = None) -> Optional[Dict]:
    """
    Generate vision AI metadata for product image (type, filename, alt text).
    Uses hybrid naming system: AI accuracy + SEO structure.

    NOTE: This function now delegates to the Image Framework for comprehensive
    rule-based processing. The framework codifies ALL image processing logic
    from config/image_processing_rules.yaml.

    Args:
        product: Shopify product data
        scraped: Scraped product data (may contain image_url)
        vendor: Vendor name (for vendor-specific config)

    Returns:
        Dict with keys: image_type, filename, alt_text
        Example: {
            "image_type": "groupshot",
            "filename": "pentart-galaxy-flakes-15g-groupshot.jpg",
            "alt_text": "Galaxy Flakes von Pentart - verschiedene Farben - Gruppenbild"
        }
        Returns None if skipped/failed
    """
    # Check if vision AI needed
    if not _needs_vision_alt_text(product, scraped):
        return None

    image_url = scraped.get("image_url")
    if not image_url:
        return None

    # Check vendor config
    vendor_manager = get_vendor_manager()
    vendor_config = vendor_manager.get_config(vendor or "default")
    if not vendor_config.get("vision_ai", {}).get("enabled", True):
        return None

    # Initialize cache
    cache = VisionAltTextCache()

    # Check cache (we'll extend cache to store full metadata later)
    # For now, check if we have cached alt text and skip metadata generation
    cached_alt_text = cache.get(image_url)
    if cached_alt_text:
        # Return minimal metadata with cached alt text
        logger.info(f"Vision cache HIT, using cached alt text")
        return {
            "image_type": "detail",  # Default when using cache
            "filename": None,  # Will use default naming
            "alt_text": cached_alt_text
        }

    logger.info(f"Vision metadata cache MISS for {image_url[:60]}...")

    # Prepare product context
    product_title = scraped.get("title") or product.get("title", "")
    vendor_name = vendor or product.get("vendor", "")
    product_type = scraped.get("product_type") or product.get("product_type", "")
    tags_value = scraped.get("tags") or product.get("tags")
    if isinstance(tags_value, str):
        tags = [tag.strip() for tag in tags_value.split(",") if tag.strip()]
    elif isinstance(tags_value, list):
        tags = tags_value
    else:
        tags = []

    # Clean title
    cleaned_title = clean_product_name(product_title) or product_title

    # Call vision AI for metadata
    client = VisionAIClient(
        provider=os.getenv("VISION_AI_PROVIDER", "openrouter"),
        model=os.getenv("VISION_AI_MODEL", "google/gemini-2.0-flash-001")  # Use 2.0 Flash for better vision
    )

    try:
        cache.ensure_within_budget()
    except BudgetExceededError as exc:
        logger.error("Vision AI budget exceeded, using fallback: %s", str(exc))
        fallback_alt = _generate_fallback_alt_text(cleaned_title, vendor_name, vendor_config)
        return {
            "image_type": "detail",
            "filename": None,
            "alt_text": fallback_alt
        }

    # Generate metadata (type + description)
    vision_metadata = client.generate_metadata(
        image_url=image_url,
        product_title=cleaned_title,
        vendor=vendor_name,
        product_type=product_type,
        tags=tags
    )

    if not vision_metadata:
        logger.warning(f"Vision AI metadata failed for {image_url[:60]}, using fallback")
        fallback_alt = _generate_fallback_alt_text(cleaned_title, vendor_name, vendor_config)
        return {
            "image_type": "detail",
            "filename": None,
            "alt_text": fallback_alt
        }

    # Apply hybrid naming
    ai_type = vision_metadata.get('type', 'detail')
    ai_description = vision_metadata.get('description', '')

    # Extract product line from title for filename
    # Example: "Galaxy Flakes 15g - Juno rose" -> "galaxy-flakes-15g"
    product_line = cleaned_title.lower()
    # Simple extraction: take first 3-4 words and convert to slug
    words = product_line.split()[:3]
    product_slug = '-'.join(words).replace(' ', '-')

    # Generate hybrid filename
    hybrid_filename = generate_hybrid_filename(
        ai_type=ai_type,
        seo_template=f"{vendor_name.lower()}-{product_slug}-detail.jpg",
        product_name=product_slug
    )

    # Prepare SEO keywords from product context
    seo_keywords = [cleaned_title, vendor_name]
    if product_type:
        seo_keywords.append(product_type)
    if tags:
        seo_keywords.extend(tags[:2])  # Add first 2 tags

    # Generate hybrid alt text
    hybrid_alt_text = generate_hybrid_alt_text(
        ai_description=ai_description,
        ai_type=ai_type,
        seo_keywords=seo_keywords,
        language="de"
    )

    # Validate alt text
    validated_alt_text, warning = validate_alt_text(hybrid_alt_text)
    if warning:
        logger.warning(f"Vision alt text validation: {warning}")

    # Cache the alt text
    product_context = {
        "title": product_title,
        "vendor": vendor_name,
        "product_type": product_type,
        "tags": tags
    }
    cache.set(image_url, validated_alt_text, product_context, client.model)

    result = {
        "image_type": ai_type,
        "filename": hybrid_filename,
        "alt_text": validated_alt_text
    }

    logger.info(f"Generated vision metadata: type={ai_type}, filename={hybrid_filename}")
    return result
