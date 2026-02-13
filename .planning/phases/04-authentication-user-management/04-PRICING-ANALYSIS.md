# Pricing Strategy Analysis: Shopify Multi-Supplier Platform

**Created:** 2026-02-09
**Purpose:** Comprehensive pricing analysis for SaaS launch
**Status:** Recommendation for Phase 4 Stripe implementation

---

## Executive Summary

**Your proposed pricing (€149-799/month) is 2-3x higher than the market will bear** for the German/Austrian e-commerce market. However, your product's unique value (conversational AI + intelligent automation) justifies **premium pricing** IF positioned correctly.

**Recommended approach:** Start at **€49-199/month** with usage-based components, then scale pricing as you prove ROI.

---

## Part 1: What You're ACTUALLY Building (Reality Check)

### Your Platform's Core Value

From your roadmap and PROJECT.md:

| Feature | Status | Competitive Advantage |
|---------|--------|----------------------|
| **Conversational AI Interface** (Phase 10) | ✅ Planned | Like ChatGPT for product management - NO competitor has this |
| **Intelligent Vendor Discovery** (Phase 2.1) | ✅ Built | Zero-config automation - learns from catalog |
| **AI-Powered Enrichment** (Phase 2.2) | ✅ Built | German SEO, attributes, quality scoring |
| **Multi-Tier AI Routing** (Phase 12) | ✅ Planned | Tier 1: LLM → Tier 2: Agentic → Tier 3: Full Agents |
| **Real-Time Progress Tracking** (Phase 9) | ✅ Planned | Live WebSocket updates |
| **Version History & Rollback** | ✅ Exists | Product change tracking |

**What makes you different:** The conversational AI interface. Competitors have **CSV uploads**. You have **"Hey, update these 50 SKUs from Pentart"** and it just works.

---

### Your Proposed Pricing vs Actual Features

| Your Proposed Feature | Reality from Roadmap | Issue |
|----------------------|---------------------|-------|
| "Manual CSV upload" (Basic tier) | You have **conversational AI** | ❌ Underselling your tech |
| "Customer configures field mapping" | You have **AI auto-mapping** | ❌ Underselling automation |
| "Automated supplier CSV syncs" (Pro) | You have **vendor discovery + scraping** | ❌ Missing the point |
| "Blog article generation" (Enterprise) | Not in roadmap (deferred) | ❌ Promising vaporware |
| "Analytics dashboard" (Enterprise) | Basic reporting only (v1.0) | ❌ Overpromising |

**Conclusion:** Your pricing tiers describe a **different product** than what you're building.

---

## Part 2: Competitive Landscape (Market Reality)

### Shopify App Pricing Benchmarks

From research, here's what competitors charge for **similar** automation:

| App | Monthly Price | Features | SKU Limit |
|-----|---------------|----------|-----------|
| Pricefy | $49-189/mo | Competitor price monitoring, auto-repricing, AI matching | 100-15K SKUs |
| Prisync AI | $100-200/mo | Price tracking, dynamic pricing | Channel-based |
| Bulk Product Editor (typical) | $9-49/mo | CSV import, field updates | Varies |
| Data Feed Watch (typical) | $39-299/mo | Product feed optimization | By channel |

**Key insight:** Premium Shopify apps rarely exceed **$299/month**. Your proposed €799 ($850) is in the stratosphere.

---

### SaaS Pricing Trends 2026

From SaaS Price Pulse Q1 2026:

1. **61% use usage-based pricing** (not flat subscription)
2. **38% faster revenue growth** for usage-based vs seat-based
3. **AI agent pricing**: $800-2000/month positioned as **FTE replacement**
4. **Outcome-based pricing**: Growing to 40% of enterprise SaaS

**Application to your product:**
- Your Tier 3 (Full Claude agents) COULD justify $500-800/month IF positioned as **replacing a data entry person** (€2,500/month salary)
- But you need usage-based component for lower tiers

---

## Part 3: Customer Willingness to Pay (Psychology)

### Your Target Market: German/Austrian Craft Stores

