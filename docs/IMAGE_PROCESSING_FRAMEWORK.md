# Image Processing Framework

**Version:** 1.0
**Last Updated:** 2026-02-02

## Overview

The **Image Processing Framework** is a comprehensive, codified system that defines **ALL** image processing rules and logic, eliminating uncertainty and constant questioning. The system automatically applies the right rules based on context.

### Key Benefits

✅ **No More Asking**: System follows defined rules automatically
✅ **Predictable Behavior**: Same input → same output every time
✅ **Easy Configuration**: Change rules in YAML, not code
✅ **Single Source of Truth**: All rules in one place
✅ **Testable**: Rules can be unit tested independently
✅ **Maintainable**: Add new rules without code changes
✅ **Auditable**: Every decision is logged and traceable

---

## Architecture

### Components

1. **`config/image_processing_rules.yaml`** - Master configuration file (all rules)
2. **`src/core/image_framework.py`** - Framework implementation
3. **`src/core/pipeline.py`** - Integration into main pipeline
4. **`src/core/vision_engine.py`** - Vision AI integration
5. **`hybrid_image_naming.py`** - Hybrid naming functions

### Framework Classes

```
ImageFramework
├── ImageProcessor (transformations)
├── ImageNamingEngine (filenames + alt text)
├── ImageUploadStrategy (upload method selection)
└── ImagePositioningEngine (ordering + positioning)
```

---

## Usage

### Basic Usage (Recommended)

```python
from src.core.image_framework import get_framework

# Get singleton framework instance
framework = get_framework()

# Process an image (all rules applied automatically)
result = framework.process_image(
    product=product,           # Shopify product data
    image_url=image_url,       # Image URL
    image_role="primary",      # "primary" or "shared"
    vendor="Pentart"           # Vendor name
)

# Result contains:
# {
#     "filename": "pentart-galaxy-flakes-15g-jupiter-white.png",
#     "alt_text": "Galaxy Flakes 15g - Jupiter white - Produktfoto - Pentart",
#     "image_type": "packshot",
#     "transformations": {...},
#     "upload_strategy": "staged",
#     "position": 0,
#     "metadata": {...}
# }
```

### Integration with Pipeline

The framework is automatically integrated into `src/core/pipeline.py`:

```python
# In process_identifier():
if scraped.get("image_url"):
    framework = get_framework()
    image_result = framework.process_image(
        product=product,
        image_url=scraped["image_url"],
        image_role="primary",
        vendor=product.get("vendor")
    )

    # Store results
    scraped["image_type"] = image_result["image_type"]
    scraped["suggested_filename"] = image_result["filename"]
    scraped["alt_text"] = image_result["alt_text"]
```

### Direct Transformation Application

```python
from src.core.image_framework import ImageFramework

framework = ImageFramework()

# Get transformation rules
transformations = framework.processor.get_transformations(
    image_type="packshot",
    image_role="primary",
    vendor="Pentart"
)

# Apply transformations to image bytes
transformed_bytes = framework.processor.apply_transformations(
    image_data=original_image_bytes,
    transformations=transformations
)
```

---

## Configuration

All rules are defined in **`config/image_processing_rules.yaml`**.

### Key Sections

#### 1. Global Defaults

```yaml
defaults:
  image_format: "png"
  transparency: true
  square_conversion: true
  square_method: "center_crop"
  target_size: 900
  alt_text_language: "de"
```

#### 2. Vision AI Rules

```yaml
vision_ai:
  enabled: true
  provider: "openrouter"
  model: "google/gemini-2.0-flash-001"
  fallback:
    when_budget_exceeded: "template"
    template: "{product_name} von {vendor}"
```

#### 3. Hybrid Naming Rules

```yaml
naming:
  strategy: "hybrid"

  primary:
    pattern: "{vendor}-{product_line}-{variant_name}.{ext}"

  shared:
    pattern: "{vendor}-{product_line}-{image_type}.{ext}"

  image_types:
    packshot:
      description: "Single product container/jar on plain background"
      german: "Produktfoto"
      priority: high
```

#### 4. Upload Strategy Rules

```yaml
upload:
  staged_uploads:
    use_when:
      - need_exact_filename: true
      - replacing_primary: true
    method: "stagedUploadsCreate"
```

#### 5. Image Positioning Rules

```yaml
positioning:
  primary:
    position: 0
    action: "replace_and_reorder"
    delete_old_primary: false

  shared:
    position: "append"
    action: "append_only"
```

#### 6. Transformation Rules

