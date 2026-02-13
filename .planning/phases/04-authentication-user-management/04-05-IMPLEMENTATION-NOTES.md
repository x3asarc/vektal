# Phase 04-05: Stripe Webhook Implementation - Current Status

**Date:** 2026-02-09
**Status:** Webhook endpoint created, business logic TODO

## ✅ What's Already Done

### 1. Environment Configuration
All Stripe configuration is complete in `.env`:
```env
# Stripe API Keys
STRIPE_PUBLISHABLE_KEY=pk_test_51Syt0fCN57zeXuXZ...
STRIPE_SECRET_KEY=sk_test_51Syt0fCN57zeXuXZ...
STRIPE_WEBHOOK_SECRET=whsec_ae09eef05e1aa9f7200d9386809164e88820a67f12a08cd30947cfb42ea844b

# Stripe Product IDs (for tier mapping)
STRIPE_PRODUCT_1_ID=prod_Twn3pXdZWZJj4G  # Tier 1
STRIPE_PRODUCT_2_ID=prod_Twn6MWTfgCLxvz  # Tier 2
STRIPE_PRODUCT_3_ID=prod_Twn6Z73AhYmT9S  # Tier 3

# Email Service (for verification emails)
RESEND_API_KEY=re_S9S3FyU1_8m1GX3yZ4WSuMLiW7wp3eTRz
```

### 2. Webhook Endpoint Created
Location: `src/app.py` lines 213-307

**Route:** `/webhooks/stripe` (POST)

**Features:**
- ✅ Stripe signature verification
- ✅ Event type routing
- ✅ Error handling with logging
- ✅ 6 event handlers (skeleton code)

**Events Handled:**
1. `checkout.session.completed` - Payment successful
2. `customer.subscription.created` - New subscription
3. `customer.subscription.updated` - Tier changes
4. `customer.subscription.deleted` - Cancellation
5. `invoice.payment_succeeded` - Successful billing
6. `invoice.payment_failed` - Payment failure

### 3. Local Testing Setup Complete
- ✅ Stripe CLI installed and authenticated
- ✅ Webhook forwarding working: `stripe-webhook-local.bat`
- ✅ Test suite created: `test-stripe-webhooks.bat`
- ✅ All 6 events tested and arriving at endpoint

## 🚧 What Needs Implementation

The webhook handlers currently have `TODO` comments. Here's what needs to be implemented:

### Event 1: `checkout.session.completed`
**Purpose:** Create user account after successful payment

**TODO Implementation:**
```python
# Extract data from session
customer_email = session.get('customer_email')
customer_id = session.get('customer')
subscription_id = session.get('subscription')
metadata = session.get('metadata', {})

# Get product ID from subscription to determine tier
subscription = stripe.Subscription.retrieve(subscription_id)
product_id = subscription['items']['data'][0]['price']['product']

# Map product ID to tier
tier_mapping = {
    os.getenv('STRIPE_PRODUCT_1_ID'): UserTier.TIER_1,
    os.getenv('STRIPE_PRODUCT_2_ID'): UserTier.TIER_2,
    os.getenv('STRIPE_PRODUCT_3_ID'): UserTier.TIER_3,
}
tier = tier_mapping.get(product_id, UserTier.TIER_1)

# Create user with PENDING_OAUTH status
from src.models.user import User, AccountStatus
from src.auth.email_verification import generate_verification_token, generate_verification_url
from src.auth.email_sender import send_verification_email, send_welcome_email

user = User(
    email=customer_email,
    password_hash=metadata.get('password_hash', 'oauth-user'),  # From checkout metadata
    tier=tier,
    account_status=AccountStatus.PENDING_OAUTH,
    email_verified=False,
    stripe_customer_id=customer_id,
    stripe_subscription_id=subscription_id,
    oauth_completion_deadline=datetime.utcnow() + timedelta(days=7),  # 7-day grace period
    billing_period_start=datetime.utcnow(),
    billing_period_end=datetime.utcnow() + timedelta(days=30)
)

db.session.add(user)
db.session.commit()

# Generate verification token
verification_url = generate_verification_url(customer_email)

# Send emails
send_verification_email(customer_email, verification_url)
send_welcome_email(customer_email, f"{request.host_url}dashboard")
```

### Event 2: `customer.subscription.created`
**Purpose:** Set billing period and tier assignment

