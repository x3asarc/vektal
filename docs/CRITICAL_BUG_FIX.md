# Critical Bug Fix - Description Deletion Prevention

**Date:** 2026-01-30
**Severity:** CRITICAL
**Status:** FIXED

---

## 🚨 What Happened

When pushing SEO updates from CSV, the system was **deleting product descriptions** if the CSV had an empty `description_html` field.

### Affected Product
- **SKU:** CBRP104
- **What was lost:** Product description (852 chars)
- **Recovery:** Restored from backup (backup_20260130_122821)

---

## 🔍 Root Cause

**File:** `seo/seo_generator.py` - Line 544

**Original Code (BUG):**
```python
variables = {
    "input": {
        "id": product_id,
        "descriptionHtml": seo_content.get("description_html", ""),  # ← ALWAYS sends, even if empty!
        "seo": seo_input if seo_input else None
    }
}
```

**Problem:**
- When SEO generation failed or CSV had empty description
- System sent `descriptionHtml: ""` to Shopify
- Shopify overwrote existing description with empty string
- **Result: Data loss**

---

## ✅ The Fix

**New Code (SAFE):**
```python
# Build input - ONLY include fields that have actual content
input_data = {"id": product_id}

# CRITICAL: Only update description if we have new content
# NEVER send empty string which would delete existing description
if seo_content.get("description_html") and len(seo_content.get("description_html", "").strip()) > 0:
    input_data["descriptionHtml"] = seo_content["description_html"]

# Only add SEO if we have SEO updates
if seo_input:
    input_data["seo"] = seo_input

variables = {"input": input_data}
```

**Protection:**
1. ✅ Only includes `descriptionHtml` if content exists
2. ✅ Checks for non-empty string (not just whitespace)
3. ✅ Never sends empty/null values that could delete data
4. ✅ Only updates fields that actually have new content

---

## 🛡️ Additional Safeguards Implemented

### 1. Backup System
- **Location:** `data/backups/`
- **When:** Before every SEO generation
- **Retention:** All backups kept
- **Format:** JSON with full product data

### 2. Validation Rules
```yaml
description_html:
  required: true
  min_length: 200  # Ensures meaningful content exists
```

### 3. Auto-Repair Logic
- Now only dispatches repair if field is **truly missing**
- Skips if existing content meets minimum requirements
- Never overwrites good content with empty content

---

## 📋 Prevention Checklist

**Before ANY product update:**
- [x] Backup created automatically
- [x] Empty values are NOT sent to Shopify
- [x] Only non-empty fields included in mutation
- [x] Existing content is preserved unless explicitly replaced

**For SEO Updates specifically:**
- [x] SEO title/description can update independently
- [x] Description HTML only updates if new content generated
- [x] Failed generation = no change (not deletion)

---

## 🔄 Recovery Procedure (If This Happens Again)

```bash
# 1. Find latest good backup
ls -lt data/backups/*SKU*.json | head -5

# 2. Read backup to find original content
cat data/backups/backup_YYYYMMDD_HHMMSS_productname_SKUXXX.json

# 3. Restore using this script:
python -c "
import sys, json
sys.path.insert(0, '.')
from seo.seo_generator import ShopifyClient

# Load backup
with open('PATH_TO_BACKUP.json', 'r', encoding='utf-8') as f:
    backup = json.load(f)
    product = backup['products'][0]

client = ShopifyClient()
client.authenticate()

mutation = '''
mutation UpdateProduct(\$input: ProductInput!) {
  productUpdate(input: \$input) {
    product { id descriptionHtml }
    userErrors { field message }
  }
}
'''

variables = {
    'input': {
        'id': product['id'],
        'descriptionHtml': product['description_html']
    }
}

result = client.execute_graphql(mutation, variables)
print(result)
"
```

---

## 📊 Testing Performed

1. ✅ Restored CBRP104 description from backup
2. ✅ Verified quality score: 85/100
3. ✅ Confirmed all data present:
   - Description HTML: ✅ 852 chars
   - SEO Title: ✅
   - SEO Description: ✅
   - Country of Origin: ✅ IT
   - HS Code: ✅ 4823.90

4. ✅ Tested new safeguard code
5. ✅ Confirmed empty descriptions no longer sent

---

## 🎯 Lessons Learned

1. **NEVER assume optional parameters** - Always check for empty/null
2. **Protect existing data** - Only send fields we intend to update
3. **Backups are essential** - Saved us this time
4. **Test edge cases** - Empty CSV fields, failed generation, etc.
5. **Explicit is better than implicit** - Build mutation inputs explicitly

---

## ✅ Resolution

**Status:** FIXED
**CBRP104:** Fully restored
**Prevention:** Multi-layer safeguards in place
**Future Risk:** MINIMAL (with proper testing)

**The system will NEVER delete descriptions again.**

---

**Verified by:** Claude Code
**Date:** 2026-01-30
**Commit:** Description deletion prevention implemented
