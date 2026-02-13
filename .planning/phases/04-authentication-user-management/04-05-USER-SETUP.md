# Phase 04-05: User Setup Required

**Generated:** 2026-02-09
**Phase:** 04-authentication-user-management
**Status:** Incomplete

Complete these items for Stripe webhooks to work. Claude automated everything possible; these items require human access to external dashboards/accounts.

## Environment Variables

| Status | Variable | Source | Add to |
|--------|----------|--------|--------|
| [ ] | `STRIPE_WEBHOOK_SECRET` | Stripe Dashboard -> Developers -> Webhooks -> Signing secret | `.env` |

## Dashboard Configuration

- [ ] **Create webhook endpoint**
  - Location: Stripe Dashboard -> Developers -> Webhooks
  - Endpoint URL: `https://<your-domain>/webhooks/stripe`
  - Events to send:
    - `checkout.session.completed`
    - `customer.subscription.updated`
    - `invoice.payment_failed`

## Verification

After completing setup, verify with:

```bash
curl -X POST http://localhost:5000/webhooks/stripe \
  -H "Content-Type: application/json" \
  -d '{}'
```

Expected results:
- Returns 400 "Missing signature" or "Invalid signature" (signature verification active).

---

**Once all items complete:** Mark status as "Complete" at top of file.
