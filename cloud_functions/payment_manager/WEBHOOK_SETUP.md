# Stripe Webhook Setup Guide

## Overview
This guide explains how to configure Stripe webhooks to handle subscription lifecycle events for the payment manager.

## Required Webhook Events

Configure these events in your Stripe Dashboard:

### Subscription Events
- `customer.subscription.created` - New subscription activated
- `customer.subscription.updated` - Subscription modified (plan change, cancellation scheduled)
- `customer.subscription.deleted` - Subscription ended/canceled

### Payment Events
- `invoice.payment_succeeded` - Successful renewal payment
- `invoice.payment_failed` - Failed payment (card declined, etc.)

### Additional Events (Optional)
- `checkout.session.completed` - Already configured for one-time payments
- `payment_intent.succeeded` - Already configured

## Setup Steps

### 1. Access Stripe Dashboard
1. Log in to [Stripe Dashboard](https://dashboard.stripe.com)
2. Navigate to **Developers** → **Webhooks**

### 2. Add Endpoint for Production

**Endpoint URL:**
```
https://us-central1-YOUR_PROJECT_ID.cloudfunctions.net/payment_manager/webhook
```

Replace `YOUR_PROJECT_ID` with your actual GCP project ID.

### 3. Select Events to Listen To

Click **"Select events"** and choose:
- [x] `customer.subscription.created`
- [x] `customer.subscription.updated`
- [x] `customer.subscription.deleted`
- [x] `invoice.payment_succeeded`
- [x] `invoice.payment_failed`
- [x] `checkout.session.completed` (if not already configured)

### 4. Get Webhook Signing Secret

After creating the webhook:
1. Click on the webhook endpoint
2. Click **"Reveal"** next to "Signing secret"
3. Copy the secret (starts with `whsec_...`)

### 5. Store Secret in GCP Secret Manager

```bash
# Set your project ID
PROJECT_ID="your-project-id"

# Create secret (if not exists)
gcloud secrets create stripe-webhook-secret \
  --project=$PROJECT_ID \
  --replication-policy="automatic"

# Add the secret value
echo -n "whsec_YOUR_ACTUAL_SECRET" | \
  gcloud secrets versions add stripe-webhook-secret \
  --data-file=- \
  --project=$PROJECT_ID
```

### 6. Redeploy Cloud Function

The function needs environment variables from Secret Manager:

```bash
cd cloud_functions/payment_manager

# Deployment will automatically pull from Secret Manager
# (configured in deploy.sh)
../../deploy.sh payment
```

## Local Testing with Stripe CLI

For development, use the Stripe CLI to forward webhooks to localhost:

### Install Stripe CLI
```bash
brew install stripe/stripe-cli/stripe
# or download from https://stripe.com/docs/stripe-cli
```

### Login to Stripe
```bash
stripe login
```

### Start Local Function
```bash
# Terminal 1
cd cloud_functions/payment_manager
functions-framework --target=payment_manager --port=8081
```

### Forward Webhooks
```bash
# Terminal 2
stripe listen --forward-to localhost:8081/webhook
```

This will output a webhook signing secret like `whsec_...`. Set this temporarily:
```bash
export STRIPE_WEBHOOK_SECRET="whsec_..."
```

### Trigger Test Events
```bash
# Test subscription created
stripe trigger customer.subscription.created

# Test subscription deleted
stripe trigger customer.subscription.deleted

# Test payment failed
stripe trigger invoice.payment_failed
```

## Verification

To verify webhooks are working:

1. Check Cloud Function logs:
```bash
gcloud functions logs read payment_manager \
  --project=YOUR_PROJECT_ID \
  --limit=50
```

2. Look for log entries like:
```
Subscription created: sub_xxx for customer: cus_xxx
Subscription deleted: sub_xxx
Payment failed for subscription: sub_xxx
```

3. Check Elasticsearch for updated user records:
   - `subscription_active` should change to `false` after `customer.subscription.deleted`
   - `subscription_cancel_at_period_end` should flip on cancel/reactivate

## Troubleshooting

### Webhook not receiving events
- Verify endpoint URL is correct
- Check that function is deployed and publicly accessible
- Ensure firewall/auth settings allow Stripe IPs

### Signature verification failing
- Confirm `STRIPE_WEBHOOK_SECRET` environment variable is set correctly
- Ensure secret matches the one from Stripe Dashboard
- Check Cloud Function logs for specific error messages

### Events not processing
- Check Cloud Function logs for errors
- Verify Elasticsearch connection is working
- Confirm user has `stripe_subscription_id` stored

## Security Best Practices

1. **Always verify webhook signatures in production**
   - Don't skip signature verification
   - Rotate webhook secrets periodically

2. **Log all webhook events**
   - Keep audit trail of subscription changes
   - Monitor for suspicious patterns

3. **Handle idempotency**
   - Stripe may send duplicate webhook events
   - Use event IDs to prevent duplicate processing

4. **Set up monitoring**
   - Alert on repeated `invoice.payment_failed` events
   - Monitor subscription churn rate

## Support

For issues:
- Stripe webhook docs: https://stripe.com/docs/webhooks
- Stripe support: https://support.stripe.com
- GCP Secret Manager: https://cloud.google.com/secret-manager/docs
