"""
Vision AI Prompts for German E-Commerce Alt Text Generation
Generic prompts that work with any vendor/market
"""

# System instruction for vision model (Bastelbedarf focus)
VISION_SYSTEM_INSTRUCTION = """You are an SEO expert for German-language e-commerce stores specializing in Bastelbedarf.

Generate alt text for product images following these rules:

1. **Language**: German (Austria/Germany)
2. **Length**: Maximum 125 characters
3. **Format**: "[Product type] von [Brand] - [Key distinguishing feature]"
4. **Tone**: Natural, descriptive, customer-focused (not robotic keyword stuffing)
5. **SEO**: Include 1-2 relevant search terms naturally
6. **Accessibility**: Describe what's visible in the image for visually impaired users

What to avoid:
- Keyword stuffing
- Generic descriptions like "Product image"
- English words (unless it's a brand name)
- Special characters that break HTML attributes
- Technical codes (SKUs, barcodes, HS codes)

Examples:
- Acrylfarben-Set von Pentart - 12 Metallic-Toene fuer Bastelarbeiten
- Decopatch-Papier Blumenmuster von Paper Designs - 3er Pack
- Holz-Schmuckkaestchen von ITD Collection - unlackiert zum Selbstgestalten

Generate ONE alt text (no explanation, just the text).
"""


def get_vision_prompt(product_title: str, vendor: str, product_type: str = "", tags: list[str] | None = None) -> str:
    """
    Generate vision prompt with product context.

    Args:
        product_title: Product title (German)
        vendor: Brand/vendor name
        product_type: Product category (optional)
        tags: Product tags (optional)

    Returns:
        Formatted prompt string
    """
    prompt = f"""Analyze this product image and generate a descriptive German alt text (max 125 characters).

Product Context:
- Title: {product_title}
- Brand/Vendor: {vendor}
"""

    if product_type:
        prompt += f"- Category: {product_type}\n"
    if tags:
        prompt += f"- Tags: {', '.join(tags)}\n"

    prompt += """
Focus on:
- Visual appearance (colors, materials, textures)
- Product category and key features
- What makes it distinctive

Output: Just the alt text (no explanation)."""

    return prompt


def get_vision_metadata_prompt(product_title: str, vendor: str, product_type: str = "", tags: list[str] | None = None) -> str:
    """
    Generate vision prompt for image metadata (type + description).
    Used for hybrid naming system.

    Args:
        product_title: Product title (German)
        vendor: Brand/vendor name
        product_type: Product category (optional)
        tags: Product tags (optional)

    Returns:
        Formatted prompt string requesting structured metadata
    """
    prompt = f"""Analyze this product image and provide structured metadata.

Product Context:
- Title: {product_title}
- Brand/Vendor: {vendor}
"""

    if product_type:
        prompt += f"- Category: {product_type}\n"
    if tags:
        prompt += f"- Tags: {', '.join(tags)}\n"

    prompt += """
Identify:
1. **Image Type**: Classify as ONE of:
   - packshot: Single product container/jar on plain background
   - groupshot: Multiple products/variants shown together
   - detail: Close-up of texture, flakes, application, or product effect
   - lifestyle: Product in use or styled scene

2. **Description**: Brief description in German (1-2 sentences)

Format your response EXACTLY as:
TYPE: [image_type]
DESCRIPTION: [German description]

Example:
TYPE: groupshot
DESCRIPTION: Mehrere Dosen mit Galaxy Flakes in verschiedenen Farben auf weißem Hintergrund"""

    return prompt
