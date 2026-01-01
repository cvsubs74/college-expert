# Production Testing Guide - Subscription Downgrades

## ✅ Deployment Status
**DEPLOYED**: https://us-east1-college-counselling-478115.cloudfunctions.net/payment-manager

---

## Quick Production Test (5 minutes)

### Step 1: Test New Endpoints

**Get Subscription Status:**
```bash
curl -X GET \
  "https://us-east1-college-counselling-478115.cloudfunctions.net/payment-manager/subscription-status" \
  -H "X-User-Email: YOUR_EMAIL@example.com"
```

**Cancel Subscription (if you have one):**
```bash
curl -X POST \
  "https://us-east1-college-counselling-478115.cloudfunctions.net/payment-manager/cancel-subscription" \
  -H "X-User-Email: YOUR_EMAIL@example.com" \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Reactivate Subscription:**
```bash
curl -X POST \
  "https://us-east1-college-counselling-478115.cloudfunctions.net/payment-manager/reactivate-subscription" \
  -H "X-User-Email: YOUR_EMAIL@example.com" \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

## Full End-to-End Test

### Test Scenario: Monthly Subscription Downgrade

**1. Create Test Subscription**
- Go to https://college-strategy.web.app
- Log in with test account
- Subscribe to **Monthly Plan ($15)**
- Use test card: `4242 4242 4242 4242`

**2. Verify Subscription Active**
```bash
curl -X GET \
  "https://us-east1-college-counselling-478115.cloudfunctions.net/payment-manager/subscription-status" \
  -H "X-User-Email: your-test-email@example.com"
```

Expected: `"subscription_active": true, "subscription_cancel_at_period_end": false`

**3. Downgrade to Free (Cancel)**
```bash
curl -X POST \
  "https://us-east1-college-counselling-478115.cloudfunctions.net/payment-manager/cancel-subscription" \
  -H "X-User-Email: your-test-email@example.com" \
  -H "Content-Type: application/json"
```

Expected Response:
```json
{
  "success": true,
  "message": "Subscription will be canceled at period end",
  "cancel_at": "2025-01-30...",
  "credits_valid_until": "2025-01-30..."
}
```

**4. Verify Stripe Dashboard**
- Go to https://dashboard.stripe.com/test/subscriptions
- Find your subscription
- Should show: **"Cancels at period end"**

**5. Verify Credits Still Valid**
```bash
curl -X GET \
  "https://us-east1-college-counselling-478115.cloudfunctions.net/payment-manager/subscription-status" \
  -H "X-User-Email: your-test-email@example.com"
```

Expected: `"subscription_cancel_at_period_end": true` but `"fit_analysis_credits": 20` (still available)

**6. Reactivate Subscription**
```bash
curl -X POST \
  "https://us-east1-college-counselling-478115.cloudfunctions.net/payment-manager/reactivate-subscription" \
  -H "X-User-Email: your-test-email@example.com"
```

Expected: `"subscription_cancel_at_period_end": false` (cancellation undone)

**7. Verify in Stripe**
- Refresh Stripe subscription page
- Should show: **"Active"** (no longer shows cancellation)

---

## Check Cloud Function Logs

```bash
gcloud functions logs read payment-manager \
  --region=us-east1 \
  --limit=50 \
  --project=college-counselling-478115
```

Look for:
- ✅ "Successfully processed payment..."
- ✅ "Subscription created: sub_xxx..."
- ✅ Webhook events if configured

---

## Next Step: Configure Webhooks

> **⚠️ IMPORTANT**: Webhooks are NOT configured yet. You need to set these up for automatic subscription lifecycle handling.

Follow: [WEBHOOK_SETUP.md](file:///Users/cvsubramanian/CascadeProjects/graphrag/agents/college_counselor/cloud_functions/payment_manager/WEBHOOK_SETUP.md)

**Quick Webhook Setup:**
1. Go to https://dashboard.stripe.com/test/webhooks
2. Add endpoint: `https://us-east1-college-counselling-478115.cloudfunctions.net/payment-manager/webhook`
3. Select events: `customer.subscription.*`, `invoice.payment_*`
4. Copy webhook secret
5. Update GCP Secret Manager:
```bash
echo -n "whsec_YOUR_SECRET" | \
  gcloud secrets versions add stripe-webhook-secret \
  --data-file=- \
  --project=college-counselling-478115
```
6. Redeploy: `./deploy.sh payment`

---

## Troubleshooting

**401 Error (User not authenticated)**
- Make sure `X-User-Email` header matches a real user in your system

**404 Error (No subscription found)**
- User doesn't have an active subscription yet
- Create one first through the frontend

**500 Error (Stripe error)**
- Check Stripe API key is valid
- Verify subscription_id exists in Elasticsearch

**Check Elasticsearch directly:**
```bash
# Use your ES credentials to query user purchases
curl -X GET "https://college-search-9522040934.us-east1.run.app/user_purchases/_search" \
  -H "Authorization: ApiKey YOUR_ES_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "term": { "user_email.keyword": "your-test-email@example.com" }
    }
  }'
```

---

## Success Criteria

✅ Subscription status endpoint returns user data  
✅ Cancel endpoint marks subscription for cancellation  
✅ Stripe Dashboard shows"Cancels at period end"  
✅ Credits remain available until period end  
✅ Reactivate endpoint removes cancellation  
✅ Stripe Dashboard shows "Active" again  

---

## What to Test

| Feature | Test | Expected Result |
|---------|------|----------------|
| Get Status | Call `/subscription-status` | Returns subscription info |
| Cancel Sub | Call `/cancel-subscription` | Sets `cancel_at_period_end=true` |
| Keep Credits | Check status after cancel | Credits still available |
| Reactivate | Call `/reactivate-subscription` | Sets `cancel_at_period_end=false` |
| Stripe Sync | Check Stripe Dashboard | Matches API responses |

---

## Questions or Issues?

Check:
- [Walkthrough](file:///Users/cvsubramanian/.gemini/antigravity/brain/c2878254-db75-48ba-93ef-8ac070a4f9c9/walkthrough.md)
- [Webhook Setup](file:///Users/cvsubramanian/CascadeProjects/graphrag/agents/college_counselor/cloud_functions/payment_manager/WEBHOOK_SETUP.md)
- Cloud Function logs (command above)
