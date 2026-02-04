"""
CLI tool to test vision AI alt text generation
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
from src.core.vision_cache import VisionAltTextCache, BudgetExceededError
from src.core.vision_client import VisionAIClient
from src.core.image_scraper import validate_alt_text

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="Generate vision AI alt text for product image")
    parser.add_argument("--image-url", required=True, help="Product image URL")
    parser.add_argument("--title", required=True, help="Product title")
    parser.add_argument("--vendor", required=True, help="Vendor/brand name")
    parser.add_argument("--type", default="", help="Product type/category")
    parser.add_argument("--tags", default="", help="Comma-separated tags")
    parser.add_argument("--no-cache", action="store_true", help="Skip cache (force AI generation)")
    parser.add_argument("--stats", action="store_true", help="Show usage statistics")
    args = parser.parse_args()

    cache = VisionAltTextCache()

    if args.stats:
        stats = cache.get_stats()
        print("\n=== Vision AI Usage Statistics ===")
        print(f"Total Processed: {stats['total_processed']}")
        print(f"Cache Hits: {stats['cache_hits']} ({stats['cache_hit_rate']:.1%})")
        print(f"API Calls: {stats['api_calls']}")
        print(f"Total Cost: EUR {stats['total_cost_eur']:.4f}")
        return 0

    # Check cache
    if not args.no_cache:
        cached = cache.get(args.image_url)
        if cached:
            print(f"\n[CACHE HIT] {cached}")
            return 0

    # Generate via AI
    print("\n[CACHE MISS] Calling Vision AI...")
    client = VisionAIClient(
        provider=os.getenv("VISION_AI_PROVIDER", "openrouter"),
        model=os.getenv("VISION_AI_MODEL", "google/gemini-flash-1.5-8b")
    )
    tags = [tag.strip() for tag in args.tags.split(",") if tag.strip()]

    try:
        cache.ensure_within_budget()
        alt_text = client.generate_alt_text(
            image_url=args.image_url,
            product_title=args.title,
            vendor=args.vendor,
            product_type=args.type,
            tags=tags
        )
    except BudgetExceededError as exc:
        print(f"[ERROR] {exc}")
        return 1

    if not alt_text:
        print("[ERROR] Vision AI failed to generate alt text")
        return 1

    # Validate
    validated, warning = validate_alt_text(alt_text)

    print(f"\n[GENERATED] {validated}")
    if warning:
        print(f"[WARNING] {warning}")

    # Cache result
    cache.set(args.image_url, validated, {
        "title": args.title,
        "vendor": args.vendor,
        "product_type": args.type,
        "tags": tags
    }, client.model)

    print("[CACHED] Saved to cache for future use")
    return 0


if __name__ == "__main__":
    sys.exit(main())
