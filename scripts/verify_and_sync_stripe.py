import os
import stripe
import logging
from elasticsearch import Elasticsearch
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Credentials
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
ES_CLOUD_ID = os.environ.get('ES_CLOUD_ID')
ES_API_KEY = os.environ.get('ES_API_KEY')
ES_USER_PURCHASES_INDEX = 'user_purchases'

def get_es_client():
    if ES_CLOUD_ID and ES_API_KEY:
        return Elasticsearch(
            cloud_id=ES_CLOUD_ID,
            api_key=ES_API_KEY,
            verify_certs=True
        )
    return None

def sync_stripe_to_es(email):
    print(f"\n🔍 Checking Stripe for {email}...")
    
    # 1. Find Customer
    customers = stripe.Customer.list(email=email, limit=1)
    if not customers.data:
        print(f"❌ No Stripe customer found for {email}")
        return
    
    customer = customers.data[0]
    print(f"✅ Found Customer: {customer.id}")
    
    # 2. Find Active Subscriptions
    subs = stripe.Subscription.list(customer=customer.id, status='active', limit=1)
    
    if not subs.data:
        print(f"❌ No active subscriptions for {customer.id}")
        return

    sub = subs.data[0]
    price_id = sub['items']['data'][0]['price']['id']
    plan_interval = sub['plan']['interval']
    
    print(f"✅ Found Active Subscription: {sub.id}")
    
    # Debug: Print available keys
    # print(f"Keys: {sub.keys()}")
    
    # Access properties safely
    current_period_end = sub.get('current_period_end')
    cancel_at_period_end = sub.get('cancel_at_period_end', False)
    
    if not current_period_end:
        print("⚠️  Warning: 'current_period_end' not found, using default 30 days")
        current_period_end = int(datetime.now(timezone.utc).timestamp()) + 30*24*3600
        
    print(f"   Plan: {plan_interval}ly")
    print(f"   Status: {sub.get('status')}")
    print(f"   Ends: {datetime.fromtimestamp(current_period_end).strftime('%Y-%m-%d')}")
    
    # 3. Sync to ES
    es = get_es_client()
    if not es:
        print("❌ ES Client not initialized (missing secrets)")
        return

    import hashlib
    user_hash = hashlib.md5(email.encode()).hexdigest()[:12]
    doc_id = f"purchases_{user_hash}"
    
    print(f"\n🔄 Syncing to ES (Doc ID: {doc_id})...")
    
    # Construct purchase record
    purchase_record = {
        'user_email': email,
        'subscription_active': True,
        'subscription_plan': 'annual' if plan_interval == 'year' else 'monthly',
        'subscription_end_date': datetime.fromtimestamp(current_period_end).isoformat(),
        'subscription_cancel_at_period_end': cancel_at_period_end,
        'stripe_customer_id': customer.id,
        'stripe_subscription_id': sub.id,
        'purchases': [{
            'id': sub.id,
            'amount': sub.plan.amount,
            'currency': sub.plan.currency,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'description': f"Manual Sync: {plan_interval}ly subscription"
        }],
        'updated_at': datetime.now(timezone.utc).isoformat(),
        # Default limits
        'ai_messages_limit': -1,
        'fit_analysis_credits': 150 if plan_interval == 'year' else 20
    }
    
    try:
        es.index(index=ES_USER_PURCHASES_INDEX, id=doc_id, body=purchase_record)
        print("✅ Successfully synced to Elasticsearch!")
        
        # Verify
        doc = es.get(index=ES_USER_PURCHASES_INDEX, id=doc_id)
        print(f"   Verified ES Status: Active={doc['_source']['subscription_active']}")
        
    except Exception as e:
        print(f"❌ Failed to sync to ES: {e}")

if __name__ == "__main__":
    import sys
    # Read secrets from env (set by gcloud wrapper)
    sync_stripe_to_es('kaaimd@gmail.com')
