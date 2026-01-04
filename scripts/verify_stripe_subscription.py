
import os
import sys
import stripe

def verify_stripe_subscription(email):
    # Get API key from env
    stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
    if not stripe.api_key:
        print("❌ STRIPE_SECRET_KEY not set")
        return

    print(f"\n🔍 Checking Stripe for: {email}")
    
    try:
        # 1. Find Customer
        customers = stripe.Customer.list(email=email, limit=1).data
        
        if not customers:
            print("   ℹ️  No Stripe customer found with this email.")
            return

        customer = customers[0]
        print(f"   👤 Customer ID: {customer.id}")
        
        # 2. List Subscriptions
        subscriptions = stripe.Subscription.list(customer=customer.id, status='all', limit=5).data
        
        if not subscriptions:
            print("   ℹ️  No subscriptions found for this customer.")
        else:
            for sub in subscriptions:
                status_icon = "✅" if sub.status == 'active' else "❌"
                print(f"   {status_icon} Subscription: {sub.id}")
                print(f"      Status: {sub.status}")
                print(f"      Plan: {sub.plan.nickname or sub.plan.id}")
                from datetime import datetime
                
                # Try multiple access methods
                cpe = getattr(sub, 'current_period_end', None)
                if cpe is None and isinstance(sub, dict):
                     cpe = sub.get('current_period_end')
                
                cpe_str = "N/A"
                if cpe:
                    cpe_str = datetime.fromtimestamp(cpe).strftime('%Y-%m-%d %H:%M:%S')
                
                print(f"      Current period end: {cpe_str} (Raw: {cpe})")
                print(f"      Cancel at period end: {sub.cancel_at_period_end}")
                
                # Debug: Print full object for inspection
                print(f"      [DEBUG] Full Object: {sub}")

                # Optional: Force cancel if active (commented out for safety, or add flag)
                # if sub.status == 'active':
                #    print("      Note: Subscription is still active in Stripe.")

    except Exception as e:
        print(f"❌ Error querying Stripe: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_stripe_subscription.py <email>")
        sys.exit(1)
        
    email = sys.argv[1]
    verify_stripe_subscription(email)
