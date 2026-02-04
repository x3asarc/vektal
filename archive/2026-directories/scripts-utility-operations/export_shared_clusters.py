import csv
from collections import defaultdict
from pathlib import Path


def main():
    svse_root = Path("data/svse/galaxy-flakes-15g-juno-rose")
    per_product_path = svse_root / "reports" / "seo_plan_per_product.csv"
    output_path = svse_root / "reports" / "shared_clusters_products.csv"

    rows = []
    with open(per_product_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    clusters = defaultdict(list)
    for row in rows:
        clusters[row["cluster_id"]].append(row)

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        fieldnames = [
            "cluster_id",
            "is_primary",
            "product_count",
            "proposed_filename",
            "proposed_alt",
            "product_handles",
            "product_titles",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for cluster_id, items in clusters.items():
            if not items:
                continue
            handles = sorted({i.get("product_handle", "") for i in items if i.get("product_handle")})
            titles = sorted({i.get("product_title", "") for i in items if i.get("product_title")})
            writer.writerow({
                "cluster_id": cluster_id,
                "is_primary": items[0].get("is_primary"),
                "product_count": len(items),
                "proposed_filename": items[0].get("proposed_filename", ""),
                "proposed_alt": items[0].get("proposed_alt", ""),
                "product_handles": " | ".join(handles),
                "product_titles": " | ".join(titles),
            })

    print(f"Wrote report: {output_path}")


if __name__ == "__main__":
    main()
