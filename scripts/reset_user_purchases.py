#!/usr/bin/env python3
"""
Reset user purchase data in Elasticsearch
Useful for testing the subscription purchase flow
"""

import os
import sys
import hashlib
import requests
from datetime import datetime, timezone

# Payment API URL
PAYMENT_API_URL = os.environ.get('PAYMENT_API_URL', 'https://payment-manager-pfnwjfp26a-ue.a.run.app')

# ES configuration
ES_CLOUD_ID = os.environ.get('ES_CLOUD_ID', '')
ES_API_KEY = os.environ.get('ES_API_KEY', '')
ES_USER_PURCHASES_INDEX = 'user_purchases'

def get_user_hash(email):
    """Generate consistent hash for user email"""
    return hashlib.md5(email.encode()).hexdigest()[:12]

def reset_user_via_api(email):
    """Reset user purchases by deleting the ES document via direct ES API"""
    from elasticsearch import Elasticsearch
    
    # Parse cloud ID to get host
    if ES_CLOUD_ID:
        es_client = Elasticsearch(
            cloud_id=ES_CLOUD_ID,
            api_key=ES_API_KEY,
            verify_certs=True,
            request_timeout=30
        )
    else:
        print("❌ ES_CLOUD_ID not set. Please set environment variables.")
        return False
    
    try:
        # 1. Reset Purchase History (MD5)
        user_hash = get_user_hash(email)
        doc_id_purchases = f"purchases_{user_hash}"
        
        # Check if purchase exists
        if es_client.exists(index=ES_USER_PURCHASES_INDEX, id=doc_id_purchases):
            es_client.delete(index=ES_USER_PURCHASES_INDEX, id=doc_id_purchases)
            print(f"✅ Reset {email} purchases (doc_id: {doc_id_purchases})")
        else:
            print(f"ℹ️  No purchase data found for {email}")

        # 2. Reset Credits/Tier (SHA256)
        doc_id_credits = hashlib.sha256(email.encode()).hexdigest()
        
        if es_client.exists(index='user_credits', id=doc_id_credits):
            es_client.delete(index='user_credits', id=doc_id_credits)
            print(f"✅ Reset {email} credits/tier (doc_id: {doc_id_credits})")
        else:
            print(f"ℹ️  No credits/tier data found for {email}")

        return True
            
    except Exception as e:
        print(f"❌ Error resetting {email}: {e}")
        return False

def verify_reset(email):
    """Verify user is back to free tier by checking API"""
    try:
        response = requests.get(
            f"{PAYMENT_API_URL}/subscription-status",
            headers={'X-User-Email': email}
        )
        
        if response.ok:
            data = response.json()
            sub = data.get('subscription', {})
            is_free = not sub.get('subscription_active', False)
            
            print(f"\n📊 Verification for {email}:")
            print(f"   Active subscription: {sub.get('subscription_active', False)}")
            print(f"   Stripe subscription ID: {sub.get('stripe_subscription_id', 'None')}")
            print(f"   Free tier: {is_free}")
            
            return is_free
        else:
            print(f"❌ Failed to verify {email}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error verifying {email}: {e}")
        return False

def main():
    print("=" * 60)
    print("Reset User Purchases for Testing")
    print("=" * 60)
    
    # Users to reset
    users = [
        'cvsubs@gmail.com',
        'kaaimd@gmail.com'
    ]
    
    if not ES_CLOUD_ID or not ES_API_KEY:
        print("\n⚠️  Environment variables not set!")
        print("Please run:")
        print("  export ES_CLOUD_ID='your_cloud_id'")
        print("  export ES_API_KEY='your_api_key'")
        sys.exit(1)
    
    print(f"\n🔄 Resetting {len(users)} users to free tier...\n")
    
    success_count = 0
    for email in users:
        if reset_user_via_api(email):
            success_count += 1
    
    print(f"\n{'=' * 60}")
    print(f"Reset complete: {success_count}/{len(users)} users")
    print(f"{'=' * 60}")
    
    # Verify resets
    print("\n🔍 Verifying resets...\n")
    for email in users:
        verify_reset(email)
    
    print(f"\n{'=' * 60}")
    print("✅ All users reset to free tier!")
    print("You can now test the purchase flow from scratch.")
    print(f"{'=' * 60}\n")

if __name__ == '__main__':
    main()
