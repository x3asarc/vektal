# Image Processing Framework - Quick Reference

## 🚀 Quick Start

```python
from src.core.image_framework import get_framework

framework = get_framework()
result = framework.process_image(product, image_url, "primary", vendor)
```

---

## 📋 Common Tasks

### Process a Primary Image
```python
result = framework.process_image(
    product={"title": "Galaxy Flakes 15g - Jupiter white", "vendor": "Pentart"},
    image_url="https://example.com/image.jpg",
    image_role="primary",
    vendor="Pentart"
)
# Result: pentart-galaxy-flakes-15g-jupiter-white.png
```

### Process a Shared Image
```python
result = framework.process_image(
    product={"title": "Galaxy Flakes 15g", "vendor": "Pentart"},
    image_url="https://example.com/groupshot.jpg",
    image_role="shared",
    vendor="Pentart"
)
# Result: pentart-galaxy-flakes-15g-groupshot.jpg
```

### Validate a Filename
```python
is_valid = framework.validate_filename("pentart-galaxy-flakes-15g-packshot.jpg")
# Returns: True or False
```

### Get Transformations
```python
transformations = framework.processor.get_transformations(
    image_type="packshot",
    image_role="primary",
    vendor="Pentart"
)
# Returns: {format: "png", convert_to_square: {...}, ...}
```

---

## 🎯 Key Rules

### Filename Patterns

**Primary (variant-specific):**
```
{vendor}-{product_line}-{variant_name}.{ext}
pentart-galaxy-flakes-15g-jupiter-white.png
```

**Shared (multi-variant):**
```
{vendor}-{product_line}-{image_type}.{ext}
pentart-galaxy-flakes-15g-groupshot.jpg
```

### Alt Text Patterns

**Primary:**
```
{product_name} - {variant_name} - {image_type_german} - {vendor}
Galaxy Flakes 15g - Jupiter white - Produktfoto - Pentart
```

**Shared:**
```
{product_line} von {vendor} - {image_type_german}
Galaxy Flakes von Pentart - Gruppenbild
```

### Image Types

| Type | Description | German | Format |
|------|-------------|--------|--------|
| packshot | Single product on plain background | Produktfoto | PNG |
| groupshot | Multiple products together | Gruppenbild | JPG |
| detail | Close-up of texture/effect | Detailansicht | PNG |
| lifestyle | Product in use | Anwendung | JPG |

### Transformations

**All Images:**
- Square: 900x900px (center crop)
- Transparency: Preserved (RGBA)
- Quality: 95 (JPG) / Compression 6 (PNG)

---

## 🔧 Configuration

All rules in `config/image_processing_rules.yaml`

### Change Image Size
```yaml
transformation:
  dimensions:
    target_size: 900  # Change to 1200, 1500, etc.
```

### Change Default Format
```yaml
defaults:
  image_format: "png"  # Change to "jpg" or "webp"
```

### Add Vendor Override
```yaml
vendor_overrides:
  my_vendor:
    min_images: 5
    image_format: "webp"
    alt_text_language: "en"
```

---

## 🧪 Testing

### Run All Tests
```bash
python -m unittest tests.test_image_framework -v
```

### Run Specific Test
```bash
python -m unittest tests.test_image_framework.TestImageFramework.test_process_primary_image -v
```

### Run Demo
```bash
python demo_framework.py
```

---

## 🐛 Troubleshooting

### Framework not loading
**Check:** `config/image_processing_rules.yaml` exists
**Fix:** Ensure YAML is valid (no syntax errors)

### Wrong filename generated
**Check:** Image role ("primary" vs "shared")
**Check:** Product context (title parsing)
**Check:** Naming pattern in config

### Transformations not applied
**Check:** `transformation.always` in config
**Check:** Format-specific rules
**Check:** Logs for errors

### Vision AI not working
**Check:** `vision_ai.enabled = true` in config
**Check:** `.env` has `OPENROUTER_API_KEY`
**Check:** Budget not exceeded

---

## 📖 Documentation

- **Full Docs:** `docs/IMAGE_PROCESSING_FRAMEWORK.md`
- **Config:** `config/image_processing_rules.yaml`
- **Tests:** `tests/test_image_framework.py`
- **Summary:** `IMPLEMENTATION_SUMMARY.md`

---

## 🆘 Need Help?

1. Read `docs/IMAGE_PROCESSING_FRAMEWORK.md`
2. Check `config/image_processing_rules.yaml`
3. Run `python demo_framework.py`
4. Check logs: `logs/image_processing.log`
5. Run tests: `python -m unittest tests.test_image_framework`

---

**Quick Tip:** The framework automatically applies ALL rules from the YAML config. Just call `framework.process_image()` and it handles everything!