**TODO Implementation:**
```python
customer_id = subscription.get('customer')
subscription_id = subscription.get('id')
current_period_start = datetime.fromtimestamp(subscription.get('current_period_start'))
current_period_end = datetime.fromtimestamp(subscription.get('current_period_end'))
product_id = subscription['items']['data'][0]['price']['product']

# Find user by Stripe customer ID
user = User.query.filter_by(stripe_customer_id=customer_id).first()
if user:
    # Map product to tier
    tier_mapping = {
        os.getenv('STRIPE_PRODUCT_1_ID'): UserTier.TIER_1,
        os.getenv('STRIPE_PRODUCT_2_ID'): UserTier.TIER_2,
        os.getenv('STRIPE_PRODUCT_3_ID'): UserTier.TIER_3,
    }
    user.tier = tier_mapping.get(product_id, UserTier.TIER_1)
    user.stripe_subscription_id = subscription_id
    user.billing_period_start = current_period_start
    user.billing_period_end = current_period_end
    db.session.commit()
```

### Event 3: `customer.subscription.updated`
**Purpose:** Handle tier upgrades and downgrades

**TODO Implementation:**
```python
customer_id = subscription.get('customer')
status = subscription.get('status')
product_id = subscription['items']['data'][0]['price']['product']

user = User.query.filter_by(stripe_customer_id=customer_id).first()
if user:
    # Determine new tier
    tier_mapping = {
        os.getenv('STRIPE_PRODUCT_1_ID'): UserTier.TIER_1,
        os.getenv('STRIPE_PRODUCT_2_ID'): UserTier.TIER_2,
        os.getenv('STRIPE_PRODUCT_3_ID'): UserTier.TIER_3,
    }
    new_tier = tier_mapping.get(product_id)

    if new_tier and new_tier != user.tier:
        # Tier change detected
        tier_levels = {UserTier.TIER_1: 1, UserTier.TIER_2: 2, UserTier.TIER_3: 3}

        if tier_levels[new_tier] > tier_levels[user.tier]:
            # UPGRADE - immediate effect
            user.tier = new_tier
            user.pending_tier = None
            user.tier_change_effective_date = None
            # TODO: Send upgrade confirmation email
        else:
            # DOWNGRADE - schedule for end of billing cycle
            user.pending_tier = new_tier
            user.tier_change_effective_date = user.billing_period_end
            # TODO: Send downgrade scheduled email

        db.session.commit()
```

### Event 4: `customer.subscription.deleted`
**Purpose:** Handle subscription cancellation

**TODO Implementation:**
```python
customer_id = subscription.get('customer')

user = User.query.filter_by(stripe_customer_id=customer_id).first()
if user:
    user.account_status = AccountStatus.SUSPENDED
    user.stripe_subscription_id = None
    db.session.commit()

    # TODO: Send cancellation confirmation email
    # TODO: Schedule data retention/deletion per GDPR
```

### Event 5: `invoice.payment_succeeded`
**Purpose:** Extend billing period, apply pending tier changes

**TODO Implementation:**
```python
customer_id = invoice.get('customer')
amount_paid = invoice.get('amount_paid')
period_end = datetime.fromtimestamp(invoice.get('period_end'))

user = User.query.filter_by(stripe_customer_id=customer_id).first()
if user:
    # Extend billing period
    user.billing_period_end = period_end

    # Check if there's a pending tier change
    if user.pending_tier and user.tier_change_effective_date:
        if datetime.utcnow() >= user.tier_change_effective_date:
            # Apply scheduled downgrade
            user.tier = user.pending_tier
            user.pending_tier = None
            user.tier_change_effective_date = None
            # TODO: Send downgrade applied email

    db.session.commit()
    # TODO: Send payment receipt email
```

### Event 6: `invoice.payment_failed`
**Purpose:** Handle payment failures, warn user

**TODO Implementation:**
```python
customer_id = invoice.get('customer')
attempt_count = invoice.get('attempt_count')

user = User.query.filter_by(stripe_customer_id=customer_id).first()
if user:
    if attempt_count >= 3:
        # All retries exhausted - suspend account
        user.account_status = AccountStatus.SUSPENDED
        db.session.commit()
        # TODO: Send account suspended email
    else:
        # Still retrying
        # TODO: Send payment failure notification
        pass
```

## 📋 Implementation Checklist

