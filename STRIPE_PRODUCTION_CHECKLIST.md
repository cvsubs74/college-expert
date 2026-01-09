# Stripe Production Launch Checklist

> **Status**: 🟡 In Progress  
> **Last Updated**: 2026-01-03  
> **Environment**: Test → Production Migration

---

## Phase 1: Stripe Account Setup

### 1.1 Activate Stripe Account
- [ ] Complete business details in Stripe Dashboard
- [ ] Add bank account for payouts
- [ ] Submit tax information (W-9/W-8BEN)
- [ ] Complete identity verification
- [ ] ✅ **Verification**: Stripe account shows "Active" status

### 1.2 Create Production Products
Navigate to Stripe Dashboard → Products (Live Mode)

- [ ] Create **Monthly Subscription** product
  - Price: $15.00 USD
  - Billing: Recurring monthly
  - Save Price ID: `price_________________`
  
- [ ] Create **Season Pass** product
  - Price: $99.00 USD
  - Billing: Recurring yearly
  - Save Price ID: `price_________________`
  
- [ ] Create **10 Credit Pack** product
  - Price: $9.00 USD
  - Type: One-time payment
  - Save Price ID: `price_________________`

---

## Phase 2: Security & Secrets

### 2.1 Retrieve Live API Keys
- [ ] Go to Stripe Dashboard → Developers → API keys (Live Mode)
- [ ] Copy **Secret Key** (starts with `sk_live_`)
- [ ] Store securely (do NOT commit to git)

### 2.2 Update GCP Secrets

```bash
# Update Stripe Secret Key
gcloud secrets versions add stripe-secret-key \
  --data-file=- <<< "sk_live_YOUR_KEY_HERE" \
  --project=college-counselling-478115

# Verify it was updated
gcloud secrets versions access latest \
  --secret="stripe-secret-key" \
  --project=college-counselling-478115
```

- [ ] Updated `stripe-secret-key` secret
- [ ] Verified new version is accessible
- [ ] ⚠️  **STOP**: Do NOT proceed until webhook is configured (Step 3)

---

## Phase 3: Webhook Configuration

### 3.1 Create Production Webhook Endpoint
In Stripe Dashboard → Developers → Webhooks (Live Mode):

**Endpoint Details**:
- URL: `https://payment-manager-pfnwjfp26a-ue.a.run.app/webhook`
- Description: "Production Payment Manager Webhook"
- API Version: Latest (2024-11-20 or newer)

**Events to Select**:
- [ ] `checkout.session.completed`
- [ ] `customer.subscription.created`
- [ ] `customer.subscription.updated`
- [ ] `customer.subscription.deleted`
- [ ] `invoice.payment_succeeded`
- [ ] `invoice.payment_failed`

- [ ] Click "Add endpoint"
- [ ] Copy **Signing Secret** (starts with `whsec_`)

### 3.2 Update Webhook Secret in GCP

```bash
# Update Stripe Webhook Secret
gcloud secrets versions add stripe-webhook-secret \
  --data-file=- <<< "whsec_YOUR_SECRET_HERE" \
  --project=college-counselling-478115
```

- [ ] Updated `stripe-webhook-secret` secret
- [ ] Verified new version is accessible

---

## Phase 4: Code Updates

### 4.1 Update Price IDs

Edit: `cloud_functions/payment_manager/main.py`

```python
# Line ~53-66: Update STRIPE_PRICES
STRIPE_PRICES = {
    # Subscriptions
    'subscription_monthly': 'price_________________',  # ← From Step 1.2
    'subscription_annual': 'price_________________',   # ← From Step 1.2
    
    # Credit Packs
    'credit_pack_10': 'price_________________',       # ← From Step 1.2
}
```

- [ ] Updated all 3 price IDs
- [ ] Double-checked IDs start with `price_` (not `prod_`)
- [ ] Committed changes: `git commit -m "Update to production Stripe price IDs"`

### 4.2 Verify Environment Configuration

Check: `cloud_functions/payment_manager/env.yaml`

```yaml
FRONTEND_URL: "https://stratiaadmissions.com"  # ✅ Already updated
```

- [ ] Confirmed `FRONTEND_URL` is production domain
- [ ] No test/localhost URLs remain in code

---

## Phase 5: Deployment

### 5.1 Deploy Payment Manager

```bash
cd /Users/cvsubramanian/CascadeProjects/graphrag/agents/college_counselor
./deploy.sh payment
```

- [ ] Deployment completed successfully
- [ ] No errors in deployment logs
- [ ] Cloud function shows "Active" status in GCP Console

### 5.2 Verify Secrets Loaded

```bash
# Check cloud function environment
gcloud functions describe payment-manager \
  --region=us-east1 \
  --project=college-counselling-478115 \
  --format="value(secrets)"
```

- [ ] `stripe-secret-key` is listed
- [ ] `stripe-webhook-secret` is listed
- [ ] Both show latest version numbers

---

## Phase 6: Pre-Launch Testing

> ⚠️ **Test in Stripe Test Mode First**

