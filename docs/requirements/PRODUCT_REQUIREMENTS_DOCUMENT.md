# Product Requirements Document (PRD)
## Shopify Image Name Rewriting & Alt Text Optimization System

**Version:** 1.0
**Date:** 2026-01-29
**Status:** Phase 1 Complete, Phase 2 Planning
**Owner:** Development Team

---

## Executive Summary

This PRD outlines the comprehensive image management system for Shopify product uploads, focusing on SEO optimization, accessibility compliance, and automated image renaming capabilities. The system addresses critical gaps in the current implementation and establishes a foundation for scalable, vendor-specific image handling.

**Current Status:**
- ✅ Phase 1: Core infrastructure and critical fixes (COMPLETE)
- 🔄 Phase 2: Advanced features and optimization (IN PROGRESS)
- ⏳ Phase 3: Testing, monitoring, and vendor customization (PLANNED)

---

## 1. Problem Statement

### 1.1 Business Context
The Shopify scraping system handles product data from multiple suppliers (Pentart, Aistcraft, Ciao Bella, ITD, etc.). Images are downloaded from supplier websites and uploaded to Shopify, but the current implementation has several critical issues:

### 1.2 Critical Issues Identified

**Issue #1: Broken Import Dependencies** (SEVERITY: CRITICAL)
- `app.py` imports `clean_product_name()` from `image_scraper.py`
- Function only exists in backup file, causing import failure
- Blocks all image upload operations via Flask app
- **Status:** ✅ RESOLVED

**Issue #2: No Image Filename Control** (SEVERITY: HIGH)
- Shopify keeps original supplier filenames from URLs
- Filenames contain UUIDs, random strings, non-SEO patterns
- Example: `product-abc-uuid-12345-temp.jpg` instead of `pentart-acrylic-paint-r0530.jpg`
- **Status:** ✅ RESOLVED (using `fileUpdate` mutation)

**Issue #3: Poor Alt Text Quality** (SEVERITY: MEDIUM)
- Alt text includes technical codes (UUIDs, HS codes, SKUs)
- No length validation (SEO best practice: 125 chars)
- Contains redundant phrases ("image of", "picture of")
- Example: "Pentart Acrylic Paint_8a4d9e6f-1234 HS code 3210 R0530"
- **Status:** ✅ RESOLVED

**Issue #4: Missing SEO Best Practices** (SEVERITY: MEDIUM)
- No lowercase normalization (case-sensitive URLs)
- No filename length limits (Windows 260-char path limit)
- Inconsistent naming patterns across vendors
- No keyword optimization strategy
- **Status:** ⚠️ PARTIALLY RESOLVED

**Issue #5: Incomplete Code Migration** (SEVERITY: HIGH)
- Advanced features exist in `.backup` file but not in production
- `ShopifyClient` class missing from active code
- Support functions (`load_processed_skus`, `clean_sku`, etc.) missing
- **Status:** ✅ RESOLVED

---

## 2. Goals & Success Metrics

### 2.1 Primary Goals

1. **Improve SEO Performance**
   - Target: 100% of images have SEO-friendly filenames
   - Target: 100% of images have clean, descriptive alt text
   - Target: Average alt text length: 80-125 characters

2. **Ensure Accessibility Compliance**
   - Target: 100% of images have meaningful alt text
   - Target: Zero redundant phrases in alt text
   - Target: WCAG 2.1 Level AA compliance

3. **Enable Operational Scalability**
   - Target: Support 5+ vendors with custom naming patterns
   - Target: Process 1000+ products without manual intervention
   - Target: <2 seconds per image upload+rename operation

4. **Maintain System Reliability**
   - Target: 99% upload success rate
   - Target: Graceful degradation if rename fails
   - Target: Comprehensive error logging

### 2.2 Success Metrics (KPIs)

**Technical Metrics:**
- Image upload success rate: ≥99%
- Image rename success rate: ≥95%
- Alt text validation pass rate: ≥98%
- Average processing time: ≤2s per image

**Business Metrics:**
- SEO score improvement: +20% for product images
- Accessibility audit score: ≥95/100
- Manual intervention rate: ≤2% of uploads
- Support ticket reduction: -30% for image issues

**Quality Metrics:**
- Filename format compliance: 100%
- Alt text length compliance: ≥95% within target range
- Special character removal: 100%
- Duplicate filename prevention: 100%

---

## 3. User Stories & Use Cases

### 3.1 Primary User: Operations Manager

**Story 1: Bulk Product Upload**
```
AS AN operations manager
I WANT to upload 500 Pentart products with images
SO THAT they appear in Shopify with SEO-optimized filenames and alt text
WITHOUT manual editing of each image
```

