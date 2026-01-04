#!/bin/bash

# Usage: ./scripts/verify_subscription.sh <email>

if [ -z "$1" ]; then
    echo "Usage: $0 <email>"
    exit 1
fi

EMAIL=$1
VENV_DIR=".venv"

# 1. Setup Venv if needed
if [ ! -d "$VENV_DIR" ]; then
    echo "Initializing virtual environment ($VENV_DIR)..."
    python3 -m venv $VENV_DIR
fi

# 2. Activate
source $VENV_DIR/bin/activate

# 3. Check dependencies (quietly)
if ! pip show stripe > /dev/null 2>&1; then
    echo "Installing dependencies..."
    pip install stripe requests > /dev/null
fi

# 4. Get Secrets
if [ -z "$STRIPE_SECRET_KEY" ]; then
    echo "Fetching Stripe Key..."
    export STRIPE_SECRET_KEY=$(gcloud secrets versions access latest --secret="stripe-secret-key" --project=college-counselling-478115)
fi

echo "============================================================"
echo "🔎 Verifying Subscription for: $EMAIL"
echo "============================================================"

# 5. Run Stripe Check
python3 scripts/verify_stripe_subscription.py $EMAIL

echo ""
echo "--- ES Payment Status ---"
curl -s -X GET "https://payment-manager-pfnwjfp26a-ue.a.run.app/subscription-status" \
    -H "X-User-Email: $EMAIL" \
    | python3 -m json.tool

echo ""
echo "--- ES Credits Status ---"
curl -s -X GET "https://profile-manager-es-pfnwjfp26a-ue.a.run.app/get-credits?user_email=$EMAIL" \
    | python3 -m json.tool

echo ""
echo "============================================================"
