
import os
import sys
import stripe
from datetime import datetime

def compare_dates(email):
    stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
    customers = stripe.Customer.list(email=email, limit=1).data
    if not customers:
        print("No customer found")
        return
    
    customer_id = customers[0].id
    subs = stripe.Subscription.list(customer=customer_id, status='all').data
    
    print(f"\nComparing Subscriptions for {email}:")
    print(f"{'Plan':<15} | {'ID':<20} | {'Start Date':<20} | {'Period End':<20} | {'Status'}")
    print("-" * 100)
    
    for sub in subs:
        # Fetch full details to guarantee field access
        full_sub = stripe.Subscription.retrieve(sub.id)
        
        plan = full_sub.plan.interval
        start = datetime.fromtimestamp(full_sub.start_date).strftime('%Y-%m-%d')
        end = datetime.fromtimestamp(full_sub.current_period_end).strftime('%Y-%m-%d')
        status = full_sub.status
        
        print(f"{plan:<15} | {full_sub.id:<20} | {start:<20} | {end:<20} | {status}")

if __name__ == "__main__":
    email = sys.argv[1]
    compare_dates(email)
