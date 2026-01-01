#!/bin/bash

# Reset User Purchases in Elasticsearch
# Deletes purchase documents to reset users to free tier

echo "============================================================"
echo "Reset User Purchases for Testing"
echo "============================================================"

# Get ES credentials from Secret Manager
echo ""
echo "🔑 Fetching ES credentials..."
ES_CLOUD_ID=$(gcloud secrets versions access latest --secret="es-cloud-id" --project=college-counselling-478115 2>/dev/null)
ES_API_KEY=$(gcloud secrets versions access latest --secret="es-api-key" --project=college-counselling-478115 2>/dev/null)

if [ -z "$ES_CLOUD_ID" ] || [ -z "$ES_API_KEY" ]; then
    echo "❌ Failed to fetch ES credentials"
    exit 1
fi

# Parse ES endpoint from cloud ID
# Cloud ID format: name:base64(endpoint$uuid$uuid)
ES_ENDPOINT=$(python3 -c "
import base64
cloud_id = '$ES_CLOUD_ID'
name, encoded = cloud_id.split(':')
decoded = base64.b64decode(encoded).decode('utf-8')
parts = decoded.split('$')
# parts[0] is host:port, parts[1] is deployment ID
host = parts[0].split(':')[0]
print(f'https://{parts[1]}.{host}')
")

echo "✅ Connected to ES: ${ES_ENDPOINT:0:50}..."

# User emails
USERS=("cvsubs@gmail.com" "kaaimd@gmail.com")

echo ""
echo "🔄 Resetting ${#USERS[@]} users to free tier..."
echo ""

# Reset each user
for email in "${USERS[@]}"; do
    echo "📧 ${email}"
    
    # 1. Reset user_purchases (MD5)
    user_hash_md5=$(python3 -c "import hashlib; print(hashlib.md5('$email'.encode()).hexdigest()[:12])")
    doc_id_purchases="purchases_${user_hash_md5}"
    
    echo "   [user_purchases] Doc ID: ${doc_id_purchases}"
    
    response_purchases=$(curl -s -X DELETE \
        "${ES_ENDPOINT}/user_purchases/_doc/${doc_id_purchases}" \
        -H "Authorization: ApiKey ${ES_API_KEY}" \
        -H "Content-Type: application/json")
        
    if echo "$response_purchases" | grep -q '"result":"deleted"'; then
        echo "   ✅ Purchase history reset"
    elif echo "$response_purchases" | grep -q '"result":"not_found"'; then
        echo "   ℹ️  No purchase history found"
    else
        echo "   ⚠️  Purchase reset failed: ${response_purchases:0:50}..."
    fi

    # 2. Reset user_credits (SHA256)
    user_hash_sha256=$(python3 -c "import hashlib; print(hashlib.sha256('$email'.encode()).hexdigest())")
    doc_id_credits="${user_hash_sha256}"
    
    echo "   [user_credits] Doc ID: ${doc_id_credits:0:12}..."
    
    response_credits=$(curl -s -X DELETE \
        "${ES_ENDPOINT}/user_credits/_doc/${doc_id_credits}" \
        -H "Authorization: ApiKey ${ES_API_KEY}" \
        -H "Content-Type: application/json")

    if echo "$response_credits" | grep -q '"result":"deleted"'; then
        echo "   ✅ Credits/Tier reset"
    elif echo "$response_credits" | grep -q '"result":"not_found"'; then
        echo "   ℹ️  No credits/tier record found"
    else
        echo "   ⚠️  Credits reset failed: ${response_credits:0:50}..."
    fi
    echo ""
done

echo "============================================================"
echo "Verifying Reset"
echo "============================================================"
echo ""

# Verify each user
for email in "${USERS[@]}"; do
    echo "📧 ${email}"
    
    # Check subscription status via API
    response=$(curl -s -X GET \
        "https://payment-manager-pfnwjfp26a-ue.a.run.app/subscription-status" \
        -H "Content-Type: application/json" \
        -H "X-User-Email: ${email}")
    
    # Extract key fields
    subscription_active=$(echo "$response" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('subscription', {}).get('subscription_active', 'N/A'))")
    stripe_sub_id=$(echo "$response" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('subscription', {}).get('stripe_subscription_id', 'None'))")
    
    echo "   Active: ${subscription_active}"
    echo "   Stripe ID: ${stripe_sub_id}"
    
    if [ "$subscription_active" == "False" ] && [ "$stripe_sub_id" == "None" ]; then
        echo "   ✅ Confirmed free tier"
    else
        echo "   ⚠️  May still have subscription data"
    fi
    echo ""
done

echo "============================================================"
echo "✅ Reset Complete!"
echo "You can now test the purchase flow from scratch."
echo "============================================================"
