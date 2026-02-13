# Phase 04-03: User Setup Required

**Generated:** 2026-02-09
**Phase:** 04-authentication-user-management
**Status:** Incomplete

Complete these items for the email verification flow to work. Claude automated everything possible; these items require human access to external dashboards/accounts.

## Environment Variables

| Status | Variable | Source | Add to |
|--------|----------|--------|--------|
| [ ] | `MAIL_SERVER` | Resend: smtp.resend.com or SendGrid: smtp.sendgrid.net | `.env` |
| [ ] | `MAIL_PORT` | 587 (TLS) | `.env` |
| [ ] | `MAIL_USERNAME` | Resend: `resend` or SendGrid: `apikey` | `.env` |
| [ ] | `MAIL_PASSWORD` | Resend/SendGrid Dashboard -> API Keys | `.env` |
| [ ] | `MAIL_DEFAULT_SENDER` | Verified sender email (e.g., noreply@yourdomain.com) | `.env` |

## Account Setup

- [ ] **Create Resend or SendGrid account**
  - URL: https://resend.com/ or https://sendgrid.com/
  - Skip if: Already have an account

## Dashboard Configuration

- [ ] **Verify sender domain or email**
  - Location: Resend/SendGrid Dashboard -> Domain/Sender verification
  - Set to: Verified sender for `MAIL_DEFAULT_SENDER`

## Verification

After completing setup, verify with:

```bash
python -c "from src.config.email_config import configure_mail, mail; print('Email config OK')"
```

Expected results:
- Imports succeed with no missing env var errors.

---

**Once all items complete:** Mark status as "Complete" at top of file.
