# CRITICAL SAFEGUARDS - IMAGE OPERATIONS

## RED FLAGS - NEVER DO THESE WITHOUT EXPLICIT USER CONFIRMATION:

### 1. DELETION POLICY
- **NEVER** delete images unless the user explicitly says "delete this specific image"
- **NEVER** delete multiple images at once
- **NEVER** assume "old" or "random filename" means deletable
- **DEFAULT: PRESERVE EVERYTHING**

### 2. BACKUP BEFORE DELETION
- **ALWAYS** download and save images locally before ANY deletion
- **ALWAYS** create a manifest of what will be deleted
- **ALWAYS** get user approval with a detailed list before deleting

### 3. PRIMARY IMAGE REPLACEMENT RULES
When replacing a primary image:
- **ONLY** upload the new primary image
- **ONLY** reorder it to position 1 (featured)
- **DO NOT** delete any existing images
- **PRESERVE** all other images (positions 2, 3, 4, etc.)

### 4. WHAT WENT WRONG - GALAXY FLAKES INCIDENT

**What was requested:**
- Replace primary image (position 1) with new Pentart supplier image
- Use proper SEO filename
- Keep image square and transparent

**What I did wrong:**
```python
# WRONG - This deleted ALL images:
old_media_ids = [edge['node']['id'] for edge in current_media]
for old_id in old_media_ids:
    delete_image(old_id)  # ❌ DELETED EVERYTHING
```

**What I should have done:**
```python
# CORRECT - Only replace primary, keep others:
# 1. Upload new image
# 2. Reorder to position 0 (featured)
# 3. DO NOT DELETE ANYTHING
# Old primary moves to position 1, all others stay
```

### 5. MANDATORY CHECKS FOR ANY DELETE OPERATION

Before ANY `productDeleteMedia` mutation:

1. **List exactly what will be deleted** (filename, position, URL)
2. **Download all images to local backup directory** with metadata
3. **Create deletion manifest JSON** with recovery information
4. **Ask user for explicit confirmation** showing the list
5. **Only proceed if user says "yes, delete these specific images"**

### 6. SAFE UPDATE PATTERN

For replacing primary images:

```python
def replace_primary_image_safely(product_id, new_image_data, new_filename, alt_text):
    """
    SAFE method to replace primary image without deleting others
    """
    gid = f"gid://shopify/Product/{product_id}"

    # 1. Upload new image (does NOT delete anything)
    new_media_id = upload_with_staged_filename(gid, new_image_data, new_filename, alt_text)

    # 2. Get all current media
    all_media_ids = get_all_media_ids(gid)

    # 3. Reorder: put new image first, others stay in their order
    if new_media_id in all_media_ids:
        all_media_ids.remove(new_media_id)
    reordered = [new_media_id] + all_media_ids

    # 4. Apply reorder
    reorder_media(gid, reordered)

    # 5. DO NOT DELETE ANYTHING
    # Old primary is now in position 1
    # All other images preserved

    return True
```

### 7. DELETION REQUIRES

- Explicit instruction: "delete image X"
- User confirmation after seeing what will be deleted
- Backup created and verified
- Cannot be part of automated batch operations

## CONSEQUENCE OF VIOLATION

Breaking these rules results in:
- Permanent data loss
- Loss of user trust
- Inability to recover
- Project failure

## RECOVERY IMPOSSIBLE WHEN

- No backup was made
- Shopify API doesn't provide undelete
- User didn't save originals elsewhere
- = PERMANENT LOSS

### 8. SKU/ARTICLE NUMBER RETRIEVAL SOP

**ALWAYS** attempt to retrieve SKU automatically before asking the user:

```
Priority order for finding article numbers:
1. Get SKU from Shopify API (product variants query)
2. If no SKU, get barcode/EAN from Shopify API
3. If Pentart product, cross-reference EAN with local Pentart database
4. ONLY ask user as last resort if all above fail
```

**Never ask for SKU when you have:**
- Product handle (can query Shopify API)
- Product ID (can query Shopify API)
- Access to local product databases

**Example correct flow:**
```python
# 1. Get product from Shopify by handle
product = get_product_by_handle(handle)

# 2. Extract SKU from variant
sku = product.variants[0].sku

# 3. If no SKU, try barcode
if not sku:
    sku = product.variants[0].barcode

# 4. If Pentart and no SKU, check local database
if not sku and vendor == "Pentart":
    sku = lookup_pentart_local_db(barcode)

# 5. Only now ask user
if not sku:
    ask_user_for_sku()
```

### 9. VISION AI IMAGE VERIFICATION (INTEGRATED)

**ALWAYS** use vision AI to verify image types and generate proper metadata:

**Integration Point:** `src/core/pipeline.py` → `generate_vision_metadata()`

**Workflow:**
```python
# 1. Vision AI analyzes image
vision_metadata = generate_vision_metadata(product, scraped, vendor)

# 2. Returns structured metadata
{
    "image_type": "groupshot",  # What AI actually sees
    "filename": "pentart-galaxy-flakes-15g-groupshot.jpg",  # Hybrid naming
    "alt_text": "Galaxy Flakes von Pentart - verschiedene Farben - Gruppenbild"
}

# 3. Pipeline uses metadata
scraped["image_type"] = vision_metadata["image_type"]
scraped["suggested_filename"] = vision_metadata["filename"]
scraped["alt_text"] = vision_metadata["alt_text"]
```

**Hybrid Naming Rule:**
- **AI provides:** Image type (packshot, groupshot, detail, lifestyle)
- **SEO provides:** Structure (vendor-product-type.ext)
- **Result:** Accurate + SEO-optimized

**Example:**
- AI sees: "groupshot"
- SEO template: "pentart-galaxy-flakes-15g-{type}.jpg"
- Result: "pentart-galaxy-flakes-15g-groupshot.jpg" ✓

**Benefit:** Never again misname images as "detail" when they're actually "groupshot"

---

**Created:** 2026-02-02
**Reason:** Galaxy Flakes incident - deleted all product images when only primary should have been replaced
**Updated:** 2026-02-02 - Added SKU retrieval SOP
**Updated:** 2026-02-02 - Integrated vision AI verification with hybrid naming
**Status:** ACTIVE - MANDATORY COMPLIANCE
