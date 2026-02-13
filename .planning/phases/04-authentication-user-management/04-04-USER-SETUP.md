# Phase 04-04: User Setup Required

**Generated:** 2026-02-09
**Phase:** 04-authentication-user-management
**Status:** Incomplete

Complete these items for Stripe Checkout to function. Claude automated everything possible; these items require human access to external dashboards/accounts.

## Environment Variables

| Status | Variable | Source | Add to |
|--------|----------|--------|--------|
| [ ] | `STRIPE_SECRET_KEY` | Stripe Dashboard -> Developers -> API keys -> Secret key | `.env` |
| [ ] | `STRIPE_PUBLISHABLE_KEY` | Stripe Dashboard -> Developers -> API keys -> Publishable key | `.env` |
| [ ] | `STRIPE_PRICE_TIER_1` | Stripe Dashboard -> Products -> Tier 1 -> Price ID | `.env` |
| [ ] | `STRIPE_PRICE_TIER_2` | Stripe Dashboard -> Products -> Tier 2 -> Price ID | `.env` |
| [ ] | `STRIPE_PRICE_TIER_3` | Stripe Dashboard -> Products -> Tier 3 -> Price ID | `.env` |

## Account Setup

- [ ] **Create Stripe account**
  - URL: https://dashboard.stripe.com/register
  - Skip if: Already have a Stripe account

## Dashboard Configuration

- [ ] **Create 3 Products (Tier 1, Tier 2, Tier 3) with monthly prices**
  - Location: Stripe Dashboard -> Products
  - Copy Price IDs into `STRIPE_PRICE_TIER_1/2/3`

## Verification

After completing setup, verify with:

```bash
python -c "import os; print('stripe keys set' if os.getenv('STRIPE_SECRET_KEY') else 'missing')"
```

Expected results:
- Output indicates Stripe keys are set.

---

**Once all items complete:** Mark status as "Complete" at top of file.
