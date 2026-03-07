"""
Product completeness scoring engine (Phase 17.1).

Calculates percentage-based completeness scores and SEO readiness
based on tracked fields and presence semantics.
"""
from typing import Dict, List, Any
from decimal import Decimal
from src.models.product import Product

# CRITICAL_FIELDS: Basic requirements for a product to be "healthy"
CRITICAL_FIELDS = [
    'title', 'description', 'price', 'vendor_code', 
    'product_type', 'image_count'
]

# OPERATIONAL_FIELDS: Pricing, warehouse, and logistic data
OPERATIONAL_FIELDS = [
    'sku', 'barcode', 'cost', 'compare_at_price', 
    'weight_kg', 'hs_code', 'country_of_origin'
]

# SEO_FIELDS: Metadata and search optimization
SEO_FIELDS = [
    'seo_title', 'seo_description', 'tags', 
    'collections_json', 'metafields_json', 'alt_text_count'
]

def is_present(value: Any) -> bool:
    """Presence semantics: Not None and non-empty."""
    if value is None:
        return False
    if isinstance(value, (str, list, dict)):
        return len(value) > 0
    if isinstance(value, (int, float, Decimal)):
        # For price/cost, 0 is allowed but usually implies missing data 
        # for catalog health purposes unless it's a gift/promo.
        # Here we consider it present if not None.
        return True
    return bool(value)

def calculate_completeness(product: Product) -> Dict[str, Any]:
    """
    Calculate completeness score across different tiers.
    
    Returns:
        Dict with scores and list of missing fields.
    """
    missing_critical = []
    missing_operational = []
    missing_seo = []
    
    # Enrichment and Images are handled separately
    enrichment = product.enrichment
    images = product.images
    
    # 1. Check Critical
    for field in CRITICAL_FIELDS:
        if field == 'image_count':
            if not images:
                missing_critical.append('images')
            continue
        
        val = getattr(product, field, None)
        if not is_present(val):
            missing_critical.append(field)
            
    # 2. Check Operational
    for field in OPERATIONAL_FIELDS:
        val = getattr(product, field, None)
        if not is_present(val):
            missing_operational.append(field)
            
    # 3. Check SEO
    for field in SEO_FIELDS:
        if field == 'seo_title':
            val = enrichment.seo_title if enrichment else None
        elif field == 'seo_description':
            val = enrichment.seo_description if enrichment else None
        elif field == 'alt_text_count':
            # Check if all active images have alt text
            val = all(is_present(img.alt_text) for img in images if img.is_active) if images else False
        else:
            val = getattr(product, field, None)
            
        if not is_present(val):
            missing_seo.append(field)

    # Calculate percentages
    total_fields = len(CRITICAL_FIELDS) + len(OPERATIONAL_FIELDS) + len(SEO_FIELDS)
    missing_total = len(missing_critical) + len(missing_operational) + len(missing_seo)
    
    completeness_score = round(((total_fields - missing_total) / total_fields) * 100, 1)
    critical_fill_rate = round(((len(CRITICAL_FIELDS) - len(missing_critical)) / len(CRITICAL_FIELDS)) * 100, 1)
    
    # SEO Readiness: Requires all critical + specific SEO set
    seo_readiness = (
        len(missing_critical) == 0 and 
        is_present(enrichment.seo_title if enrichment else None) and
        is_present(enrichment.seo_description if enrichment else None)
    )

    return {
        "completeness_score": completeness_score,
        "critical_fill_rate": critical_fill_rate,
        "is_seo_ready": seo_readiness,
        "missing_critical": missing_critical,
        "missing_operational": missing_operational,
        "missing_seo": missing_seo,
        "field_stats": {
            "critical_total": len(CRITICAL_FIELDS),
            "critical_filled": len(CRITICAL_FIELDS) - len(missing_critical),
            "operational_total": len(OPERATIONAL_FIELDS),
            "operational_filled": len(OPERATIONAL_FIELDS) - len(missing_operational),
            "seo_total": len(SEO_FIELDS),
            "seo_filled": len(SEO_FIELDS) - len(missing_seo)
        }
    }
