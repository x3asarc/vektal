"""
Scrape and upload images for 3 Pentart products
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fix_pentart_products import scrape_pentart_image

# Products with their correct SKUs
PRODUCTS = [
    {
        "sku": "40070",
        "title": "Harztönung Jade 20 ml",
        "handle": "harztonung-jade-20-ml",
        "barcode": "5996546033389"
    },
    {
        "sku": "20738",
        "title": "Dekofolie Bronze 14 x 14 cm",
        "handle": "dekofolie-bronze-14-x-14-cm-5-stuck-packung",
        "barcode": "5997412742664"
    },
    {
        "sku": "13397",
        "title": "Textilkleber 80 ml",
        "handle": "textilkleber-80-ml",
        "barcode": "5997412709667"
    }
]

def main():
    print("="*70)
    print("SCRAPING IMAGES FROM PENTACOLOR.EU")
    print("="*70)

    results = []

    for product in PRODUCTS:
        sku = product["sku"]
        title = product["title"]

        print(f"\n{'='*70}")
        print(f"SKU: {sku} - {title}")
        print(f"{'='*70}")

        # Try scraping with SKU
        print(f"  Scraping from pentacolor.eu...")
        image_url = scrape_pentart_image(sku, use_selenium=True)

        if image_url:
            print(f"  OK Found image: {image_url}")
            results.append({
                "sku": sku,
                "title": title,
                "handle": product["handle"],
                "image_url": image_url,
                "success": True
            })
        else:
            print(f"  ERROR No image found")
            results.append({
                "sku": sku,
                "title": title,
                "handle": product["handle"],
                "image_url": None,
                "success": False
            })

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")

    for result in results:
        status = "OK" if result["success"] else "FAILED"
        print(f"{result['sku']}: {status}")
        if result["success"]:
            print(f"  Image: {result['image_url']}")

    successful = sum(1 for r in results if r["success"])
    print(f"\n{successful}/{len(PRODUCTS)} images found")

    # Save results for next step (upload to Shopify)
    import json
    with open("scraped_images_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: scraped_images_results.json")

    print(f"\n{'='*70}")
    print("COMPLETE")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
