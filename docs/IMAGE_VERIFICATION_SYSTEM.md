# Post-Upload Image Verification System

## Overview

Instead of preemptively transforming all images (which can over-crop zoomed images), this system:

1. **Upload first** - Let the image go to Shopify as-is
2. **Verify quality** - Check if the uploaded image is actually good
3. **Fix only if needed** - Only recrop/adjust if issues are detected
4. **Re-upload if fixed** - Replace with corrected version

## Why This Approach?

### Problem with Preemptive Cropping
```
Original image: 800x1200 (portrait, product slightly zoomed)
├─ center_crop applied
├─ Crops to 800x800
└─ Result: Product now VERY zoomed, parts cut off ❌
```

### Solution: Verify First
```
Original image: 800x1200
├─ Upload as-is
├─ Verify: "Product too zoomed, edges cut off"
├─ Apply: "contain" method (add padding instead)
└─ Re-upload: 900x900 with product fully visible ✓
```

## Workflow

### 1. Image Upload
```python
# In shopify_apply.py
client.update_product_media(product_id, image_url, alt_text=alt_text)
```

### 2. Post-Upload Verification
```python
from src.core.image_verifier import verify_and_fix_product_image

verification = verify_and_fix_product_image(
    product_id=product_id,
    image_url=image_url,  # Just uploaded
    product_title="Product Name",
    vendor="Pentart",
    image_type="packshot",
    shopify_client=client,
    auto_fix=False  # Log only for now
)
```

### 3. Verification Checks

#### Quick Checks (No AI needed)
- ✓ Is aspect ratio ~1:1? (square)
- ✓ Is size appropriate? (500-2500px)
- ✓ Is file size reasonable?

#### AI Quality Checks (Vision AI)
```
Prompt: "Analyze this product image:
- Is product cut off or cropped too tight?
- Is product too zoomed in?
- Is product clearly visible?
- Does it need adjustment?"

Response:
"Status: NEEDS_RECROP
Issue: Product edges cut off at top
Recommendation: Use contain method with padding
Confidence: 0.9"
```

### 4. Results

**Good Image:**
```
[Verifier] OK: Image looks good (confidence: 95%)
```

**Needs Attention:**
```
[Verifier] WARNING: Image may need adjustment
  Issue: Product too zoomed, container edges cut off
  Recommendation: Recrop with contain method
  Confidence: 85%
```

### 5. CLI Output

```bash
=== Image Verification ===
Status: NEEDS ATTENTION
Issue: Product edges cut off at top
Fix: Use contain method with padding
Confidence: 90%
```

## Verification Logic

### ImageVerifier Class

```python
class ImageVerifier:
    def verify_image(image_url, product_title, vendor, image_type):
        # Quick checks first
        quick_check = _quick_quality_check(img)
        if quick_check["has_issues"]:
            return needs_recrop

        # AI analysis for subjective quality
        ai_analysis = _ai_quality_check(image_url, context)

        return {
            "needs_recrop": bool,
            "issue": str,
            "recommendation": str,
            "confidence": float
        }
```

### Decision Tree

```
Image Uploaded
    │
    ├─ Quick Check
    │   ├─ Not square? → NEEDS_RECROP (use squaring)
    │   ├─ Too small? → NEEDS_RECROP (upscale/replace)
    │   └─ Too large? → NEEDS_RECROP (downsize)
    │
    ├─ AI Check
    │   ├─ Product cut off? → NEEDS_RECROP (use contain)
    │   ├─ Too zoomed? → NEEDS_RECROP (add padding)
    │   ├─ Too small in frame? → NEEDS_RECROP (crop tighter)
    │   └─ Looks good? → OK
    │
    └─ Result
        ├─ OK → Done
        └─ NEEDS_RECROP → Recrop & Re-upload
```

## Recrop Methods

### Contain (Add Padding)
Best for: Zoomed images, images where product is close to edges

```python
def _apply_contain_method(img, target_size=900):
    # Fit inside square, add transparent padding
    max_dim = max(width, height)
    canvas = new_square(max_dim, transparent)
    paste_centered(img, canvas)
    resize(canvas, target_size)
```

**Before:** 800x1200 portrait (product fills frame)
**After:** 900x900 square (product centered, padding top/bottom)

### Center Crop
Best for: Nearly square images, images with extra background

```python
def _apply_center_crop(img, target_size=900):
    # Crop to square from center
    min_dim = min(width, height)
    crop_centered(img, min_dim, min_dim)
    resize(img, target_size)
```

**Before:** 1200x800 landscape (product in center)
**After:** 900x900 square (sides cropped, product visible)

### Add Padding
Best for: Good images that just need a bit more breathing room

```python
def _add_padding(img, padding_percent=10):
    # Add 10% padding around existing image
    add_border(img, padding)
```

## Integration Points

