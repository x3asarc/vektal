"""
Hybrid Image Naming System
Combines AI vision accuracy with SEO best practices

RULE:
- Use AI to identify WHAT the image actually shows (type)
- Use SEO naming conventions for STRUCTURE and KEYWORDS
- Result: Accurate + SEO-optimized filenames and alt text

NOTE: This module is now integrated with the Image Framework.
The framework (src/core/image_framework.py) uses these functions
but gets ALL configuration from config/image_processing_rules.yaml.

For new code, prefer using the framework directly:
    from src.core.image_framework import get_framework
    framework = get_framework()
    result = framework.process_image(product, image_url, image_role="primary")
"""

def generate_hybrid_filename(ai_type, seo_template, product_name="galaxy-flakes-15g"):
    """
    Generate filename that combines AI accuracy with SEO structure

    Args:
        ai_type: What AI vision sees (packshot, groupshot, detail, lifestyle)
        seo_template: SEO naming pattern (e.g., pentart-{product}-{type}.jpg)
        product_name: Product identifier

    Returns:
        SEO-optimized filename with accurate type

    Example:
        ai_type = "packshot"
        seo_template = "pentart-galaxy-flakes-15g-detail.jpg"
        → "pentart-galaxy-flakes-15g-packshot.jpg"
    """
    # Extract vendor and product from template
    vendor = "pentart"  # Standard for Pentart products

    # Normalize AI type
    type_mapping = {
        'packshot': 'packshot',
        'groupshot': 'groupshot',
        'detail': 'detail',
        'lifestyle': 'lifestyle',
        'texture': 'detail',  # Texture shots count as details
        'macro': 'detail',
        'close-up': 'detail',
        'other': 'detail'  # Default fallback
    }

    normalized_type = type_mapping.get(ai_type.lower(), 'detail')

    # Build filename with SEO structure + accurate type
    filename = f"{vendor}-{product_name}-{normalized_type}.jpg"

    return filename


def generate_hybrid_alt_text(ai_description, ai_type, seo_keywords, language="de"):
    """
    Generate alt text that combines AI description with SEO keywords

    Args:
        ai_description: What AI sees in the image
        ai_type: Image type from AI
        seo_keywords: SEO keywords to include (product name, features, brand)
        language: Target language ("de" for German, "en" for English)

    Returns:
        SEO-optimized alt text in target language

    Example:
        ai_description = "Jar of pink glitter flakes on white background"
        ai_type = "packshot"
        seo_keywords = ["Galaxy Flakes", "Pentart", "Glitzerflocken", "15g"]
        → "Galaxy Flakes von Pentart - 15g Glitzerflocken - Produktfoto"
    """
    # Type descriptions in German
    type_descriptions_de = {
        'packshot': 'Produktfoto',
        'groupshot': 'Gruppenbild',
        'detail': 'Detailansicht',
        'lifestyle': 'Anwendung',
        'texture': 'Textur-Nahaufnahme'
    }

    type_descriptions_en = {
        'packshot': 'product photo',
        'groupshot': 'group shot',
        'detail': 'detail view',
        'lifestyle': 'lifestyle',
        'texture': 'texture close-up'
    }

    type_desc = type_descriptions_de if language == "de" else type_descriptions_en
    type_label = type_desc.get(ai_type.lower(), type_desc['detail'])

    if language == "de":
        # German alt text structure:
        # {Product} von {Brand} - {Features} - {Type}

        # Extract key elements from AI description
        # Keep it concise but descriptive

        # Build structured alt text
        brand = "Pentart"
        product = seo_keywords[0] if seo_keywords else "Galaxy Flakes"

        # Add specific details from AI if useful
        details = []
        if "verschiedenen farben" in ai_description.lower() or "different colors" in ai_description.lower():
            details.append("verschiedene Farben")
        if "glitter" in ai_description.lower() or "flakes" in ai_description.lower():
            details.append("schillernde Effektflocken")
        if "15g" in str(seo_keywords):
            details.append("15g")

        detail_str = " - ".join(details) if details else "schillernde Dekorfolien"

        alt_text = f"{product} von {brand} - {detail_str} - {type_label}"

    else:
        # English alt text
        brand = "Pentart"
        product = seo_keywords[0] if seo_keywords else "Galaxy Flakes"
        alt_text = f"{product} by {brand} - {type_label}"

    return alt_text


