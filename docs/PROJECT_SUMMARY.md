# Shopify Multi-Supplier Scraper - Status Summary

## 🚀 Current Project State
The scraper tool is fully built, tested, and ready for production runs. The file system has been cleaned of debug artifacts.

## 🌐 NEW: Web App Available!
A **Shopify App** version is now available! See `README_APP.md` and `SETUP.md` for instructions on setting up the web interface.

## 🛠️ Main Scraper: `image_scraper.py`
This script handles automated data syncing from multiple suppliers to Shopify.

### **Features:**
- **Multi-Supplier Support**: Custom logic for:
  - **Aistcraft** (SI)
  - **Pentart** (HU)
  - **Ciao Bella** (IT)
  - **ITD Collection** (PL) - *Includes EAN/HS Code extraction*
  - **Paper Designs** (IT)
  - **FN Deco** (HU)
- **Shopify Sync**:
  - Uploads/Updates Images (cleans duplicates first).
  - Updates Costs (Kosten pro Artikel).
  - Updates Barcodes (only if different from SKU).
  - Sets Country of Origin & HS Code dynamically.
- **Resume Capability**: Skips SKU if already found in `push_proof.csv`.

### **How to Run:**
```bash
python image_scraper.py --live --csv products.csv
```

## 📂 Core Files
- `image_scraper.py`: The production script.
- `products.csv`: Your master product list (Needs `Handle`, `SKU`, `Vendor`).
- `push_proof.csv`: Success log and "Resume" state tracker.
- `.env`: API credentials and Shop Domain.

## ⚠️ Notes for Claude
- **Credentials**: Loaded via `.env` (SHOPIFY_CLIENT_ID, SHOPIFY_CLIENT_SECRET, SHOP_DOMAIN).
- **Security**: Paper Designs/FN Deco require a realistic 'User-Agent' (already implemented in `image_scraper.py`).
- **HS Codes**: Scripts use a dynamic mapping (~4823.90) but ITD pulls specific codes from titles.