### 1. Pipeline (pipeline.py)
```python
# Framework stores transformation rules
scraped["image_transformations"] = framework_result["transformations"]
```

### 2. Upload (shopify_apply.py)
```python
# Upload image
client.update_product_media(product_id, image_url)

# Verify post-upload
verification = verify_and_fix_product_image(...)
if verification["needs_recrop"]:
    # Log warning for now
    print(f"WARNING: {verification['issue']}")
```

### 3. CLI (main.py)
```python
# Show verification results
if apply_result.get("image_verification"):
    print("=== Image Verification ===")
    print(f"Status: {status}")
```

## Configuration

### Enable/Disable Verification

```yaml
# config/image_processing_rules.yaml

verification:
  enabled: true
  run_after_upload: true
  auto_fix: false  # Log only, don't auto-fix yet

  checks:
    quick_checks: true
    ai_quality_check: true

  thresholds:
    min_confidence: 0.7  # Only act if >70% confident
    aspect_ratio_tolerance: 0.05  # 0.95-1.05 is OK
```

### Per-Vendor Settings

```yaml
vendor_overrides:
  pentart:
    verification:
      auto_fix: false  # Be conservative with Pentart
      min_confidence: 0.85  # Higher confidence required
```

## Future Enhancements

### Phase 1: Logging Only (Current)
- ✓ Verify images post-upload
- ✓ Log issues detected
- ✓ Show recommendations
- ✗ Manual fix required

### Phase 2: Auto-Fix (Next)
- Enable `auto_fix=True`
- Automatically recrop and re-upload if issues detected
- Log before/after comparison

### Phase 3: Learning System
- Track which recommendations work best
- Build confidence scores based on outcomes
- Reduce false positives

### Phase 4: Batch Verification
- Scan all existing products
- Identify images needing improvement
- Generate fix report

## Usage Examples

### Example 1: Good Image
```bash
$ python cli/main.py --sku "40070" --auto-apply

[Framework] Applying image transformations:
  - Format: png
  - Square: 900px
  - Transparency: True

[Verifier] Checking uploaded image quality...
[Verifier] OK: Image looks good (confidence: 95%)

=== Image Verification ===
Status: OK
Confidence: 95%
```

### Example 2: Needs Recrop
```bash
$ python cli/main.py --sku "20738" --auto-apply

[Framework] Applying image transformations:
  - Format: png
  - Square: 900px
  - Transparency: True

[Verifier] Checking uploaded image quality...
[Verifier] WARNING: Image may need adjustment
  Issue: Product edges cut off at top and bottom
  Recommendation: Use contain method with 10% padding
  Confidence: 87%

=== Image Verification ===
Status: NEEDS ATTENTION
Issue: Product edges cut off at top and bottom
Fix: Use contain method with 10% padding
Confidence: 87%
```

### Example 3: Manual Fix Flow
```bash
# After seeing verification warning, manually fix:

$ python -c "
from src.core.image_verifier import ImageVerifier
verifier = ImageVerifier()

# Download, recrop, re-upload
verifier.recrop_and_reupload(
    image_url='https://cdn.shopify.com/...',
    product_id='gid://shopify/Product/123',
    media_id='gid://shopify/MediaImage/456',
    recommendation='Use contain method',
    shopify_client=client
)
"
```

## Benefits

### 1. Prevents Over-Cropping
- Doesn't blindly crop all images
- Only fixes actual problems
- Preserves good images as-is

### 2. Catches Real Issues
- Detects cut-off products
- Identifies too-zoomed images
- Flags poor framing

### 3. Smart Recommendations
- AI suggests specific fixes
- Explains the problem
- Provides confidence score

### 4. Flexible
- Can run in log-only mode
- Can enable auto-fix later
- Easy to customize thresholds

### 5. Transparent
- Shows verification results in CLI
- Logs all decisions
- User can review and override

## Testing

```bash
# Test verification system
python -c "
from src.core.image_verifier import ImageVerifier

verifier = ImageVerifier()

# Test with sample image
result = verifier.verify_image(
    image_url='https://example.com/product.jpg',
    product_title='Test Product',
    vendor='Pentart',
    image_type='packshot'
)

print(f'Needs recrop: {result[\"needs_recrop\"]}')
print(f'Issue: {result[\"issue\"]}')
print(f'Fix: {result[\"recommendation\"]}')
"
```

## Related Files

- **Core:** `src/core/image_verifier.py` - Verification logic
- **Integration:** `src/core/shopify_apply.py` - Post-upload hook
- **CLI:** `cli/main.py` - Display results
- **Framework:** `src/core/image_framework.py` - Transformation rules
- **Config:** `config/image_processing_rules.yaml` - Settings

---

**Status:** ✓ Implemented (logging only)
**Next Step:** Enable auto-fix after validation period
**Documentation:** Complete