### 6.1 Smoke Tests (Test Mode)
- [ ] Frontend loads pricing page without errors
- [ ] Can click "Subscribe" and reach Stripe Checkout
- [ ] Can complete test purchase (use `4242 4242 4242 4242`)
- [ ] Webhook received in Stripe Dashboard → Webhooks → Test events
- [ ] Credits updated in Elasticsearch
- [ ] User can access Pro features

### 6.2 Production Tests (Live Mode)
> ⚠️ **Use a real card (will create actual charge)**

- [ ] Purchase Monthly Subscription ($15)
- [ ] Verify charge in Stripe Dashboard (Live Mode)
- [ ] Check Elasticsearch for updated credits
- [ ] Test cancellation flow
- [ ] Test reactivation flow
- [ ] Purchase Season Pass ($99) - verify old subscription handling
- [ ] Purchase Credit Pack ($9)

### 6.3 Webhook Verification
- [ ] Check Stripe Dashboard → Developers → Webhooks (Live Mode)
- [ ] Confirm all events show "Succeeded" (not "Failed")
- [ ] Check GCP Cloud Function logs for webhook processing
- [ ] No errors in payment-manager logs

---

## Phase 7: Compliance & Legal

### 7.1 Terms of Service
- [ ] Mentions automatic subscription renewal
- [ ] States renewal dates clearly
- [ ] Explains how to cancel
- [ ] Published at: `https://stratiaadmissions.com/terms`

### 7.2 Refund Policy
- [ ] Document refund policy clearly
- [ ] Published at: `https://stratiaadmissions.com/refunds`

### 7.3 Privacy Policy  
- [ ] Mentions Stripe as payment processor
- [ ] States data is encrypted (PCI compliant via Stripe)
- [ ] Published at: `https://stratiaadmissions.com/privacy`

### 7.4 Tax Collection (Optional but Recommended)
- [ ] Enable Stripe Tax in Dashboard (if applicable)
- [ ] Configure tax jurisdictions

---

## Phase 8: Monitoring Setup

### 8.1 Stripe Alerts
In Stripe Dashboard → Settings → Email notifications:
- [ ] Enable "Failed payments" notifications
- [ ] Enable "Disputed payments" notifications  
- [ ] Add backup email for critical alerts

### 8.2 GCP Monitoring
- [ ] Set up Cloud Function error alerts
- [ ] Monitor webhook endpoint uptime
- [ ] Configure budget alerts for GCP spend

### 8.3 Elasticsearch Health
- [ ] Verify `user_purchases` index is accessible
- [ ] Verify `user_credits` index is accessible
- [ ] Set up automated backups (if not already configured)

---

## Phase 9: Rollback Plan

### 9.1 Emergency Rollback Procedure

If critical issues arise after launch:

```bash
# 1. Revert to test keys
gcloud secrets versions add stripe-secret-key \
  --data-file=- <<< "sk_test_YOUR_TEST_KEY"

# 2. Redeploy
./deploy.sh payment

# 3. Update frontend to show maintenance message
```

- [ ] Test key backup is accessible: `sk_test_________________`
- [ ] Rollback script tested (optional)

---

## Launch Day Checklist

- [ ] **9:00 AM**: Final deployment verification
- [ ] **9:30 AM**: Make small test purchase yourself
- [ ] **10:00 AM**: Monitor for 1 hour - check logs every 15 min
- [ ] **11:00 AM**: Announce live payments to users
- [ ] **EOD**: Review all transactions for anomalies
- [ ] **Day 2-7**: Daily monitoring of failed payments

---

## Post-Launch (First Week)

- [ ] **Day 1**: Monitor all transactions
- [ ] **Day 2**: Review webhook success rate (should be >99%)
- [ ] **Day 3**: Check for any customer support issues
- [ ] **Day 7**: Review Stripe Dashboard analytics
- [ ] **Day 7**: Confirm all customer subscriptions are active

---

## Important Numbers

| Contact | Purpose |
|---------|---------|
| Stripe Support | Dashboard → Help → Email support |
| GCP Support | [console.cloud.google.com/support](https://console.cloud.google.com/support) |

---

## Common Issues & Solutions

### Issue: Webhook shows "Failed"
**Solution**: Check GCP logs, verify signing secret is correct

### Issue: Prices not showing in checkout
**Solution**: Verify price IDs updated in code, redeploy

### Issue: Credits not updating after purchase
**Solution**: Check Elasticsearch connection, verify webhook received

### Issue: Users charged twice
**Solution**: Implement subscription swap logic (see `implementation_plan.md`)

---

## ✅ Launch Complete

Once all checkboxes above are complete:

```bash
# Tag the production release
git tag -a v1.0.0-production -m "Production Stripe integration live"
git push origin v1.0.0-production
```

- [ ] All checklist items completed
- [ ] Production release tagged in git
- [ ] Team notified of successful launch

---

**Next Steps After Launch**:
1. Implement subscription swap logic to prevent double subscriptions
2. Set up automated reconciliation between Stripe and Elasticsearch
3. Create customer-facing subscription management portal