**Acceptance Criteria:**
- ✅ All 500 images upload successfully
- ✅ Filenames follow pattern: `{product-name}_{sku}.jpg`
- ✅ Alt text is clean (no UUIDs, HS codes)
- ✅ Process completes in <20 minutes
- ✅ Failure report shows any issues

**Story 2: Multi-Vendor Processing**
```
AS AN operations manager
I WANT to process products from different vendors (Pentart, Aistcraft, ITD)
SO THAT each vendor's images follow their specific naming conventions
WITHOUT changing code or configurations manually
```

**Acceptance Criteria:**
- ⏳ Vendor-specific naming patterns configured
- ⏳ Automatic vendor detection from product data
- ⏳ Custom alt text templates per vendor
- ⏳ Validation rules per vendor

### 3.2 Secondary User: SEO Specialist

**Story 3: Alt Text Optimization**
```
AS AN SEO specialist
I WANT all product images to have keyword-rich alt text
SO THAT our products rank higher in Google Image Search
AND we improve overall page SEO scores
```

**Acceptance Criteria:**
- ✅ Alt text contains primary product keywords
- ⏳ Alt text includes category terms when relevant
- ⏳ Alt text follows 80-125 character guideline
- ⏳ Analytics integration to track image search performance

**Story 4: Quality Assurance**
```
AS AN SEO specialist
I WANT to audit a sample of uploaded images
SO THAT I can verify they meet SEO and accessibility standards
WITHOUT manually checking Shopify admin for each product
```

**Acceptance Criteria:**
- ⏳ Automated quality report generation
- ⏳ Sample audit of 10% of uploads
- ⏳ Alt text scoring system
- ⏳ Filename compliance verification

### 3.3 Tertiary User: Developer

**Story 5: Error Troubleshooting**
```
AS A developer
I WANT detailed logs when image uploads or renames fail
SO THAT I can quickly diagnose and fix issues
WITHOUT spending hours debugging
```

**Acceptance Criteria:**
- ✅ Structured logging with timestamps
- ⏳ Error categorization (upload vs rename vs validation)
- ⏳ Stack traces for exceptions
- ⏳ Correlation IDs for tracking individual products

---

## 4. Functional Requirements

### 4.1 Image Filename Generation (PHASE 1 ✅)

**FR-1.1: Filename Sanitization**
- ✅ Remove special characters (regex-based)
- ✅ Replace spaces with underscores
- ✅ Convert to lowercase
- ✅ Remove multiple consecutive underscores
- ✅ Limit length to 200 characters

**FR-1.2: Filename Pattern**
- ✅ Format: `{product_name}_{sku}.{extension}`
- ✅ Product name: cleaned, sanitized title
- ✅ SKU: lowercase, sanitized
- ✅ Extension: matches original file type

**FR-1.3: Duplicate Prevention**
- ✅ Multiple images: `{product_name}_{sku}_1.jpg`, `_2.jpg`, etc.
- ⏳ Cross-product duplicate detection
- ⏳ Automatic suffix increment if collision detected

### 4.2 Alt Text Generation (PHASE 1 ✅)

**FR-2.1: Alt Text Cleaning**
- ✅ Remove UUID patterns
- ✅ Remove HS code patterns
- ✅ Remove SKU patterns from end of title
- ✅ Remove redundant phrases ("image of", "picture of")
- ✅ Normalize whitespace

**FR-2.2: Alt Text Validation**
- ✅ Maximum length: 512 characters (Shopify limit)
- ✅ Target length: 125 characters (SEO best practice)
- ✅ Truncate at word boundary if too long
- ✅ Warning if exceeds target length
- ✅ Error if empty or None

**FR-2.3: Alt Text Enhancement (PHASE 2 ⏳)**
- ⏳ Keyword injection based on product category
- ⏳ Multilingual support (German translation)
- ⏳ Vendor-specific templates
- ⏳ A/B testing different alt text formats

### 4.3 Shopify Integration (PHASE 1 ✅)

**FR-3.1: Image Upload**
- ✅ GraphQL `productCreateMedia` mutation
- ✅ Upload by URL (from supplier sites)
- ✅ Alt text included in upload
- ✅ Media ID captured in response

**FR-3.2: Image Renaming**
- ✅ GraphQL `fileUpdate` mutation
- ✅ Rename after successful upload
- ✅ Batch processing (max 25 files)
- ✅ Extension validation (must match original)

