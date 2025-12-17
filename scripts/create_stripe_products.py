#!/usr/bin/env python3
"""
Create Stripe Products and Prices for CollegeAI Pro
Refreshed for "Retainer + Project Scope" model
"""

import stripe
import json
import os

# Load Stripe API key from environment variable
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
if not stripe.api_key:
    raise ValueError("STRIPE_SECRET_KEY environment variable is required")

# Product definitions
PRODUCTS = [
    # Subscriptions (Retainers)
    {
        "id": "subscription_monthly",
        "name": "CollegeAI Monthly",
        "description": "Full access to CollegeAI tools. Includes 100 AI messages/mo and 3 college analyses.",
        "price_cents": 1500,
        "recurring": {"interval": "month"},
        "metadata": {"type": "subscription", "plan": "monthly", "grants": "access_full,ai_messages:100,fit_analysis:3"}
    },
    {
        "id": "subscription_annual",
        "name": "CollegeAI Annual",
        "description": "Full access for the entire application cycle. Save $81! Includes 100 AI messages/mo and 3 college analyses.",
        "price_cents": 9900,
        "recurring": {"interval": "year"},
        "metadata": {"type": "subscription", "plan": "annual", "grants": "access_full,ai_messages:100,fit_analysis:3"}
    },

    # Add-on Packs (Scope Expansion) - One-time purchases
    {
        "id": "addon_1_college",
        "name": "+1 College Slot",
        "description": "Unlock deep strategy analysis for 1 additional college.",
        "price_cents": 900,
        "metadata": {"type": "addon", "grants": "college_slots:1"}
    },
    {
        "id": "addon_3_colleges",
        "name": "+3 College Slots",
        "description": "Unlock deep strategy analysis for 3 additional colleges. Save $7!",
        "price_cents": 2000,
        "metadata": {"type": "addon", "grants": "college_slots:3"}
    },
    {
        "id": "addon_5_colleges",
        "name": "+5 College Slots",
        "description": "Unlock deep strategy analysis for 5 additional colleges. Save $16!",
        "price_cents": 2900,
        "metadata": {"type": "addon", "grants": "college_slots:5"}
    },
    {
        "id": "addon_10_colleges",
        "name": "+10 College Slots",
        "description": "Unlock deep strategy analysis for 10 additional colleges. Best value!",
        "price_cents": 4900,
        "metadata": {"type": "addon", "grants": "college_slots:10"}
    }
]

def create_products():
    """Create all products and prices in Stripe"""
    created = {}
    
    print("Creating Stripe Products for CollegeAI Pro (New Model)...\n")
    
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
                    "product_id": product_def["id"]
                }
            }
            
            # Add recurring params if applicable
            if "recurring" in product_def:
                price_args["recurring"] = product_def["recurring"]
                
            price = stripe.Price.create(**price_args)
            
            created[product_def["id"]] = {
                "product_id": product.id,
                "price_id": price.id,
                "name": product_def["name"],
                "price": f"${product_def['price_cents'] / 100:.2f}"
            }
            
            print(f"✓ {product_def['name']}: {price.id}")
            
        except stripe.error.StripeError as e:
            print(f"✗ Error creating {product_def['name']}: {e}")
    
    print("\n" + "="*60)
    print("PRICE IDs FOR CODE UPDATE:")
    print("="*60 + "\n")
    
    # Output the price mapping for updating the code
    for product_id, data in created.items():
        print(f"'{product_id}': '{data['price_id']}',")
    
    print("\n" + "="*60)
    
    # Save to file for reference
    with open("stripe_products_new.json", "w") as f:
        json.dump(created, f, indent=2)
    
    return created

if __name__ == "__main__":
    create_products()