```yaml
transformation:
  always:
    - convert_to_square:
        method: "center_crop"
        target_size: 900
    - ensure_transparency:
        convert_to_rgba: true
    - optimize_size:
        quality: 95
        compression: 6
```

#### 7. Deletion Safeguards

```yaml
deletion:
  default_policy: "preserve"

  allow_deletion_when:
    - explicit_user_confirmation: true
    - backup_created: true

  never_delete:
    - shared_images
    - images_without_backup
    - primary_without_replacement
```

#### 8. Vendor Overrides

```yaml
vendor_overrides:
  pentart:
    min_images: 3
    image_format: "png"
    alt_text_language: "de"
```

---

## Workflow Decision Tree

The framework follows this workflow automatically:

1. **Step 1: Image Type Identification**
   - Method: Vision AI
   - Fallback: "detail"

2. **Step 2: Filename Generation**
   - If primary: Use primary pattern with variant name
   - If shared: Use shared pattern with AI type
   - Method: Hybrid naming

3. **Step 3: Alt Text Generation**
   - Method: Vision AI
   - Enhance with: SEO keywords
   - Language: German (de)

4. **Step 4: Transformation**
   - Apply: square, transparency, optimize

5. **Step 5: Upload**
   - Method: Staged upload (for filename control)
   - Verify: Filename correctness

6. **Step 6: Positioning**
   - If primary: Reorder to position 0
   - If shared: Append after primary

7. **Step 7: Cleanup** (OPTIONAL)
   - Delete old: false (NEVER without confirmation)
   - Verify: Result correctness

---

## Examples

### Example 1: Primary Image Upload

**Input:**
```python
product = {
    "id": "gid://shopify/Product/123",
    "title": "Galaxy Flakes 15g - Jupiter white",
    "vendor": "Pentart"
}
image_url = "https://example.com/image.jpg"
```

**Framework Processing:**

1. **Type Identification**: Vision AI → "packshot"
2. **Filename**: `pentart-galaxy-flakes-15g-jupiter-white.png`
3. **Alt Text**: `Galaxy Flakes 15g - Jupiter white - Produktfoto - Pentart`
4. **Transformations**: Square (900x900), RGBA, PNG compression 6
5. **Upload**: Staged upload (exact filename)
6. **Position**: 0 (featured)

**Output:**
```python
{
    "filename": "pentart-galaxy-flakes-15g-jupiter-white.png",
    "alt_text": "Galaxy Flakes 15g - Jupiter white - Produktfoto - Pentart",
    "image_type": "packshot",
    "upload_strategy": "staged",
    "position": 0
}
```

### Example 2: Shared Image Distribution

**Input:**
```python
product = {
    "id": "gid://shopify/Product/123",
    "title": "Galaxy Flakes 15g - Jupiter white",
    "vendor": "Pentart"
}
image_url = "https://example.com/groupshot.jpg"
image_role = "shared"
```

**Framework Processing:**

1. **Type Identification**: Vision AI → "groupshot"
2. **Filename**: `pentart-galaxy-flakes-15g-groupshot.jpg`
3. **Alt Text**: `Galaxy Flakes von Pentart - Gruppenbild`
4. **Transformations**: Square (900x900), JPG quality 95
5. **Upload**: Staged upload
6. **Position**: append (after primary)

**Output:**
```python
{
    "filename": "pentart-galaxy-flakes-15g-groupshot.jpg",
    "alt_text": "Galaxy Flakes von Pentart - Gruppenbild",
    "image_type": "groupshot",
    "upload_strategy": "staged",
    "position": "append"
}
```

---

## Image Types

The framework recognizes these image types (from Vision AI):

| Type | Description | German | Priority |
|------|-------------|--------|----------|
| **packshot** | Single product container/jar on plain background | Produktfoto | High |
| **groupshot** | Multiple products/variants shown together | Gruppenbild | High |
| **detail** | Close-up of texture, flakes, or product effect | Detailansicht | Medium |
| **lifestyle** | Product in use or styled scene | Anwendung | Medium |

---

## Filename Patterns

### Primary Images (Variant-Specific)

**Pattern:** `{vendor}-{product_line}-{variant_name}.{ext}`

**Examples:**
- `pentart-galaxy-flakes-15g-jupiter-white.png`
- `pentart-galaxy-flakes-15g-saturn-green.png`
- `pentart-galaxy-flakes-15g-neptune-blue.png`

### Shared Images (Multi-Variant)

**Pattern:** `{vendor}-{product_line}-{image_type}.{ext}`

**Examples:**
- `pentart-galaxy-flakes-15g-packshot.jpg`
- `pentart-galaxy-flakes-15g-groupshot.jpg`
- `pentart-galaxy-flakes-15g-detail.jpg`
- `pentart-galaxy-flakes-15g-lifestyle.jpg`

