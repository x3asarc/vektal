# Hybrid Naming Example - Galaxy Flakes

## Example 1: Groupshot Image

### INPUT
```python
product = {
    "title": "Galaxy Flakes 15g - Juno rose",
    "vendor": "Pentart",
    "product_type": "Flakes/ Blattmetall",
    "image_url": "https://cdn.shopify.com/s/files/1/0422/.../galaxy-flakes-15g-juno-rose-bastelschachtel-20160.jpg"
}

scraped = {
    "image_url": "https://cdn.shopify.com/s/files/1/0422/.../galaxy-flakes-15g-juno-rose-bastelschachtel-20160.jpg"
}

seo_keywords = ["Galaxy Flakes", "Pentart", "15g", "Glitzerflocken", "Effektflocken"]
```

### VISION AI ANALYSIS
```python
vision_result = {
    "type": "groupshot",
    "description": "A group of approximately ten small open jars, each filled with Pentart Galaxy Flakes in different iridescent colors including pink, purple, blue, and green, arranged on a white surface",
    "confidence": 0.95
}
```

### SEO PLAN DATA
```python
seo_template = {
    "vendor": "pentart",
    "product_line": "galaxy-flakes",
    "size": "15g",
    "keywords": ["schillernde Effektflocken", "Glitzerflocken", "verschiedene Farben", "Dekorfolien"]
}
```

### HYBRID NAMING FUNCTION CALL
```python
from hybrid_image_naming import generate_hybrid_filename, generate_hybrid_alt_text

# Generate filename
filename = generate_hybrid_filename(
    ai_type="groupshot",
    seo_template="pentart-galaxy-flakes-15g-detail.jpg",
    product_name="galaxy-flakes-15g"
)

# Generate alt text
alt_text = generate_hybrid_alt_text(
    ai_description="Ten small jars with Galaxy Flakes in different iridescent colors",
    ai_type="groupshot",
    seo_keywords=["Galaxy Flakes", "Pentart", "15g", "verschiedene Farben", "Glitzerflocken"],
    language="de"
)
```

### HYBRID OUTPUT
```python
{
    "filename": "pentart-galaxy-flakes-15g-groupshot.jpg",
    "alt_text": "Galaxy Flakes von Pentart - verschiedene Farben - 15g - Gruppenbild",
    "image_type": "groupshot"
}
```

**Before (SEO Plan):** `pentart-galaxy-flakes-15g-detail.jpg` ❌ (Wrong type)
**After (Hybrid):** `pentart-galaxy-flakes-15g-groupshot.jpg` ✓ (Accurate + SEO)

---

## Example 2: Packshot Image

### INPUT
```python
product = {
    "title": "Galaxy Flakes 15g - Saturn green",
    "vendor": "Pentart",
    "image_url": "https://cdn.shopify.com/s/files/1/0422/.../galaxy-flakes-15g-saturn-green-bastelschachtel-29324.jpg"
}
```

### VISION AI ANALYSIS
```python
vision_result = {
    "type": "packshot",
    "description": "A single jar of Pentart Galaxy Flakes with a black lid on a white background, showing green iridescent flakes inside",
    "confidence": 0.98
}
```

### HYBRID OUTPUT
```python
{
    "filename": "pentart-galaxy-flakes-15g-packshot.jpg",
    "alt_text": "Galaxy Flakes von Pentart - 15g - schillernde Effektflocken - Produktfoto",
    "image_type": "packshot"
}
```

**Before (Random):** `galaxy-flakes-15g-saturn-green-bastelschachtel-29324.jpg` ❌
**After (Hybrid):** `pentart-galaxy-flakes-15g-packshot.jpg` ✓

---

## Example 3: Detail/Texture Image

### INPUT
```python
product = {
    "title": "Galaxy Flakes 15g - Uranus blue",
    "vendor": "Pentart",
    "image_url": "https://cdn.shopify.com/s/files/1/0422/.../galaxy-flakes-detail-texture-89263.jpg"
}
```

### VISION AI ANALYSIS
```python
vision_result = {
    "type": "detail",
    "description": "The words 'GALAXY FLAKES' against a black background with colorful iridescent flakes scattered around, showing the metallic sheen and texture of the flakes",
    "confidence": 0.92
}
```

