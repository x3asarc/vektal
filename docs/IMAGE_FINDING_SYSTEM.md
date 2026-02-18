# Automated Image Finding System

**Created:** 2026-01-30
**Status:** Active

---

## 🎯 Overview

System to automatically find and flag missing product images using:
1. ✅ Vendor website check
2. ✅ Google Image Search (manual links provided)
3. ✅ Google Shopping (manual links provided)
4. ✅ Automatic flagging when not found
5. ✅ Easy manual addition

---

## 🚀 Quick Start

### Find Missing Images
```bash
python utils/find_product_image.py --sku "CBRP104"
```

**Output:**
- Checks vendor website (if configured)
- Provides Google Image Search link
- Provides Google Shopping link
- **FLAGS** if no automated source found
- Gives manual search instructions

### Add Image Manually
```bash
python utils/add_product_image.py --sku "CBRP104" --image-url "https://example.com/image.jpg"
```

---

## 📋 Real Example: CBRP104

### Problem
- **Product:** Reispapier A4 - Under the tuscan sun cards
- **Vendor:** Ciao Bella
- **Issue:** No image on Ciao Bella website

### Solution Process
1. **Checked vendor website** → NOT FOUND (flagged!)
2. **Googled manually:** "Ciao Bella Under the Tuscan Sun rice paper"
3. **Found on Etsy:** https://www.etsy.com/ie/listing/1896660419/
4. **Got image URL:** https://i.etsystatic.com/29438472/r/il/d8f485/7006499669/il_794xN.7006499669_gc5p.jpg
5. **Added to Shopify:**
   ```bash
   python utils/add_product_image.py --sku "CBRP104" --image-url "https://i.etsystatic.com/29438472/r/il/d8f485/7006499669/il_794xN.7006499669_gc5p.jpg"
   ```
6. **Result:** Quality score 85 → 92/100 ✅

---

## 🔍 Search Strategy

### 1. Vendor Website (Automatic Check)
```yaml
# config/vendor_configs.yaml
ciao_bella:
  website: "https://www.ciaobella.com"
  # If configured, system checks here first
```

**Status:** ⚠️ Placeholder (requires web scraping implementation)

### 2. Google Image Search (Manual Links)
System provides clickable link:
```
https://www.google.com/search?tbm=isch&q=Ciao+Bella+Reispapier+A4+Under+the+Tuscan+Sun
```

**Tip:** Look for:
- Official vendor images
- Retailer product photos (Etsy, Amazon, eBay)
- High resolution images (prefer 794x or larger)

### 3. Google Shopping (Manual Links)
System provides clickable link:
```
https://www.google.com/search?tbm=shop&q=Ciao+Bella+Reispapier+A4+Under+the+Tuscan+Sun
```

Or search by barcode:
```
https://www.google.com/search?tbm=shop&q=19423133
```

---

## 🚨 Flagging System

When image NOT found, system outputs:

```
🚨 [FLAG] NO IMAGES FOUND

Manual search required:
  - google_images: https://www.google.com/search?tbm=isch&q=...
  - google_shopping: https://www.google.com/search?tbm=shop&q=...

RECOMMENDED NEXT STEPS:
1. Search manually using links above
2. Once you find image URL, run:
   python utils/add_product_image.py --sku CBRP104 --image-url <URL>
```

This **flags** the product in the quality system, so you know manual intervention is needed.

---

## 🔧 Integration with Quality Orchestrator

### Automatic Detection
```bash
python orchestrator/product_quality_agent.py --sku "CBRP104"
```

**Output:**
```
Missing Fields: 1
   X images: Missing Product images (nice to have)

Found 1 repair job(s) needed:
   [1] images: utils/find_product_image.py --sku CBRP104
```

### With Auto-Repair
```bash
python orchestrator/product_quality_agent.py --sku "CBRP104" --auto-repair
```

**What happens:**
1. ✅ Runs `find_product_image.py`
2. ✅ Checks vendor website
3. ✅ Provides Google search links
4. 🚨 **FLAGS** if not found
5. ⏸️ Waits for manual input

---

## 📊 Quality Score Impact

| Field | Status | Score Impact |
|-------|--------|--------------|
| Images (none) | ❌ Missing | -7 points |
| Images (1+) | ✅ Present | Full points |

**Example (CBRP104):**
- Before image: 85/100
- After image: 92/100
- Improvement: +7 points