**Key Rule:** Same type = same filename across all variants

---

## Alt Text Patterns

### Primary Images

**Pattern:** `{product_name} - {variant_name} - {image_type_german} - {vendor}`

**Example:** `Galaxy Flakes 15g - Jupiter white - Produktfoto - Pentart`

### Shared Images

**Pattern:** `{product_line} von {vendor} - {image_type_german}`

**Example:** `Galaxy Flakes von Pentart - Gruppenbild`

**Language:** German (de) by default
**Max Length:** 125 characters (Shopify limit)

---

## Transformations

All images go through these transformations:

1. **Square Conversion** (1:1 aspect ratio)
   - Method: Center crop
   - Target: 900x900px
   - Preserves main subject

2. **Transparency**
   - Convert to RGBA (for PNG)
   - Preserve alpha channel
   - White background for JPG conversion

3. **Format Optimization**
   - **PNG**: Primary, packshot, detail (compression 6)
   - **JPG**: Shared, groupshot, lifestyle (quality 95)

4. **Size Optimization**
   - Target: 900x900px
   - Min: 500px
   - Max: 2048px

---

## Upload Strategies

### Staged Upload (Default)

**When to Use:**
- Need exact filename control
- Replacing primary image
- New image uploads

**Method:** `stagedUploadsCreate`

**Benefits:**
- Full filename control
- No random filenames
- Consistent naming

### Simple Upload (Fallback)

**When to Use:**
- Source URL provided
- Filename not critical

**Method:** `productCreateMedia`

---

## Deletion Safeguards

### Default Policy: PRESERVE

**CRITICAL:** Framework defaults to **NEVER delete** images.

### Deletion Only Allowed When:

1. ✅ Explicit user confirmation
2. ✅ Backup created
3. ✅ Not a shared image
4. ✅ Replacement exists (for primary)

### NEVER Delete:

- ❌ Shared images (used by multiple products)
- ❌ Images without backup
- ❌ Primary without replacement

### Pre-Deletion Checks:

1. Download to backup
2. Create deletion manifest
3. Log all deletions
4. Require user approval

---

## Vendor Overrides

Vendors can override framework defaults:

```yaml
vendor_overrides:
  pentart:
    min_images: 3           # Pentart products need more images
    image_format: "png"     # Always PNG for Pentart
    alt_text_language: "de" # German alt text
```

**Supported Overrides:**
- `min_images`: Minimum image count
- `image_format`: Default format (png/jpg/webp)
- `alt_text_language`: Alt text language (de/en)
- `square_method`: Square conversion method
- `target_size`: Image dimensions

---

## Error Handling

### Vision API Failure

**Action:** Use fallback template
**Template:** `{product_name} von {vendor}`
**Log:** Yes
**Notify:** No

### Upload Failure

**Action:** Retry (max 3 times)
**Log:** Yes
**Notify:** Yes

### Filename Collision

**Action:** Append UUID
**Format:** `{filename}_{uuid}`
**Log:** Yes

### Budget Exceeded

**Action:** Use cache or fallback
**Log:** Yes
**Notify:** Yes

---

## Logging & Monitoring

### Log Events

- Vision AI calls
- Filename generation
- Transformations applied
- Uploads completed
- Deletions attempted
- Errors encountered

### Metrics Tracked

- Images processed count
- Vision API cost
- Upload success rate
- Average processing time

### Log File

**Location:** `logs/image_processing.log`
**Level:** INFO (configurable)

---

## Testing

### Test 1: Primary Image Upload

```python
framework = get_framework()
result = framework.process_image(
    product={"title": "Galaxy Flakes 15g - Jupiter white", "vendor": "Pentart"},
    image_url="https://example.com/image.jpg",
    image_role="primary"
)

assert result["image_type"] in ["packshot", "groupshot", "detail", "lifestyle"]
assert result["filename"].endswith(".png")
assert "Pentart" in result["alt_text"]
assert result["upload_strategy"] == "staged"
assert result["position"] == 0
```

### Test 2: Shared Image Distribution

```python
result = framework.process_image(
    product={"title": "Galaxy Flakes 15g - Jupiter white", "vendor": "Pentart"},
    image_url="https://example.com/groupshot.jpg",
    image_role="shared"
)

assert result["filename"] == "pentart-galaxy-flakes-15g-groupshot.jpg"
assert "Gruppenbild" in result["alt_text"]
assert result["position"] == "append"
```

### Test 3: Filename Validation