**FR-3.3: Error Handling**
- ✅ Graceful degradation if rename fails
- ✅ Upload succeeds even if rename fails
- ✅ Detailed error messages
- ✅ User-friendly status reporting

### 4.4 Vendor-Specific Logic (PHASE 2 ⏳)

**FR-4.1: Vendor Detection**
- ⏳ Automatic detection from product vendor field
- ⏳ Vendor normalization (case-insensitive)
- ⏳ Default vendor if not specified

**FR-4.2: Vendor Configurations**
- ⏳ Custom filename patterns per vendor
- ⏳ Custom alt text templates per vendor
- ⏳ Vendor-specific HS code mappings
- ⏳ Vendor-specific keyword lists

**FR-4.3: Vendor Examples**
```yaml
vendors:
  pentart:
    filename_pattern: "{category}_{product_name}_{sku}"
    alt_text_template: "{product_name} - {category} by Pentart"
    country_of_origin: "HU"

  aistcraft:
    filename_pattern: "{product_name}_{sku}_aistcraft"
    alt_text_template: "{product_name} - Aistcraft"
    country_of_origin: "SI"
```

---

## 5. Technical Requirements

### 5.1 System Architecture

**Components:**
1. **Image Scraper Module** (`image_scraper.py`)
   - Core helper functions
   - ShopifyClient class
   - Vendor scraper stubs

2. **Image Upload Script** (`push_images_only.py`)
   - Batch upload from CSV
   - Progress tracking
   - Results export

3. **Flask Application** (`app.py`)
   - Web-based product management
   - OAuth integration
   - Job queue system

### 5.2 Dependencies

**Required Libraries:**
```python
# Core
requests>=2.31.0
python-dotenv>=1.0.0
pandas>=2.0.0

# Web scraping
beautifulsoup4>=4.12.0
selenium>=4.0.0
webdriver-manager>=4.0.0

# Optional (for advanced features)
python-slugify>=8.0.0  # SEO-friendly slugs
deep-translator>=1.11.0  # Multilingual support
pillow>=10.0.0  # Image analysis
```

### 5.3 API Requirements

**Shopify GraphQL API:**
- Version: 2024-01 or later
- Required scopes: `read_products`, `write_products`
- Rate limits: 50 requests/second (standard)

**Required Mutations:**
- ✅ `productCreateMedia` - Upload images
- ✅ `fileUpdate` - Rename images
- ✅ `productVariantsBulkUpdate` - Update variants
- ✅ `productDeleteMedia` - Delete images

**Required Queries:**
- ✅ `products` - Fetch products by SKU
- ✅ `product.media` - Check existing images

### 5.4 Performance Requirements

**Throughput:**
- Target: 30 images/minute (2s per image)
- Batch size: 25 images per `fileUpdate` mutation
- Concurrent uploads: 5 products in parallel

**Latency:**
- Upload: <1s average
- Rename: <500ms average
- Total: <2s per image (upload + rename)

**Scalability:**
- Support: 10,000+ products
- Support: 50,000+ images
- Support: 10+ concurrent workers

### 5.5 Data Requirements

**Input Data (CSV):**
```csv
SKU,Handle,Title,ImageURL,Vendor
R0530,pentart-paint,Pentart Acrylic Paint,https://...,Pentart
```

**Output Data (Success Log):**
```csv
SKU,Handle,Status,Filename,AltText,Timestamp,ErrorMessage
R0530,pentart-paint,Success,pentart_acrylic_paint_r0530.jpg,Pentart Acrylic Paint,2026-01-29 10:30:00,
```

### 5.6 Security Requirements

**API Credentials:**
- ⏳ Store in environment variables (`.env`)
- ⏳ Never commit credentials to Git
- ⏳ Rotate OAuth tokens every 90 days
- ⏳ Use separate credentials for dev/prod

**Data Privacy:**
- ⏳ No customer data in logs
- ⏳ No API tokens in error messages
- ⏳ Sanitize URLs in logs (remove query params)

---

## 6. Non-Functional Requirements

### 6.1 Reliability
- ✅ Graceful degradation (upload succeeds even if rename fails)
- ⏳ Automatic retry on transient failures (3 attempts)
- ⏳ Exponential backoff for rate limiting
- ⏳ Circuit breaker for API failures

### 6.2 Maintainability
- ✅ Comprehensive docstrings for all functions
- ✅ Type hints for function signatures
- ⏳ Unit tests (80% code coverage target)
- ⏳ Integration tests for API calls
- ⏳ Documentation for all vendor configurations

