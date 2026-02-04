import csv
import re
from collections import defaultdict
from pathlib import Path


COLOR_WORDS = {
    "black", "white", "red", "green", "blue", "yellow", "orange", "pink",
    "purple", "violet", "brown", "gray", "grey", "silver", "gold", "beige",
    "ivory", "turquoise", "navy", "teal",
    "schwarz", "weiss", "weiß", "rot", "gruen", "grün", "blau", "gelb",
    "orange", "rosa", "pink", "lila", "violett", "braun", "grau", "silber",
    "gold", "beige", "tuerkis", "türkis",
}


def normalize_color(value: str) -> str:
    if not value:
        return ""
    value = value.strip().lower()
    value = value.replace("weiß", "weiss").replace("grün", "gruen").replace("türkis", "tuerkis")
    return value


def extract_color_words(text: str):
    if not text:
        return []
    tokens = re.split(r"[^\wäöüÄÖÜß]+", text.lower())
    found = []
    for token in tokens:
        if token in COLOR_WORDS:
            found.append(token)
    return sorted(set(found))


def main():
    svse_root = Path("data/svse/galaxy-flakes-15g-juno-rose")
    per_product_path = svse_root / "reports" / "seo_plan_per_product.csv"
    output_path = svse_root / "reports" / "shared_alt_review.csv"

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
            "colors",
            "proposed_filename",
            "proposed_alt",
            "alt_contains_color",
            "color_words_found",
            "note",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for cluster_id, items in clusters.items():
            if not items:
                continue
            is_primary = items[0]["is_primary"]
            colors = sorted({normalize_color(i.get("product_color", "")) for i in items if i.get("product_color")})
            alt = items[0].get("proposed_alt", "")
            found_colors = extract_color_words(alt)
            has_color = bool(found_colors)
            multi_color = len(colors) > 1
            note = ""
            if is_primary == "False" and multi_color and has_color:
                note = "shared cluster with multiple colors; alt mentions color"

            writer.writerow({
                "cluster_id": cluster_id,
                "is_primary": is_primary,
                "product_count": len(items),
                "colors": ", ".join(colors),
                "proposed_filename": items[0].get("proposed_filename", ""),
                "proposed_alt": alt,
                "alt_contains_color": "yes" if has_color else "no",
                "color_words_found": ", ".join(found_colors),
                "note": note,
            })

    print(f"Wrote review: {output_path}")


if __name__ == "__main__":
    main()
