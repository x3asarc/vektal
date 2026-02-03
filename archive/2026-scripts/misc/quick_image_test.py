import requests
import time

# Known: views_0009 has image ID 3925
# Let's test nearby IDs for the other SKUs

test_cases = {
    "views-0167": range(3920, 3950),
    "views-0084": range(3850, 3930),
    "rc003": range(3900, 4000),
    "rc-003": range(3900, 4000),
}

found = {}

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0"})

for sku, id_range in test_cases.items():
    print(f"\nTesting {sku}...")

    for img_id in id_range:
        # Try common description patterns
        for desc in ["rice-paper-for-the-decoupage", "rice-paper", "views"]:
            url = f"https://paperdesigns.it/{img_id}-superlarge_default/{sku}-{desc}.jpg"

            try:
                r = session.head(url, timeout=3)
                if r.status_code == 200:
                    print(f"  ✓ FOUND: {url}")
                    found[sku] = url
                    break
            except:
                pass

            time.sleep(0.2)

        if sku in found:
            break

    if sku not in found:
        print(f"  ✗ Not found")

print("\n" + "="*70)
print("Results:")
for sku, url in found.items():
    print(f"{sku}: {url}")