**Profile (from your context):**
- Small to medium businesses (500-5,000 SKUs)
- Tight margins (craft/hobby supplies)
- Tech-aware but not tech companies
- Compare to: Employee salary, not software cost

**Budget reality:**
- **€149/month** = €1,788/year = **0.5 FTE** month
- **€399/month** = €4,788/year = **1.3 FTE** months
- **€799/month** = €9,588/year = **2.6 FTE** months

**Question:** Does your software save 0.5-2.6 months of employee time per year?

**Answer:** YES - but you need to PROVE it.

---

### Time Saved Calculation (Your ROI)

Let's calculate actual time saved:

| Task | Manual Time | With Your Platform | Time Saved |
|------|-------------|-------------------|-----------|
| **Finding vendor product info** | 5 min/SKU × 100 SKUs = 8.3 hours | Auto-discovered | 8.3 hours |
| **Scraping product data** | 3 min/SKU × 100 SKUs = 5 hours | Automated | 5 hours |
| **Writing German SEO descriptions** | 10 min/SKU × 100 SKUs = 16.7 hours | AI-generated | 16.7 hours |
| **Image analysis + alt text** | 2 min/SKU × 100 SKUs = 3.3 hours | Vision AI | 3.3 hours |
| **Quality checking + approvals** | 1 min/SKU × 100 SKUs = 1.7 hours | Dry-run preview | 1 hour saved |
| **Total for 100 SKUs** | **35 hours** | **1 hour** (approval only) | **34 hours saved** |

**Monthly value (100 SKUs/month processed):**
- 34 hours × €25/hour labor cost = **€850/month saved**
- Justifies up to **€500/month pricing** (60% of savings)

**But:** Most stores process 20-50 SKUs/month, not 100.

---

## Part 4: Recommended Pricing Strategy

### Pricing Model: Hybrid (Base + Usage)

Based on 2026 SaaS trends, combine subscription + usage:

```
Monthly Fee (base platform access)
+
Usage Fee (per SKU processed with AI)
```

**Why this works:**
- Low barrier to entry (affordable base)
- Scales with value delivered (more SKUs = more savings)
- Aligns cost with ROI (customer only pays when getting value)

---

### Tier Structure: Align with YOUR Roadmap

Your roadmap defines tiers by **AI capability**, not feature lists:

| Tier | AI Engine | Your Roadmap | Pricing Strategy |
|------|-----------|-------------|------------------|
| **Tier 1** | OpenRouter LLM | Basic text generation | **Entry-level** |
| **Tier 2** | Agentic Workflows | Background jobs, parallel processing | **Professional** |
| **Tier 3** | Full Claude Agents + GSD | Conversational AI, autonomous tasks | **Premium/FTE Replacement** |

---

### RECOMMENDED: 3-Tier Pricing (v1.0 Launch)

#### Tier 1: Starter (€49/month)

**Target:** Solo store owners, 500-1,500 SKUs, testing the platform

**Base includes:**
- Up to **50 SKU updates/month** (usage limit)
- AI-powered vendor discovery
- Basic SEO generation (OpenRouter LLM)
- Manual approval workflow
- Email support (48-hour response)
- 1 connected supplier

**Overage:** €0.80 per additional SKU

**Why €49?**
- Competitive with Shopify apps ($39-69 range)
- Low enough for trial/test
- Covers infrastructure costs (AI API, hosting)

---

#### Tier 2: Professional (€149/month)

**Target:** Growing stores, 1,500-3,000 SKUs, want automation

**Base includes:**
- Up to **200 SKU updates/month**
- Everything in Starter, plus:
- **Agentic workflows** (Tier 2 AI from roadmap)
- Background job processing (Celery workers)
- Bulk operations (10-100 SKUs at once)
- Version history & rollback
- Priority support (24-hour response)
- Up to 5 connected suppliers

**Overage:** €0.60 per additional SKU

**Why €149?**
- Matches your original proposal
- Justifiable ROI (saves ~30 hours/month at 200 SKUs)
- Sweet spot for e-commerce SaaS

---

#### Tier 3: Enterprise (€399/month)

**Target:** Large catalogs, 3,000-5,000+ SKUs, want "digital employee"