def apply_hybrid_naming(vision_results, seo_plan):
    """
    Apply hybrid naming to all images

    Args:
        vision_results: List of AI vision analysis results
        seo_plan: DataFrame with SEO plan data

    Returns:
        List of dicts with hybrid naming applied
    """
    hybrid_results = []

    for result in vision_results:
        ai_type = result.get('ai_type', 'detail')
        ai_description = result.get('ai_description', '')

        # Get SEO keywords from plan
        seo_keywords = ['Galaxy Flakes', 'Pentart', '15g', 'Glitzerflocken']

        # Generate hybrid filename
        hybrid_filename = generate_hybrid_filename(
            ai_type=ai_type,
            seo_template="pentart-galaxy-flakes-15g-detail.jpg",
            product_name="galaxy-flakes-15g"
        )

        # Generate hybrid alt text
        hybrid_alt = generate_hybrid_alt_text(
            ai_description=ai_description,
            ai_type=ai_type,
            seo_keywords=seo_keywords,
            language="de"
        )

        hybrid_results.append({
            'image_num': result['image_num'],
            'ai_type': ai_type,
            'ai_description': ai_description,
            'hybrid_filename': hybrid_filename,
            'hybrid_alt': hybrid_alt,
            'original_proposed': result.get('proposed_filename'),
            'ai_suggested': result.get('ai_filename')
        })

    return hybrid_results


# RULE SUMMARY
HYBRID_NAMING_RULES = """
HYBRID IMAGE NAMING RULES
==========================

1. FILENAME STRUCTURE
   - Format: {vendor}-{product}-{type}.{ext}
   - Vendor: Always "pentart" for Pentart products
   - Product: "galaxy-flakes-15g" (consistent)
   - Type: FROM AI VISION (packshot, groupshot, detail, lifestyle)
   - Extension: .jpg or .png based on format

2. TYPE DETERMINATION
   - Use AI vision to identify actual content
   - Normalize to standard types:
     * packshot: Product container on plain background
     * groupshot: Multiple products/variants together
     * detail: Close-up of texture, flakes, or application
     * lifestyle: Product in use or styled scene

3. ALT TEXT STRUCTURE (German)
   - Format: {Product} von {Brand} - {Details} - {Type}
   - Product: "Galaxy Flakes" (SEO keyword)
   - Brand: "Pentart" (SEO keyword)
   - Details: Extracted from AI + SEO keywords
   - Type: German translation of image type

4. KEYWORD INTEGRATION
   - Always include: Product name, Brand, Size (15g)
   - Add specific features from AI description
   - Keep concise (60-80 characters optimal)

5. CONSISTENCY
   - Same type = same filename base across products
   - Example: All groupshots = "pentart-galaxy-flakes-15g-groupshot.jpg"
   - But alt text varies by specific content

EXAMPLE APPLICATION:
-------------------
AI sees: "Multiple jars of Galaxy Flakes in different colors"
AI type: groupshot
SEO plan: pentart-galaxy-flakes-15g-detail.jpg

HYBRID OUTPUT:
Filename: pentart-galaxy-flakes-15g-groupshot.jpg
Alt: Galaxy Flakes von Pentart - verschiedene Farben - Gruppenbild

BENEFITS:
- Accurate (AI identifies real content)
- SEO-optimized (consistent structure, keywords)
- User-friendly (descriptive alt text)
- Scalable (same rules for all products)
"""

if __name__ == "__main__":
    print(HYBRID_NAMING_RULES)

    # Example usage
    print("\nEXAMPLE:")
    print("="*60)

    filename = generate_hybrid_filename(
        ai_type="groupshot",
        seo_template="pentart-galaxy-flakes-15g-detail.jpg"
    )

    alt = generate_hybrid_alt_text(
        ai_description="Multiple jars with different colored flakes",
        ai_type="groupshot",
        seo_keywords=["Galaxy Flakes", "Pentart", "15g", "Glitzerflocken"]
    )

    print(f"Filename: {filename}")
    print(f"Alt text: {alt}")