### HYBRID OUTPUT
```python
{
    "filename": "pentart-galaxy-flakes-15g-detail.jpg",
    "alt_text": "Galaxy Flakes von Pentart - schillernde Effektflocken - Detailansicht",
    "image_type": "detail"
}
```

**Before (SEO Plan):** `pentart-galaxy-flakes-15g-detail.jpg` ✓ (Correct!)
**After (Hybrid):** `pentart-galaxy-flakes-15g-detail.jpg` ✓ (Confirmed accurate)

---

## Example 4: Lifestyle Image

### INPUT
```python
product = {
    "title": "Galaxy Flakes 15g - Vesta purple",
    "vendor": "Pentart",
    "image_url": "https://cdn.shopify.com/s/files/1/0422/.../galaxy-flakes-clock-lifestyle-41487.jpg"
}
```

### VISION AI ANALYSIS
```python
vision_result = {
    "type": "lifestyle",
    "description": "A decorative clock face featuring a color gradient with iridescent Galaxy Flakes embedded in resin, showing the product in a finished craft project",
    "confidence": 0.89
}
```

### HYBRID OUTPUT
```python
{
    "filename": "pentart-galaxy-flakes-15g-lifestyle.jpg",
    "alt_text": "Galaxy Flakes von Pentart - 15g - Anwendung in Bastelprojekt",
    "image_type": "lifestyle"
}
```

**Before (SEO Plan):** `pentart-galaxy-flakes-15g-detail.jpg` ❌ (Wrong type)
**After (Hybrid):** `pentart-galaxy-flakes-15g-lifestyle.jpg` ✓ (Accurate + SEO)

---

## Full Pipeline Example

### When Processing "Galaxy Flakes 15g - Juno rose"

**Step 1: Vision AI Call**
```python
vision_metadata = generate_vision_metadata(product, scraped, vendor="Pentart")
```

**Step 2: Vision AI Returns**
```python
{
    "image_type": "groupshot",
    "description": "Ten jars of Galaxy Flakes in different colors",
    "confidence": 0.95,
    "filename": "pentart-galaxy-flakes-15g-groupshot.jpg",
    "alt_text": "Galaxy Flakes von Pentart - verschiedene Farben - 15g - Gruppenbild"
}
```

**Step 3: Pipeline Uses Result**
```python
scraped["image_type"] = "groupshot"
scraped["suggested_filename"] = "pentart-galaxy-flakes-15g-groupshot.jpg"
scraped["alt_text"] = "Galaxy Flakes von Pentart - verschiedene Farben - 15g - Gruppenbild"
```

**Step 4: When Uploading to Shopify**
```python
# Upload with proper filename
upload_image_with_proper_filename(
    resolver=resolver,
    product_gid=product_gid,
    image_data=image_data,
    filename=scraped["suggested_filename"],  # pentart-galaxy-flakes-15g-groupshot.jpg
    alt_text=scraped["alt_text"]  # Galaxy Flakes von Pentart - verschiedene Farben - 15g - Gruppenbild
)
```

---

## Comparison Summary

| Image | AI Sees | SEO Plan Said | Hybrid Result | Match |
|-------|---------|---------------|---------------|-------|
| Image 1 | packshot | detail | pentart-galaxy-flakes-15g-packshot.jpg | ✓ |
| Image 2 | groupshot | detail | pentart-galaxy-flakes-15g-groupshot.jpg | ✓ |
| Image 3 | detail | detail | pentart-galaxy-flakes-15g-detail.jpg | ✓ |
| Image 4 | detail | detail | pentart-galaxy-flakes-15g-detail.jpg | ✓ |
| Image 5 | groupshot | detail | pentart-galaxy-flakes-15g-groupshot.jpg | ✓ |
| Image 6 | lifestyle | detail | pentart-galaxy-flakes-15g-lifestyle.jpg | ✓ |
| Image 7 | groupshot | detail | pentart-galaxy-flakes-15g-groupshot.jpg | ✓ |

**Result:** All 7 images now have ACCURATE type identification + SEO-optimized naming!

---

## Benefits

1. **Accuracy:** AI identifies what image actually shows
2. **SEO:** Follows vendor-product-type naming convention
3. **Consistency:** Same type = same filename across products
4. **Multilingual:** German alt text with proper keywords
5. **Scalable:** Works for any product, not just Galaxy Flakes