**Base includes:**
- **Unlimited SKU updates** (fair use policy)
- Everything in Professional, plus:
- **Full Claude Code agents** (Tier 3 AI from roadmap)
- Conversational AI interface ("Update all Pentart products")
- API access for custom integrations
- Real-time progress tracking (WebSocket)
- White-glove onboarding (1-hour call)
- Dedicated support (4-hour response)
- Unlimited suppliers
- Early access to new features

**No overage** (unlimited usage)

**Why €399?**
- Positioned as **FTE replacement** (vs €2,500/month employee)
- Justified by conversational AI + full automation
- High enough to filter serious customers
- Room to scale to €599-799 after proving value

---

### NO Setup Fees (Initially)

**Your proposed:** €500-1,500 setup fees

**Recommended:** €0 setup fees for v1.0

**Why:**
- Your onboarding is **automated** (Phase 2.1: Auto-catalog analysis)
- Setup fees create friction (user hesitation)
- You're unproven (no customer testimonials yet)
- Competitors don't charge setup fees

**Exception:** Offer **optional** white-glove onboarding:
- €500 one-time for custom vendor configuration
- €1,000 one-time for historical data migration
- Only for Enterprise tier (upsell)

---

## Part 5: Feature Mapping (What's Actually in Each Tier)

### Tier 1: Starter (€49/month)

| Feature Category | What's Included | What's NOT |
|-----------------|-----------------|------------|
| **Product Updates** | Manual trigger via dashboard | ❌ Conversational AI |
| **Vendor Discovery** | Auto-discover from SKU | ❌ Multi-vendor batch |
| **SEO Generation** | Basic (OpenRouter Gemini Flash) | ❌ Premium models |
| **Image Analysis** | Vision AI (basic) | ❌ Bulk image replacement |
| **Approval** | Manual dry-run preview | ❌ Auto-approval rules |
| **Support** | Email (48h) | ❌ Priority support |

**User flow:**
1. Paste SKU in dashboard
2. System discovers vendor + scrapes
3. AI generates SEO content
4. User approves
5. Push to Shopify

---

### Tier 2: Professional (€149/month)

| Feature Category | What's Included | What's NOT |
|-----------------|-----------------|------------|
| **Product Updates** | Bulk operations (10-100 SKUs) | ❌ Conversational AI |
| **Vendor Discovery** | Multi-vendor parallel processing | ❌ Unlimited vendors |
| **SEO Generation** | Premium AI models (GPT-4) | ✅ Same |
| **Image Analysis** | Bulk Vision AI processing | ✅ Advanced |
| **Approval** | Approval rules + auto-apply | ✅ Automated |
| **Background Jobs** | Celery workers, queue system | ✅ Async |
| **Version History** | Full rollback capability | ✅ Essential |
| **Support** | Priority email (24h) | ❌ Chat/phone |

**User flow:**
1. Upload CSV with 50 SKUs
2. System processes in background
3. Real-time progress updates
4. Bulk approve or individual review
5. Scheduled push to Shopify

---

### Tier 3: Enterprise (€399/month)

| Feature Category | What's Included | Unique to Enterprise |
|-----------------|-----------------|---------------------|
| **Product Updates** | **Conversational AI** ("Update all Pentart") | ✅ Natural language |
| **Vendor Discovery** | Unlimited suppliers | ✅ Scale |
| **SEO Generation** | Best-in-class AI (Claude Opus if needed) | ✅ Premium |
| **Image Analysis** | Advanced Vision AI + transformations | ✅ Advanced |
| **Automation** | Full Claude Code agents + GSD skills | ✅ Autonomous |
| **API Access** | REST API for custom integrations | ✅ Developer |
| **Analytics** | Basic dashboard (catalog health, changes) | ✅ Insights |
| **Support** | Dedicated (4h response) + optional call | ✅ White-glove |

**User flow (conversational):**
```
User: "Update all products from Pentart supplier catalog"
AI: "Found 127 Pentart SKUs. Checking for price/stock changes..."
AI: "43 SKUs have updates. Here's a summary: [...]"
User: "Apply the changes"
AI: "Pushed to Shopify. Version saved for rollback."
```