```python
assert framework.validate_filename("pentart-galaxy-flakes-15g-packshot.jpg") == True
assert framework.validate_filename("PENTART Galaxy Flakes.JPG") == False  # Not sanitized
```

### Test 4: Transformations

```python
transformations = framework.processor.get_transformations(
    image_type="packshot",
    image_role="primary",
    vendor="Pentart"
)

assert transformations["format"] == "png"
assert transformations["convert_to_square"]["method"] == "center_crop"
assert transformations["convert_to_square"]["target_size"] == 900
```

---

## Migration Guide

### From Legacy Code to Framework

**Before (Legacy):**
```python
vision_metadata = generate_vision_metadata(product, scraped, vendor)
if vision_metadata:
    scraped["alt_text"] = vision_metadata["alt_text"]
    scraped["image_type"] = vision_metadata["image_type"]
```

**After (Framework):**
```python
framework = get_framework()
result = framework.process_image(product, image_url, "primary", vendor)
scraped.update({
    "alt_text": result["alt_text"],
    "image_type": result["image_type"],
    "suggested_filename": result["filename"],
    "image_transformations": result["transformations"]
})
```

### Benefits of Migration

1. **Centralized Rules**: All logic in YAML config
2. **Comprehensive**: Covers transformations, upload, positioning
3. **Testable**: Framework methods can be unit tested
4. **Maintainable**: Change rules without code changes
5. **Auditable**: All decisions logged with metadata

---

## Troubleshooting

### Issue: Framework not applying rules

**Check:**
1. YAML config exists: `config/image_processing_rules.yaml`
2. Framework loaded: Check logs for "Loaded image processing rules"
3. Vendor override: Check if vendor has custom rules

### Issue: Wrong filename generated

**Check:**
1. Image role: Is it "primary" or "shared"?
2. Product context: Is product title parsed correctly?
3. Naming pattern: Check `naming.primary.pattern` or `naming.shared.pattern`

### Issue: Transformations not applied

**Check:**
1. Transformation rules: Check `transformation.always` in config
2. Format config: Check `transformation.formats.png` or `.jpg`
3. Processor logs: Check for transformation errors

### Issue: Vision AI not working

**Check:**
1. Vision AI enabled: `vision_ai.enabled = true`
2. API credentials: Check `.env` for `OPENROUTER_API_KEY`
3. Budget: Check cache for budget exceeded errors
4. Fallback: Framework uses template fallback on AI failure

---

## Best Practices

### 1. Always Use Framework for New Code

```python
# ✅ GOOD
framework = get_framework()
result = framework.process_image(product, image_url, "primary")

# ❌ BAD
vision_metadata = generate_vision_metadata(product, scraped)
filename = generate_hybrid_filename(ai_type, seo_template)
```

### 2. Check Framework Results

```python
result = framework.process_image(product, image_url, "primary")

# Validate critical fields
assert result["filename"], "Filename must be generated"
assert result["alt_text"], "Alt text must be generated"
assert result["upload_strategy"] in ["staged", "simple"]
```

### 3. Use Vendor Overrides for Special Cases

```yaml
vendor_overrides:
  my_vendor:
    image_format: "webp"  # Override default PNG
    min_images: 5         # Require more images
```

### 4. Log Framework Decisions

```python
logger.info(f"Framework result: {result['metadata']}")
```

### 5. Test Framework Changes

After modifying `image_processing_rules.yaml`:

```bash
python -m pytest tests/test_image_framework.py -v
```

---

## Future Enhancements

### Planned Features

1. **Full Vision AI Integration**: Direct integration with vision_client
2. **Batch Processing**: Process multiple images in parallel
3. **Advanced Transformations**: Watermarks, overlays, filters
4. **Multi-Language Alt Text**: Support for EN, FR, IT, etc.
5. **Performance Metrics Dashboard**: Real-time monitoring
6. **Automated Testing**: CI/CD integration
7. **Vendor-Specific Transformations**: Per-vendor image rules

---

## Related Documentation

- **CRITICAL_SAFEGUARDS.md** - Deletion safeguards and safety rules
- **vendor_configs.yaml** - Vendor-specific configurations
- **product_quality_rules.yaml** - Product quality requirements
- **hybrid_image_naming.py** - Hybrid naming implementation

---

## Support

For issues or questions:

1. Check this documentation
2. Review `config/image_processing_rules.yaml`
3. Check logs: `logs/image_processing.log`
4. Review framework source: `src/core/image_framework.py`

---

**Last Updated:** 2026-02-02
**Framework Version:** 1.0
**Status:** ✅ Production Ready
