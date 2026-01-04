#!/usr/bin/env python3

import os
import sys
import stripe

def reset_stripe_subscription(email):
    # Get API key from env
    stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
    if not stripe.api_key:
        print("❌ STRIPE_SECRET_KEY not set")
        return

    print(f"\n🔄 Resetting Stripe for: {email}")
    
    try:
        # 1. Find Customer
        customers = stripe.Customer.list(email=email, limit=1).data
        
        if not customers:
            print("   ℹ️  No Stripe customer found with this email.")
            return

        customer = customers[0]
        print(f"   👤 Customer ID: {customer.id}")
        
        # 2. List Active Subscriptions
        subscriptions = stripe.Subscription.list(customer=customer.id, status='active', limit=10).data
        
        if not subscriptions:
            print("   ✅ No active subscriptions found.")
        else:
            for sub in subscriptions:
                print(f"   ⚠️  Canceling active subscription: {sub.id}...")
                try:
                    # Cancel immediately
                    stripe.Subscription.delete(sub.id)
                    print(f"      ✅ Canceled successfully.")
                except Exception as e:
                    print(f"      ❌ Failed to cancel: {e}")

    except Exception as e:
        print(f"❌ Error operating on Stripe: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python reset_stripe_subscription.py <email>")
        sys.exit(1)
        
    email = sys.argv[1]
    reset_stripe_subscription(email)