---

## Part 6: Pricing Comparison (Yours vs Recommended)

| Metric | Your Proposal | Recommended | Difference |
|--------|--------------|-------------|------------|
| **Tier 1 Monthly** | €149 | €49 | **-67%** (too high) |
| **Tier 2 Monthly** | €399 | €149 | **-63%** (too high) |
| **Tier 3 Monthly** | €799 | €399 | **-50%** (too high) |
| **Setup Fees** | €500-1,500 | €0 | **-100%** (eliminate) |
| **Year 1 Cost (Tier 1)** | €1,788 | €588 | **-67%** |
| **Year 1 Cost (Tier 2)** | €5,288 | €1,788 | **-66%** |
| **Year 1 Cost (Tier 3)** | €11,088 | €4,788 | **-57%** |

**Why lower?**
1. You're **unproven** (no customers, testimonials, case studies)
2. Shopify app market norm is **$39-299/month**
3. Your Tier 1 has **fewer features** than proposed (no CSV, no manual config)
4. German/Austrian market is **price-sensitive**

**When to increase?**
- After 50 paying customers (social proof)
- After case studies showing ROI
- After Phase 10 (conversational AI) ships
- After analytics dashboard (Enterprise value-add)

---

## Part 7: Go-to-Market Pricing Strategy

### Phase 1: Launch Pricing (Months 1-6)

**Goal:** Acquire first 50 customers, prove ROI

| Tier | Monthly | Setup | Limit |
|------|---------|-------|-------|
| Starter | **€39** (launch discount) | €0 | 50 SKUs/mo |
| Professional | **€99** (launch discount) | €0 | 200 SKUs/mo |
| Enterprise | **€299** (launch discount) | €0 | Unlimited |

**Promotion:** "Early adopter pricing - lock in forever"

---

### Phase 2: Standard Pricing (Months 7-12)

**Goal:** Scale to 200 customers, increase ARPU

| Tier | Monthly | Setup | Limit |
|------|---------|-------|-------|
| Starter | **€49** | €0 | 50 SKUs/mo |
| Professional | **€149** | €0 | 200 SKUs/mo |
| Enterprise | **€399** | €0 | Unlimited |

**Grandfathering:** Early adopters keep launch pricing

---

### Phase 3: Premium Pricing (Year 2+)

**Goal:** Maximize revenue from proven value

| Tier | Monthly | Setup | Limit |
|------|---------|-------|-------|
| Starter | **€69** | €0 | 50 SKUs/mo |
| Professional | **€199** | €0 | 200 SKUs/mo |
| Enterprise | **€599** | €500 (optional white-glove) | Unlimited |

**Justification:** Conversational AI proven, customer ROI documented

---

## Part 8: Usage-Based Pricing Component

### Overage Pricing (Alternative Model)

If base subscriptions don't work, try:

