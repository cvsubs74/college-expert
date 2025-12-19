#!/usr/bin/env python3
"""
Create Stripe Products for Credits-Based Pricing Model

Products:
- Pro Annual: $99/year subscription with 50 credits
- Credit Pack 50: $10 one-time purchase for 50 credits

Usage:
  export STRIPE_SECRET_KEY="sk_test_..."
  python scripts/create_credits_products.py
"""

import stripe
import json
import os

# Load Stripe API key
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
if not stripe.api_key:
    print("ERROR: STRIPE_SECRET_KEY environment variable is required")
    print("Usage: export STRIPE_SECRET_KEY='sk_test_...' && python scripts/create_credits_products.py")
    exit(1)

# Credits-based products
PRODUCTS = [
    {
        "id": "pro_annual",
        "name": "CollegeAI Pro Annual",
        "description": "Pro subscription with 50 fit analysis credits. Unlimited colleges, priority support. Credits refresh yearly.",
        "price_cents": 9900,  # $99.00
        "recurring": {"interval": "year"},
        "metadata": {
            "type": "subscription",
            "plan": "pro_annual",
            "credits": "50",
            "tier": "pro"
        }
    },
    {
        "id": "credit_pack_50",
        "name": "50 Credit Pack",
        "description": "Add 50 fit analysis credits to your account. Each credit = 1 personalized fit analysis with infographic. Never expires.",
        "price_cents": 1000,  # $10.00
        "metadata": {
            "type": "credit_pack",
            "credits": "50"
        }
    }
]

def create_products():
    """Create credits products in Stripe"""
    created = {}
    
    print("\n" + "="*60)
    print("Creating Stripe Products for Credits-Based Pricing")
    print("="*60 + "\n")
    
    for product_def in PRODUCTS:
        try:
            # Create product
            product = stripe.Product.create(
                name=product_def["name"],
                description=product_def["description"],
                metadata={
                    "product_id": product_def["id"],
                    **product_def.get("metadata", {})
                }
            )
            
            # Create price
            price_args = {
                "product": product.id,
                "unit_amount": product_def["price_cents"],
                "currency": "usd",
                "metadata": {
                    "product_id": product_def["id"],
                    **product_def.get("metadata", {})
                }
            }
            
            # Add recurring for subscriptions
            if "recurring" in product_def:
                price_args["recurring"] = product_def["recurring"]
                
            price = stripe.Price.create(**price_args)
            
            created[product_def["id"]] = {
                "product_id": product.id,
                "price_id": price.id,
                "name": product_def["name"],
                "price": f"${product_def['price_cents'] / 100:.2f}",
                "credits": product_def["metadata"].get("credits", "0")
            }
            
            print(f"✓ Created: {product_def['name']}")
            print(f"  Product ID: {product.id}")
            print(f"  Price ID: {price.id}")
            print(f"  Price: ${product_def['price_cents'] / 100:.2f}")
            print(f"  Credits: {product_def['metadata'].get('credits', 'N/A')}")
            print()
            
        except stripe.error.StripeError as e:
            print(f"✗ Error creating {product_def['name']}: {e}")
    
    print("="*60)
    print("ADD THESE TO stripe_products.json:")
    print("="*60 + "\n")
    
    for product_id, data in created.items():
        print(f'  "{product_id}": {{')
        print(f'    "product_id": "{data["product_id"]}",')
        print(f'    "price_id": "{data["price_id"]}",')
        print(f'    "name": "{data["name"]}",')
        print(f'    "price": "{data["price"]}",')
        print(f'    "credits": {data["credits"]}')
        print('  },')
    
    print("\n" + "="*60)
    print("WEBHOOK SETUP REQUIRED:")
    print("="*60)
    print("""
After purchase, call these backend endpoints:

For pro_annual subscription:
  POST /upgrade-to-pro
  {"user_email": "...", "subscription_expires": "YYYY-MM-DD"}

For credit_pack_50 purchase:
  POST /add-credits  
  {"user_email": "...", "credit_count": 50, "source": "credit_pack"}
""")
    
    # Save to file
    output_file = "stripe_credits_products.json"
    with open(output_file, "w") as f:
        json.dump(created, f, indent=2)
    print(f"Saved to {output_file}")
    
    return created

if __name__ == "__main__":
    create_products()
