# Color Learning Integration Guide

How to integrate dynamic color learning with store profile analysis (Phase 2.1).

## Overview

When a user first connects their Shopify store:

1. **Phase 2.1**: StoreProfileAnalyzer analyzes catalog
2. **NEW**: ColorLearner extracts all unique colors
3. **Saved**: Colors stored in `data/store_profile.json`
4. **Phase 2.2**: EnrichmentPipeline loads colors automatically

## Integration with StoreProfileAnalyzer

### Step 1: Update StoreProfileAnalyzer

In `universal_vendor_scraper/core/store_analyzer.py` (Phase 2.1):

```python
from src.core.enrichment.color_learning import ColorLearner, save_store_colors

class StoreProfileAnalyzer:
    def analyze_catalog(self, products: List[dict]) -> dict:
        """Analyze Shopify catalog on first connection"""

        # Existing analysis...
        keywords = self._extract_keywords(products)
        niche = self._detect_niche(products)
        sku_patterns = self._learn_sku_patterns(products)

        # NEW: Learn colors from catalog
        color_learner = ColorLearner()
        color_analysis = color_learner.analyze_catalog_colors(products)

        print(f"\nColor Learning Results:")
        print(f"  Base colors: {color_analysis['base_colors']}")
        print(f"  Learned colors: {color_analysis['total_learned']}")
        print(f"  Coverage increase: +{color_analysis['coverage_increase_percent']}%")

        # Show sample products
        print(f"\nExample products using new colors:")
        for sample in color_analysis['sample_products'][:3]:
            print(f"  - {sample['title']}")
            print(f"    Color: {sample['learned_color']}")

        # Save learned colors to store profile
        learned_colors = color_analysis['learned_colors']
        save_store_colors(learned_colors, store_profile_path='data/store_profile.json')

        # Return complete profile
        return {
            'keywords': keywords,
            'niche': niche,
            'sku_patterns': sku_patterns,
            'colors': {
                'learned': learned_colors,
                'count': len(learned_colors),
                'coverage_increase': color_analysis['coverage_increase_percent']
            }
        }
```

### Step 2: Store Profile Format

The colors are saved in `data/store_profile.json`:

```json
{
  "store_name": "Bastelschachtel",
  "analyzed_at": "2026-02-08T18:00:00Z",
  "product_count": 381,

  "keywords": {
    "primary": ["decoupage", "serviettentechnik"],
    "secondary": ["basteln", "craft"]
  },

  "niche": {
    "detected": "Craft Supplies - Decoupage",
    "confidence": 0.92
  },

  "colors": {
    "learned": {
      "mintgrün": "Mint Grün",
      "apricot": "Apricot",
      "lavendel": "Lavendel",
      "türkis": "Türkis",
      "himmelblau": "Himmelblau",
      "koralle": "Koralle",
      "pfirsich": "Pfirsich",
      "bordeaux": "Bordeaux",
      "petrol": "Petrol",
      "olive": "Olive"
    },
    "count": 10,
    "coverage_increase": 26.3
  }
}
```

### Step 3: EnrichmentPipeline Auto-Loads

When you run enrichment, colors are automatically loaded:

```python
from src.core.enrichment import EnrichmentPipeline

# Pipeline auto-loads colors from data/store_profile.json
pipeline = EnrichmentPipeline()

# Output:
# Loaded 10 store-specific colors from catalog analysis
# Total color vocabulary: 48 colors

products = [
    {'title': 'Pentart Acrylfarbe Mintgrün 20ml', 'vendor': 'Pentart'}
]

enriched, report = pipeline.run(products)

# "mintgrün" is now recognized and normalized to "Mint Grün"
print(enriched[0]['extracted_color'])  # "Mint Grün"
```

## CLI Command for Manual Color Learning

Add this to your CLI (optional):

```python
# In src/cli.py or similar
import typer
from src.core.enrichment.color_learning import ColorLearner, save_store_colors

@app.command()
def learn_colors(
    shopify_api_key: str = typer.Option(..., help="Shopify API key"),
    store_name: str = typer.Option(..., help="Store name")
):
    """
    Analyze Shopify catalog and learn product colors.

    Extracts all unique colors from your product catalog
    and saves them for automatic recognition during enrichment.
    """
    # Fetch catalog from Shopify
    products = fetch_shopify_catalog(shopify_api_key, store_name)

    # Learn colors
    learner = ColorLearner()
    analysis = learner.analyze_catalog_colors(products)

    print(f"\nColor Analysis Complete!")
    print(f"  Products analyzed: {len(products)}")
    print(f"  Base colors: {analysis['base_colors']}")
    print(f"  New colors found: {analysis['total_learned']}")
    print(f"  Coverage increase: +{analysis['coverage_increase_percent']}%")

    # Show samples
    print(f"\nSample products with new colors:")
    for sample in analysis['sample_products']:
        print(f"  - {sample['title']}")
        print(f"    → Color: {sample['learned_color']}")

    # Save
    save_store_colors(analysis['learned_colors'])
    print(f"\nSaved {analysis['total_learned']} colors to data/store_profile.json")
    print("These colors will be automatically recognized during enrichment.")

# Usage:
# python -m src.cli learn-colors --shopify-api-key xxx --store-name bastelschachtel
```

## Testing Color Learning

### Test with Sample Catalog

