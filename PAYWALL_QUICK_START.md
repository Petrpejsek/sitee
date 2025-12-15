# Quick Start Guide - Paywall System

## 🚀 Getting Started

### 1. Run Database Migration

```bash
cd /Users/petrliesner/LLm\ audit\ engine/backend
source venv/bin/activate
alembic upgrade head
```

This will create:
- users table
- payments table
- subscriptions table
- analytics_events table
- Add user_id and audit_access_state to audit_jobs

### 2. Install New Dependencies

```bash
# Backend
cd backend
pip install stripe pyjwt

# No new frontend dependencies needed
```

### 3. Configure Environment Variables

Edit `backend/.env` and add:

```bash
# Generate a secure JWT secret (32+ characters)
JWT_SECRET_KEY=your-random-32-plus-character-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=15

# Stripe (use test keys initially)
STRIPE_API_KEY=sk_test_your_stripe_secret_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
STRIPE_AUDIT_PRICE_ID=price_xxxxx
STRIPE_STARTER_PRICE_ID=price_xxxxx
STRIPE_GROWTH_PRICE_ID=price_xxxxx
STRIPE_SCALE_PRICE_ID=price_xxxxx
```

### 4. Stripe Setup

1. Go to https://dashboard.stripe.com/test/products
2. Create products:
   - **One-time audit**: $199, one-time payment
   - **Starter subscription**: Monthly recurring
   - **Growth subscription**: Monthly recurring
   - **Scale subscription**: Monthly recurring
3. Copy Price IDs to .env

4. Set up webhook:
   - Go to https://dashboard.stripe.com/test/webhooks
   - Add endpoint: `http://localhost:8000/api/webhooks/stripe`
   - Select events: `checkout.session.completed`, `customer.subscription.*`
   - Copy webhook secret to .env

### 5. Restart Services

```bash
./dev.sh restart
```

## 🧪 Testing the Flow

### Test as Anonymous User (Preview)

1. Open http://localhost:3000
2. Create a new audit
3. View report - should see limited content
4. Scroll down - email gate should appear
5. Submit email
6. Check console for magic link (development mode)

### Test as Registered User (Locked)

1. Click magic link from previous step
2. Should redirect to report with session
3. See full structure but with lock overlays
4. Click "Unlock Full Audit"
5. Modal should appear with options

### Test Payment

1. Click "Unlock This Audit - $199"
2. Use test card: `4242 4242 4242 4242`
3. Complete checkout
4. Should redirect to success page
5. Report should now be fully unlocked
6. Section 6 should be visible

### Test Subscription

1. Create new audit as registered user
2. Click subscription option
3. Use test card: `4242 4242 4242 4242`
4. Complete checkout
5. All audits should be unlocked

## 🔍 Debugging

### Check Database

```bash
cd /Users/petrliesner/LLm\ audit\ engine
./dev.sh db shell

-- Check users
SELECT * FROM users;

-- Check payments
SELECT * FROM payments;

-- Check subscriptions
SELECT * FROM subscriptions;

-- Check audit access states
SELECT id, target_domain, user_id, audit_access_state FROM audit_jobs;

-- Check analytics
SELECT * FROM analytics_events ORDER BY created_at DESC LIMIT 10;
```

### Check Logs

```bash
# Backend logs
./dev.sh logs api

# Check for webhook events
grep "webhook" logs/api.log

# Check for authentication events
grep "magic_link" logs/api.log
```

### Test Webhooks Locally

Use Stripe CLI:

```bash
# Install Stripe CLI
brew install stripe/stripe-cli/stripe

# Login
stripe login

# Forward webhooks to local
stripe listen --forward-to localhost:8000/api/webhooks/stripe

# Trigger test event
stripe trigger checkout.session.completed
```

## 🐛 Common Issues

### "Authentication required" error

- Make sure you clicked the magic link
- Check browser cookies are enabled
- Verify JWT_SECRET_KEY is set

### Section 6 not showing after payment

- Check payment status in database
- Verify webhook was received (check logs)
- Refresh the page
- Check audit_access_state in database

### Stripe errors

- Verify Stripe API key is correct
- Check webhook secret matches
- Ensure price IDs are correct

## 📝 Important Notes

1. **Magic Link Email**: Currently returns link in API response (dev only)
   - For production, integrate email service (SendGrid, AWS SES)
   - Update `backend/app/api/auth.py` request_magic_link endpoint

2. **Subscription Pricing**: Update prices in `UnlockModal.jsx`
   - Currently showing placeholder values
   - Match with actual Stripe product prices

3. **Backfill Existing Audits**: The migration sets all existing audits to UNLOCKED
   - This grandfathers in existing audits
   - New audits will start as PREVIEW

4. **Analytics**: All events are tracked to analytics_events table
   - Use this data to optimize conversion funnel
   - Track: audit_started, email_submitted, unlock_clicked, etc.

## ✅ Verification Checklist

Before deploying to production:

- [ ] Database migration completed successfully
- [ ] JWT_SECRET_KEY is set to secure random value
- [ ] Stripe products created with correct prices
- [ ] Stripe webhook endpoint configured
- [ ] Test payment flow works end-to-end
- [ ] Test subscription flow works
- [ ] Email service integrated (or magic link visible in dev)
- [ ] Analytics events being tracked
- [ ] All environment variables set

## 🎯 Next Steps

1. Test all flows thoroughly in development
2. Set up Stripe in test mode
3. Integrate email service for magic links
4. Configure production Stripe account
5. Deploy to staging for final testing
6. Monitor analytics and conversion rates

For detailed implementation info, see: PAYWALL_IMPLEMENTATION_COMPLETE.md
