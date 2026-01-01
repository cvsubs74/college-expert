#!/bin/bash
# Script to add Stripe webhook secret to GCP Secret Manager

PROJECT_ID="college-counselling-478115"

echo "Adding Stripe webhook secret to GCP Secret Manager..."
echo ""
echo "Paste your webhook signing secret (starts with whsec_):"
read -r WEBHOOK_SECRET

if [[ ! $WEBHOOK_SECRET == whsec_* ]]; then
    echo "❌ Error: Secret must start with 'whsec_'"
    exit 1
fi

# Add secret version
echo -n "$WEBHOOK_SECRET" | \
  gcloud secrets versions add stripe-webhook-secret \
  --data-file=- \
  --project=$PROJECT_ID

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Webhook secret added successfully!"
    echo ""
    echo "Next step: Redeploy the payment manager function"
    echo "Run: cd ../.. && ./deploy.sh payment"
else
    echo "❌ Failed to add secret"
    exit 1
fi