### 6.3 Observability
- ✅ Structured logging (timestamp, level, message)
- ⏳ Progress indicators for batch operations
- ⏳ Metrics collection (upload rate, error rate)
- ⏳ Alerting for critical failures

### 6.4 Usability
- ✅ Clear error messages for users
- ✅ Status reporting during batch operations
- ⏳ Web UI for monitoring job progress
- ⏳ Email notifications for job completion

---

## 7. Implementation Roadmap

### PHASE 1: Core Infrastructure ✅ COMPLETE
**Duration:** Complete
**Status:** ✅ All items complete

- ✅ Add `clean_product_name()` to `image_scraper.py`
- ✅ Enhance `get_valid_filename()` with lowercase, length limits
- ✅ Add `validate_alt_text()` function
- ✅ Implement `fileUpdate` mutation in ShopifyClient
- ✅ Add missing imports for `app.py` compatibility
- ✅ Update `push_images_only.py` with auto-rename
- ✅ Create comprehensive documentation

**Deliverables:**
- ✅ Working image upload + rename system
- ✅ Alt text cleaning and validation
- ✅ Implementation summary document
- ✅ Test script for verification

---

### PHASE 2: Advanced Features & Optimization 🔄 IN PROGRESS
**Duration:** 5-7 days
**Status:** Planning

#### 2.1 Vendor Configuration System (HIGH PRIORITY)
- ⏳ Create `vendor_configs.yaml` for vendor-specific settings
- ⏳ Implement vendor detection from product data
- ⏳ Add vendor-specific filename patterns
- ⏳ Add vendor-specific alt text templates
- ⏳ Expand HS code mapping per vendor

#### 2.2 Keyword Optimization (MEDIUM PRIORITY)
- ⏳ Keyword injection in alt text based on category
- ⏳ Keyword scoring algorithm
- ⏳ A/B testing framework for alt text variations
- ⏳ Analytics integration to track performance

#### 2.3 Multilingual Support (MEDIUM PRIORITY)
- ⏳ Activate German translation (from backup)
- ⏳ Add language detection
- ⏳ Generate multilingual alt text
- ⏳ Support multilingual filenames (slugified)

#### 2.4 Image Quality Analysis (LOW PRIORITY)
- ⏳ Image dimension validation
- ⏳ Image format optimization (WebP conversion)
- ⏳ Image compression before upload
- ⏳ Alt text scoring based on image content

---

### PHASE 3: Testing & Quality Assurance ⏳ PLANNED
**Duration:** 3-5 days
**Status:** Not started

#### 3.1 Unit Testing
- ⏳ Test `clean_product_name()` - all edge cases
- ⏳ Test `get_valid_filename()` - length limits, special chars
- ⏳ Test `validate_alt_text()` - validation rules
- ⏳ Test ShopifyClient methods (mocked API)
- ⏳ Target: 80% code coverage

#### 3.2 Integration Testing
- ⏳ Test full upload+rename workflow
- ⏳ Test batch processing (100+ products)
- ⏳ Test error handling (network failures, API errors)
- ⏳ Test vendor-specific configurations

#### 3.3 Performance Testing
- ⏳ Load test: 1000 products in parallel
- ⏳ Measure: throughput, latency, error rate
- ⏳ Identify bottlenecks
- ⏳ Optimize critical paths

#### 3.4 User Acceptance Testing (UAT)
- ⏳ Operations team tests bulk upload
- ⏳ SEO team audits sample of images
- ⏳ Verify Shopify admin shows correct filenames
- ⏳ Verify alt text in page source

---

### PHASE 4: Monitoring & Maintenance ⏳ PLANNED
**Duration:** Ongoing
**Status:** Not started

#### 4.1 Monitoring Setup
- ⏳ CloudWatch/DataDog integration
- ⏳ Custom metrics dashboard
- ⏳ Alert rules for critical failures
- ⏳ Weekly performance reports

#### 4.2 Maintenance Tasks
- ⏳ Monthly review of error logs
- ⏳ Quarterly update of HS code mappings
- ⏳ Quarterly review of vendor configurations
- ⏳ Annual security audit

---

## 8. Open Questions & Decisions Needed

### 8.1 Vendor Configurations
**Question:** Should vendor configurations be in YAML file or database?
**Options:**
1. YAML file (`vendor_configs.yaml`) - Simple, version-controlled
2. Database table - Dynamic, admin UI possible
3. Hybrid - YAML for defaults, DB for overrides

**Recommendation:** Start with YAML, migrate to DB if needed

---

### 8.2 Image Optimization
**Question:** Should we optimize/compress images before upload?
**Pros:**
- Faster page load times
- Reduced storage costs
- Better mobile experience