**Model:** Pay per SKU processed (similar to Intercom's $0.99/resolution)

| What You Do | Cost | Rationale |
|------------|------|-----------|
| **SKU discovery + scraping** | €0.50/SKU | Replaces 5 min manual work (€2.08 labor) |
| **AI SEO generation** | €0.30/SKU | Replaces 10 min copywriting (€4.17 labor) |
| **Vision AI image analysis** | €0.20/SKU | Replaces 2 min image work (€0.83 labor) |
| **Total per SKU** | **€1.00/SKU** | Saves €7.08 in labor (86% savings) |

**Example bills:**
- 20 SKUs/month = €20/month
- 100 SKUs/month = €100/month
- 500 SKUs/month = €500/month

**Pros:**
- Perfect alignment with value delivered
- Scales with customer size
- No "unused subscription" waste

**Cons:**
- Unpredictable revenue (harder to forecast)
- Requires more complex billing (Stripe metered usage)

---

## Part 9: Competitive Positioning

### How to Justify Premium Pricing

Your proposed pricing IS achievable, but you need positioning:

| Instead of Saying | Say This |
|------------------|----------|
| "AI-powered field mapping" | **"Replaces 30 hours/month of data entry"** |
| "Automated supplier CSV syncs" | **"Your products update automatically while you sleep"** |
| "Blog article generation" | **"Never write product descriptions again"** (if you add this) |
| "Up to 5 suppliers" | **"Connect all your vendors - we auto-discover them"** |
| "€399/month" | **"Costs less than 1 day of employee time per month"** |

**Value anchor:** Compare to employee cost (€2,500/month), not software cost.

---

### Your Unique Selling Proposition (USP)

**What NO competitor has:**

1. **Conversational AI Interface** (Phase 10)
   - Competitor: Upload CSV, configure fields, pray
   - You: "Update all Pentart products" → Done

2. **Zero-Config Vendor Discovery** (Phase 2.1)
   - Competitor: Manually configure each supplier
   - You: Paste SKU → Auto-discovers vendor

3. **German E-Commerce Optimized** (Phase 2.2)
   - Competitor: Generic English content
   - You: Native German SEO, proper HS codes, Austrian conventions

4. **Intelligent AI Routing** (Phase 12)
   - Competitor: One AI model for everything
   - You: Tier 1 gets basic LLM, Tier 3 gets full Claude agents

**Positioning statement:**
> "The first AI assistant for Shopify product management. Just tell it what you need - no CSV uploads, no field mapping, no manual work. Built specifically for German-speaking e-commerce."

---

## Part 10: Final Recommendations

### ✅ DO THIS:

1. **Start at €49-399/month** (not €149-799)
2. **No setup fees** initially
3. **Align tiers with AI capabilities** (LLM → Agentic → Full Agents)
4. **Add usage-based component** (€0.60-0.80 per SKU overage)
5. **Position as FTE replacement** (save 30+ hours/month)
6. **Launch discount** (€39-299 for first 50 customers)
7. **Grandfather early adopters** (lock in low pricing)

### ❌ DON'T DO THIS:

1. ❌ Setup fees (automated onboarding)
2. ❌ Feature lists that don't match roadmap (blog generation, analytics v1.0)
3. ❌ Pricing above €400/month until proven (no social proof)
4. ❌ SKU limits (use overage pricing instead)
5. ❌ Long-term contracts (monthly only at first)

### 🎯 Pricing for Phase 4 Implementation

For **right now** (Phase 4 auth setup), configure Stripe with:

**Launch Pricing:**
- Tier 1: €39/month (`price_tier1_monthly`)
- Tier 2: €99/month (`price_tier2_monthly`)
- Tier 3: €299/month (`price_tier3_monthly`)

**Rationale:**
- Low barrier to entry
- You can raise prices later
- Easier to get first customers
- Validates product-market fit

---

## Decision Matrix

**Which pricing should we use for Phase 4 Stripe setup?**

### Option A: Conservative Launch (RECOMMENDED)
- Tier 1: €39/month
- Tier 2: €99/month
- Tier 3: €299/month
- No setup fees
- **Risk:** Low
- **Speed to first customer:** Fast
- **Revenue potential Year 1:** €10K-50K

### Option B: Your Original (High Risk)
- Tier 1: €149/month
- Tier 2: €399/month
- Tier 3: €799/month
- Setup fees: €500-1,500
- **Risk:** High (market rejection)
- **Speed to first customer:** Slow
- **Revenue potential Year 1:** €0-20K (few customers)

### Option C: Middle Ground
- Tier 1: €49/month
- Tier 2: €149/month
- Tier 3: €399/month
- No setup fees
- **Risk:** Medium
- **Speed to first customer:** Medium
- **Revenue potential Year 1:** €15K-75K

**Recommendation:** Start with **Option A** for Phase 4, then raise prices after proving value.

---

## Sources

- [Pricefy - Shopify App Store](https://apps.shopify.com/pricefy-io)
- [Prisync AI - Shopify App Store](https://apps.shopify.com/prisync-for-shopify)
- [SaaS Pricing Trends 2026](https://medium.com/@aymane.bt/the-future-of-saas-pricing-in-2026-an-expert-guide-for-founders-and-leaders-a8d996892876)
- [SaaS Price Pulse Q1 2026](https://www.saaspricepulse.com/reports/state-of-saas-pricing-q1-2026)
- [Best Pricing Optimization Apps For 2026 - Shopify](https://apps.shopify.com/categories/selling-products-pricing-pricing-optimization/all)

---

## Part 11: Stripe Setup Guide (Step-by-Step)

### Your Situation
- **Have:** Australian Business Number (ABN)
- **Location:** Currently in Austria
- **Need:** Stripe account for Phase 4 development

### Good News
You can start **immediately** with Stripe **test mode** - no business verification required. You'll develop and test Phase 4 entirely in test mode, then activate your account later when you're ready to go live.

---

### Step 1: Create Stripe Account (5 minutes)

#### Option A: Australian Business (Recommended)
Since you have an ABN, create account for Australia:

1. Go to: https://dashboard.stripe.com/register
2. Email: your-email@domain.com
3. Password: create secure password
4. **Country:** Select **Australia** (important!)
5. Click "Create account"

**Why Australia?**
- You have ABN (legal business entity)
- Can operate from anywhere in the world
- Stripe supports Australia fully

#### Option B: Austrian Business
Only if you plan to register a business in Austria:
- Would need Austrian business registration
- More complex if you're just visiting

**Recommendation:** Use Australia (your ABN).

---

### Step 2: Stay in Test Mode (No Verification Needed)

After creating account, you'll see this toggle:

```
[Test mode] ←→ [Live mode]
```

**Keep it on "Test mode"** - this gives you:
- ✅ Full Stripe API access
- ✅ Create products, test webhooks
- ✅ No business verification required
- ✅ Free forever (no fees)
- ❌ Can't accept real payments (test cards only)

**For Phase 4 development, test mode is perfect.**

---

### Step 3: Get API Keys (Test Mode)

1. In Stripe Dashboard, click **Developers** (top right)
2. Click **API keys** (left sidebar)
3. You'll see:

```
Publishable key: pk_test_51...
Secret key: sk_test_51...  [Reveal test key]
```

4. Click **"Reveal test key"** and copy both

#### Add to `.env`:

```bash
# Stripe (Test Mode)
STRIPE_SECRET_KEY=sk_test_51xxxxxxxxxxxxxxxxxxxxxxxxx
STRIPE_PUBLISHABLE_KEY=pk_test_51xxxxxxxxxxxxxxxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxxxxx  # We'll get this in Step 5
```

---

### Step 4: Create 3 Products (Your Tier System)

**Use the pricing you decided on** (Option A, B, or C from above).

#### Product 1: Tier 1 - Starter

1. Click **Products** (left sidebar)
2. Click **"+ Add product"**
3. Fill in:
   - **Name:** Tier 1 - Starter
   - **Description:** AI-powered vendor discovery with basic SEO generation
   - **Pricing:**
     - One time or recurring: **Recurring**
     - Price: **39** EUR (or your chosen price)
     - Billing period: **Monthly**
4. Click **"Save product"**
5. **IMPORTANT:** Copy the **Price ID** (starts with `price_`)
   - Example: `price_1QRs2LKZ3yF8nxM7AbCdEfGh`

#### Product 2: Tier 2 - Professional

Same steps, but:
- **Name:** Tier 2 - Professional
- **Description:** Agentic workflows with background job processing and bulk operations
- **Price:** 99 EUR / month (or your chosen price)
- **Copy the Price ID**

#### Product 3: Tier 3 - Enterprise

Same steps, but:
- **Name:** Tier 3 - Enterprise
- **Description:** Full Claude Code agents with conversational AI interface
- **Price:** 299 EUR / month (or your chosen price)
- **Copy the Price ID**

#### Add Price IDs to `.env`:

```bash
# Stripe Price IDs (Test Mode)
STRIPE_PRICE_TIER_1=price_xxxxxxxxxxxxxxxxxxxxxx
STRIPE_PRICE_TIER_2=price_xxxxxxxxxxxxxxxxxxxxxx
STRIPE_PRICE_TIER_3=price_xxxxxxxxxxxxxxxxxxxxxx
```

---

### Step 5: Set Up Webhook Endpoint

Webhooks tell your app when payments succeed.

#### A. Get ngrok (for local testing):

While developing locally, Stripe can't reach `localhost:5000`. Use ngrok to create a public URL:

```bash
# Install ngrok
# Windows: Download from https://ngrok.com/download
# Or use: choco install ngrok (if you have Chocolatey)

# Run ngrok (forwards Stripe webhooks to your local Flask)
ngrok http 5000
```

You'll get a URL like: `https://a1b2-c3d4.ngrok.io`

#### B. Create Webhook in Stripe:

1. In Stripe Dashboard: **Developers** → **Webhooks**
2. Click **"+ Add endpoint"**
3. **Endpoint URL:** `https://a1b2-c3d4.ngrok.io/webhooks/stripe`
   - (Replace with your ngrok URL + `/webhooks/stripe`)
4. **Events to send:** Click **"Select events"**, then add:
   - `checkout.session.completed`
   - `customer.subscription.updated`
   - `invoice.payment_failed`
5. Click **"Add endpoint"**
6. **Copy the "Signing secret"** (starts with `whsec_`)

#### Add to `.env`:

```bash
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxxxxxxxxxxxxx
```

---

### Step 6: Verify Your `.env` File

Your `.env` should now have:

```bash
# Email Service (Resend)
RESEND_API_KEY=re_S9S3FyU1_8m1GX3yZ4WSuMLiW7wp3eTRz
MAIL_FROM_ADDRESS=onboarding@resend.dev

# Stripe (Test Mode)
STRIPE_SECRET_KEY=sk_test_51xxxxxxxxxxxxxxxxxxxxxxxxx
STRIPE_PUBLISHABLE_KEY=pk_test_51xxxxxxxxxxxxxxxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxxxxx

# Stripe Price IDs
STRIPE_PRICE_TIER_1=price_xxxxxxxxxxxxxxxxxxxxxx
STRIPE_PRICE_TIER_2=price_xxxxxxxxxxxxxxxxxxxxxx
STRIPE_PRICE_TIER_3=price_xxxxxxxxxxxxxxxxxxxxxx

# Existing keys (from previous phases)
DB_PASSWORD=your-postgres-password
SHOPIFY_API_KEY=your-shopify-api-key
SHOPIFY_API_SECRET=your-shopify-api-secret
SECRET_KEY=your-flask-secret-key
```

---

### Step 7: Test Stripe Integration

Once Phase 4 is executed, test with Stripe's test cards:

**Successful payment:**
```
Card: 4242 4242 4242 4242
Expiry: Any future date (e.g., 12/34)
CVC: Any 3 digits (e.g., 123)
```

**Declined payment:**
```
Card: 4000 0000 0000 0002
```

Full list: https://stripe.com/docs/testing#cards

---

### Step 8: Later - Activate Live Mode (When Ready to Launch)

When you want to accept real payments, you'll need to:

1. **Switch to Live mode** in Stripe Dashboard
2. **Complete business verification:**
   - ABN (you have this ✓)
   - Business address (can be Australian address)
   - Bank account details (Australian bank for AUD payouts)
   - ID verification (passport/driver's license)
3. **Get new API keys** (live mode keys start with `sk_live_` and `pk_live_`)
4. **Update webhook endpoint** to production URL (not ngrok)

**For now, stay in test mode.** You can develop everything and only activate when you have real customers.

---

### Summary: What You Need Right Now

✅ **Have:**
- Australian ABN
- Email address
- Resend API key (already provided)

✅ **Do now (15 minutes):**
1. Create Stripe account (Australia)
2. Stay in test mode
3. Copy API keys → `.env`
4. Create 3 products (Tier 1/2/3)
5. Copy price IDs → `.env`
6. Install ngrok
7. Create webhook endpoint
8. Copy webhook secret → `.env`

✅ **Do later (when launching):**
- Complete business verification
- Add bank account
- Switch to live mode

---

*Document created: 2026-02-09*
*For Phase 4 Stripe configuration reference*
*Update this document as market feedback arrives*