```python
from src.core.enrichment.color_learning import ColorLearner

# Sample products with various colors
products = [
    {'title': 'Acrylfarbe Mintgrün 20ml', 'variants': []},
    {'title': 'Reispapier Lavendel A4', 'variants': []},
    {'title': 'Serviette Apricot 33x33cm', 'variants': []},
    {'title': 'Farbe Himmelblau 50ml', 'variants': []},
    {'title': 'Kleber Transparent 100ml', 'variants': []},
]

learner = ColorLearner()
learned = learner.extract_colors_from_catalog(products)

print("Learned colors:")
for raw, normalized in learned.items():
    print(f"  {raw} → {normalized}")

# Output:
#   mintgrün → Mint Grün
#   lavendel → Lavendel
#   apricot → Apricot
#   himmelblau → Himmelblau
#   transparent → Transparent
```

### Test Extraction with Learned Colors

```python
from src.core.enrichment.extractors import AttributeExtractor
from src.core.enrichment.config import COLOR_MAP

# Merge learned colors with base
learned_colors = {
    'mintgrün': 'Mint Grün',
    'apricot': 'Apricot'
}
combined_map = {**COLOR_MAP, **learned_colors}

# Create extractor with combined map
extractor = AttributeExtractor(custom_color_map=combined_map)

# Test extraction
result = extractor.extract_from_title("Pentart Acrylfarbe Mintgrün 20ml")

print(f"Extracted color: {result['extracted_color']}")  # "Mint Grün"
```

## Color Detection Rules

### What Gets Detected

✅ **Detected as colors:**
- Color keywords in product titles
- Variant option values (Color, Farbe, etc.)
- Color-related tags

✅ **Minimum threshold:**
- Must appear in at least 2 products (filters typos)

✅ **Auto-normalized:**
- "mintgrün" → "Mint Grün"
- "sky-blue" → "Sky Blue"
- "PETROL" → "Petrol"

### What Gets Filtered

❌ **Not detected:**
- Generic words: "format", "papier", "vintage", "set"
- Single-character words
- Words appearing only once (likely typos)

## Updating Colors

### Option 1: Re-run Store Analysis

When you add new products with new colors:

```bash
# Re-analyze catalog (will merge with existing colors)
python -m src.cli learn-colors --shopify-api-key xxx --store-name xxx
```

### Option 2: Manual Update

Edit `data/store_profile.json` directly:

```json
{
  "colors": {
    "learned": {
      "mintgrün": "Mint Grün",
      "newcolor": "New Color"  // Add manually
    }
  }
}
```

### Option 3: Incremental Learning

Add to StoreProfileAnalyzer to learn incrementally:

```python
# When user adds new products
new_products = fetch_new_products(since=last_analysis_date)

if len(new_products) > 10:  # Only worth learning if enough new products
    learner = ColorLearner()
    new_colors = learner.extract_colors_from_catalog(new_products)

    # Merge with existing colors
    existing_colors = load_store_colors()
    existing_colors.update(new_colors)
    save_store_colors(existing_colors)
```

## Monitoring Color Coverage

Track how well colors are being recognized:

```python
from src.core.enrichment.color_learning import ColorLearner

learner = ColorLearner()
analysis = learner.analyze_catalog_colors(your_products)

print(f"Color Recognition Stats:")
print(f"  Base vocabulary: {analysis['base_colors']} colors")
print(f"  Store-specific: {analysis['total_learned']} colors")
print(f"  Total coverage: {analysis['base_colors'] + analysis['total_learned']} colors")
print(f"  Improvement: +{analysis['coverage_increase_percent']}%")
```

## FAQ

### Q: Do I need to re-run color learning often?

**A:** No. Run it:
- When first connecting store
- When adding many new products with new colors
- Every few months to catch new color trends

### Q: Will old products be re-processed with new colors?

**A:** No. Only new enrichment runs use the updated color map. To re-enrich old products with new colors, run the enrichment pipeline again.

### Q: What if a color is wrong?

**A:** Edit `data/store_profile.json` manually:

```json
{
  "colors": {
    "learned": {
      "mintgrün": "Mint",  // Change normalization
      "wrongcolor": null    // Remove entry
    }
  }
}
```

### Q: Can I disable automatic color loading?

**A:** Yes, pass empty store_profile_path:

```python
pipeline = EnrichmentPipeline(store_profile_path='')  # Won't load store colors
```

### Q: How do I see which colors were learned?

**A:** Check the store profile:

```bash
# View learned colors
cat data/store_profile.json | jq '.colors.learned'
```

Or in Python:

```python
from src.core.enrichment.color_learning import load_store_colors

colors = load_store_colors()
for raw, normalized in colors.items():
    print(f"{raw} → {normalized}")
```

## Integration Checklist

- [ ] Update StoreProfileAnalyzer to call ColorLearner
- [ ] Test with sample catalog (20+ products with various colors)
- [ ] Verify colors saved to data/store_profile.json
- [ ] Test EnrichmentPipeline loads colors automatically
- [ ] Verify extraction works with learned colors
- [ ] Add CLI command for manual color learning (optional)
- [ ] Document color learning in user onboarding flow
- [ ] Add monitoring for color recognition coverage

---

**Result**: Users get automatic color recognition based on their actual product catalog, without manual configuration.
