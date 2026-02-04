"""
CLI test harness for the Vision AI alt text generator.
Usage: python -m vision_ai.test --image ... --title ... --vendor ...
"""
import argparse
import sys

from vision_ai.generator import AltTextGenerator
from vision_ai.cache import VisionAltTextCache, BudgetExceededError


def main():
    parser = argparse.ArgumentParser(description="Vision AI alt text generator test")
    parser.add_argument("--image", required=True, help="Product image URL")
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

    if not args.no_cache:
        cached = cache.get(args.image)
        if cached:
            print(f"\n[CACHE HIT] {cached}")
            return 0

    generator = AltTextGenerator()
    tags = [tag.strip() for tag in args.tags.split(",") if tag.strip()]
    context = {
        "title": args.title,
        "vendor": args.vendor,
        "product_type": args.type,
        "tags": tags,
    }

    try:
        alt_text = generator.generate(args.image, context)
    except BudgetExceededError as exc:
        print(f"[ERROR] {exc}")
        return 1

    print(f"\n[GENERATED] {alt_text}")
    print("[CACHED] Saved to cache for future use")
    return 0


if __name__ == "__main__":
    sys.exit(main())