**Cons:**
- Adds processing time
- Requires image processing library (Pillow)
- May reduce image quality

**Recommendation:** Phase 2 feature, opt-in per vendor

---

### 8.3 Multilingual Alt Text
**Question:** How to handle multilingual alt text for German market?
**Options:**
1. Translate all alt text to German
2. Provide both English and German (meta field)
3. Auto-detect market and use appropriate language

**Recommendation:** Option 3 - detect from Shopify market settings

---

### 8.4 Scraper Implementation
**Question:** `scrape_product_info()` is currently a stub. What vendors need scrapers?
**Priority:**
1. Pentart (HU) - Database exists, scraper fallback needed
2. Aistcraft (SI) - Scraper exists in backup
3. Ciao Bella (IT) - Needs implementation
4. ITD (PL) - Needs implementation

**Recommendation:** Migrate scrapers from backup, prioritize by volume

---

## 9. Risks & Mitigations

### 9.1 Technical Risks

**Risk: Shopify API Rate Limiting**
- Probability: Medium
- Impact: High
- Mitigation: Implement exponential backoff, batch processing, rate limiting tracker

**Risk: fileUpdate Mutation Fails**
- Probability: Low
- Impact: Medium
- Mitigation: ✅ Graceful degradation (upload still succeeds)

**Risk: Filename Extension Mismatch**
- Probability: Low
- Impact: Medium
- Mitigation: ✅ Extension validation before rename, preserve original extension

### 9.2 Business Risks

**Risk: SEO Impact During Migration**
- Probability: Low
- Impact: High
- Mitigation: Phased rollout, monitor search rankings, rollback plan

**Risk: Vendor Changes Website Structure**
- Probability: Medium
- Impact: Medium
- Mitigation: Scraper health checks, fallback to manual upload, vendor alerts

### 9.3 Operational Risks

**Risk: Large Batch Failures**
- Probability: Medium
- Impact: High
- Mitigation: Checkpoint system, resume from failure, detailed error logs

---

## 10. Success Criteria & Validation

### 10.1 Phase 1 Success Criteria ✅ COMPLETE
- ✅ All imports from `app.py` work without errors
- ✅ Images upload with cleaned alt text
- ✅ Images rename to SEO-friendly filenames
- ✅ No regressions in existing functionality
- ✅ Documentation complete

### 10.2 Phase 2 Success Criteria (Targets)
- Vendor configurations support 5+ vendors
- Alt text quality score ≥85/100 (automated scoring)
- Filename compliance: 100%
- Processing speed: ≥30 images/minute
- Error rate: ≤5%

### 10.3 Phase 3 Success Criteria (Targets)
- Unit test coverage: ≥80%
- Integration test coverage: ≥60%
- UAT approval from operations and SEO teams
- Performance benchmark: 1000 products in ≤35 minutes

---

## 11. Appendices

### Appendix A: Filename Examples

**Before Implementation:**
```
original-supplier-filename-uuid-abc123.jpg
product_8a4d9e6f-1234-5678-9012-abcdef123456.jpg
tmpimg_3210_random.jpg
```

**After Implementation:**
```
pentart_acrylic_paint_r0530.jpg
aistcraft_rice_paper_tag123.jpg
ciao_bella_napkin_cb456.jpg
```

### Appendix B: Alt Text Examples

**Before Implementation:**
```
Pentart Acrylic Paint_8a4d9e6f-1234-5678 (HS code 3210) R0530
Image of Rice Paper TAG123 HS: 48021000
Picture of product
```

**After Implementation:**
```
Pentart Acrylic Paint
Rice Paper for Decoupage
Decorative Napkin with Floral Pattern
```

### Appendix C: API Mutation Examples

**fileUpdate Mutation:**
```graphql
mutation fileUpdate($files: [FileUpdateInput!]!) {
  fileUpdate(files: $files) {
    files {
      id
      ... on MediaImage {
        image { url }
      }
    }
    userErrors { field message }
  }
}
```

**Variables:**
```json
{
  "files": [
    {
      "id": "gid://shopify/MediaImage/123456789",
      "filename": "pentart_acrylic_paint_r0530.jpg"
    }
  ]
}
```

---

## 12. Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-29 | Claude Code | Initial PRD creation |
| | | | Phase 1 complete, Phases 2-4 planned |

---

## 13. Approval & Sign-off

**Prepared By:** Claude Code (Claude Sonnet 4.5)
**Review Required:** Product Owner, Development Lead, SEO Team
**Approval Status:** Draft - Pending Review

---

**END OF DOCUMENT**