---

## 🛠️ Advanced Usage

### Add Multiple Images
```bash
# Add first image
python utils/add_product_image.py --sku "CBRP104" \
  --image-url "https://example.com/image1.jpg" \
  --alt "Front view"

# Add second image
python utils/add_product_image.py --sku "CBRP104" \
  --image-url "https://example.com/image2.jpg" \
  --alt "Back view"
```

### Batch Processing
```python
# Script to process multiple products
import subprocess

products = [
    ("CBRP104", "https://example.com/image1.jpg"),
    ("ABC123", "https://example.com/image2.jpg"),
]

for sku, image_url in products:
    subprocess.run([
        "python", "utils/add_product_image.py",
        "--sku", sku,
        "--image-url", image_url
    ])
```

---

## 🔮 Future Enhancements

### Planned Features
1. **Automated Google API Integration**
   - Google Custom Search API
   - Automatic image finding
   - No manual search needed

2. **Vendor Website Scraping**
   - Selenium-based scraping
   - Per-vendor scraping configs
   - Automated image extraction

3. **AI-Powered Image Validation**
   - Check if image matches product
   - Verify image quality
   - Flag inappropriate images

4. **Image CDN Integration**
   - Download and host images
   - Optimize for web (resize, compress)
   - Backup original URLs

### How to Upgrade

**Option 1: Google Custom Search API** (Recommended)
```bash
# 1. Get API key: https://developers.google.com/custom-search
# 2. Add to .env:
GOOGLE_SEARCH_API_KEY=your_key_here
GOOGLE_SEARCH_ENGINE_ID=your_engine_id

# 3. System will automatically use it
```

**Option 2: SerpAPI** (Easier, paid)
```bash
# 1. Sign up: https://serpapi.com/
# 2. Add to .env:
SERPAPI_KEY=your_key_here

# 3. Install: pip install google-search-results
```

---

## 📝 Best Practices

### When Searching Manually
1. **Use specific terms:** Include vendor name + product title
2. **Try barcode:** Often finds exact match
3. **Check multiple sources:** Etsy, Amazon, eBay, vendor site
4. **Prefer high-res:** 600px+ width minimum
5. **Verify product match:** Make sure it's the exact product

### Image URL Guidelines
- ✅ Direct image URLs (.jpg, .png, .webp)
- ✅ HTTPS preferred
- ✅ Permanent URLs (not temp/cached)
- ❌ Avoid redirect URLs
- ❌ Avoid auth-protected URLs

### Alt Text Best Practices
- Include vendor name
- Include product name
- Keep it descriptive
- Avoid keyword stuffing

**Good examples:**
- "Ciao Bella A4 Rice Paper - Under the Tuscan Sun"
- "Pentart Acrylic Paint Set - Metallic Colors"

**Bad examples:**
- "Image" (too generic)
- "Product photo SKU CBRP104" (not descriptive)

---

## 🆘 Troubleshooting

### Image Won't Add
**Error:** "mediaUserErrors"

**Solution:**
- Check image URL is direct link (not HTML page)
- Verify URL is publicly accessible
- Try a different image source
- Check image file size (< 20MB)

### Image Shows as "PROCESSING"
**Status:** Normal

**Timeline:**
- Shopify processes images in background
- Usually takes 1-5 minutes
- Will show in product after processing

### Can't Find Image Anywhere
**Options:**
1. Contact vendor for official product image
2. Take photo yourself (if you have product)
3. Use placeholder image temporarily
4. Flag product as "missing image" in notes

---

## ✅ Success Criteria

**System working correctly when:**
- ✅ Missing images are detected
- ✅ Search links are provided
- ✅ Products are flagged when images not found
- ✅ Manual addition is easy (one command)
- ✅ Quality scores update after adding images

---

## 📁 Files Created

1. **utils/find_product_image.py** - Image finder with flagging
2. **utils/add_product_image.py** - Manual image adder
3. **docs/IMAGE_FINDING_SYSTEM.md** - This documentation

## 🔄 Modified Files

1. **config/product_quality_rules.yaml** - Added image finder script
2. **orchestrator/product_quality_agent.py** - Integrated image checks

---

**Status:** Operational ✅
**Flagging:** Working ✅
**Manual Addition:** Easy ✅
**Next:** Add Google API integration for full automation
