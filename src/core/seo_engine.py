import os

from seo.seo_generator import SEOContentGenerator


def _needs_seo_generation(product, scraped):
    if not product:
        return False
    description = scraped.get("description_html") or product.get("description_html")
    seo_title = scraped.get("seo_title") or product.get("seo_title")
    seo_description = scraped.get("seo_description") or product.get("seo_description")
    return not (description and seo_title and seo_description)


def generate_seo_fields(product, scraped, model_id=None):
    if not _needs_seo_generation(product, scraped):
        return {}, {}

    title = scraped.get("title") or product.get("title")
    if not title:
        return {}, {}

    product_data = {
        "title": title,
        "vendor": product.get("vendor") or "",
        "product_type": scraped.get("product_type") or product.get("product_type") or "",
        "tags": scraped.get("tags") or product.get("tags") or [],
        "description_html": scraped.get("description_html") or product.get("description_html") or "",
        "seo_title": product.get("seo_title") or "",
        "seo_description": product.get("seo_description") or "",
    }

    model_id = model_id or os.getenv("SEO_MODEL_ID", "gemini-2.5-flash")
    generator = SEOContentGenerator(model_id=model_id)
    seo_content = generator.generate_seo_content(product_data, quick_mode=True) or {}

    seo_fields = {
        "seo_title": seo_content.get("meta_title"),
        "seo_description": seo_content.get("meta_description"),
        "description_html": seo_content.get("description_html"),
    }

    seo_meta = {
        "fallback": bool(seo_content.get("fallback")),
        "error": seo_content.get("error"),
        "model": model_id,
    }

    return seo_fields, seo_meta