### Database Models (From Plan 04-01)
- [ ] Ensure User model has all Stripe fields:
  - [ ] `stripe_customer_id` (String, unique, indexed)
  - [ ] `stripe_subscription_id` (String, unique)
  - [ ] `stripe_subscription_item_id` (String, nullable)
  - [ ] `tier` (UserTier enum)
  - [ ] `pending_tier` (UserTier enum, nullable)
  - [ ] `tier_change_effective_date` (DateTime, nullable)
  - [ ] `billing_period_start` (DateTime)
  - [ ] `billing_period_end` (DateTime)
  - [ ] `account_status` (AccountStatus enum)
  - [ ] `email_verified` (Boolean)
  - [ ] `oauth_completion_deadline` (DateTime)

### Email Functions (From Plan 04-03)
- [ ] Implement `send_verification_email(email, url)`
- [ ] Implement `send_welcome_email(email, dashboard_url)`
- [ ] Implement `send_oauth_reminder_email(email, connect_url, days_remaining)`
- [ ] Implement tier change notification emails:
  - [ ] `send_upgrade_confirmation_email(email, new_tier)`
  - [ ] `send_downgrade_scheduled_email(email, new_tier, effective_date)`
  - [ ] `send_downgrade_applied_email(email, new_tier)`
- [ ] Implement payment emails:
  - [ ] `send_payment_receipt_email(email, amount, date)`
  - [ ] `send_payment_failed_email(email, retry_date)`
  - [ ] `send_account_suspended_email(email, reason)`

### Helper Functions Needed
- [ ] `get_tier_from_product_id(product_id) -> UserTier`
- [ ] `get_product_id_from_tier(tier) -> str`
- [ ] `calculate_proration(old_tier, new_tier, days_remaining) -> int`
- [ ] `is_upgrade(old_tier, new_tier) -> bool`
- [ ] `is_downgrade(old_tier, new_tier) -> bool`

### Testing
- [ ] Unit tests for each webhook handler
- [ ] Integration tests with Stripe test mode
- [ ] Test user creation flow end-to-end
- [ ] Test tier upgrades (immediate)
- [ ] Test tier downgrades (scheduled)
- [ ] Test payment failures
- [ ] Test subscription cancellation
- [ ] Test email delivery

### Production Setup
- [ ] Add webhook endpoint to Stripe Dashboard
- [ ] Get production webhook signing secret
- [ ] Update production .env with webhook secret
- [ ] Set up monitoring/alerts for webhook failures
- [ ] Implement webhook event logging/replay system

## 🔗 Integration Points

### With Plan 04-01 (Database Models)
- User model must have all Stripe and billing fields
- AccountStatus enum must match webhook logic
- UserTier enum must match Stripe product mapping

### With Plan 04-03 (Email Verification)
- Use `generate_verification_url()` after user creation
- Use `send_verification_email()` in checkout webhook
- Use `send_welcome_email()` after account creation

### With Plan 04-04 (Checkout)
- Password hash passed via checkout session metadata
- Tier selection passed via metadata
- Email pre-filled in checkout session

### With Plan 04-06 (OAuth)
- User created with PENDING_OAUTH status
- 7-day grace period set in oauth_completion_deadline
- OAuth flow updates status to ACTIVE

## 📝 Next Steps

1. **Implement User Creation Logic** (Priority 1)
   - Complete `handle_checkout_completed()` function
   - Test with Stripe CLI: `stripe trigger checkout.session.completed`

2. **Implement Tier Management** (Priority 2)
   - Complete subscription event handlers
   - Test upgrades and downgrades

3. **Set Up Email Templates** (Priority 3)
   - Create Resend email templates
   - Test email delivery

4. **Production Deployment** (Priority 4)
   - Configure Stripe webhook in dashboard
   - Deploy and test in production

## 📖 Reference

**Stripe Documentation:**
- Webhooks: https://stripe.com/docs/webhooks
- Checkout Sessions: https://stripe.com/docs/api/checkout/sessions
- Subscriptions: https://stripe.com/docs/api/subscriptions

**Phase 4 Context:**
- `.planning/phases/04-authentication-user-management/04-CONTEXT.md`
- `.planning/phases/04-authentication-user-management/04-RESEARCH.md`
- `.planning/phases/04-authentication-user-management/04-05-PLAN.md`
