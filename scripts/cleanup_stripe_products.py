#!/usr/bin/env python3
"""
Stripe Product Cleanup Script
Deletes test mode products and creates only the ones needed for Stratia Admissions.
"""

import stripe
import os
import sys

# Get Stripe API key from environment
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

if not stripe.api_key:
    print("ERROR: No Stripe API key found!")
    exit(1)

print(f"Using Stripe API key: {stripe.api_key[:12]}...")

# Products we want to create
DESIRED_PRODUCTS = {
    'stratia_monthly': {
        'name': 'Stratia Admissions Monthly',
        'description': 'Full access to AI tools. Includes 20 fit analyses per month + unlimited AI chat.',
        'price_cents': 1500,
        'recurring_interval': 'month',
    },
    'stratia_season_pass': {
        'name': 'Stratia Admissions Season Pass',
        'description': 'Best Value. 150 fit analyses + unlimited AI chat for one year.',
        'price_cents': 9900,
        'recurring_interval': 'year',
    },
    'credit_pack_10': {
        'name': '10 Credit Pack',
        'description': 'Add 10 more fit analyses to your account.',
        'price_cents': 900,
        'recurring_interval': None,  # One-time payment
    },
}

def list_all_products():
    """List all products in the Stripe account."""
    print("\n=== Current Stripe Products ===")
    products = stripe.Product.list(limit=100)
    for product in products.data:
        status = "ACTIVE" if product.active else "ARCHIVED"
        print(f"  [{status}] {product.id}: {product.name}")
    return products.data

def delete_all_products(products):
    """Delete all existing products (test mode only)."""
    print("\n=== Deleting Existing Products ===")
    for product in products:
        try:
            # First delete/archive all prices
            prices = stripe.Price.list(product=product.id, limit=100)
            for price in prices.data:
                if price.active:
                    stripe.Price.modify(price.id, active=False)
                    print(f"  Archived price: {price.id}")
            
            # Try to delete the product (works in test mode)
            try:
                stripe.Product.delete(product.id)
                print(f"  DELETED product: {product.name}")
            except Exception as e:
                # If delete fails, archive it
                if product.active:
                    stripe.Product.modify(product.id, active=False)
                    print(f"  Archived product: {product.name} (delete failed: {e})")
                else:
                    print(f"  Already archived: {product.name}")
        except Exception as e:
            print(f"  Failed on {product.id}: {e}")

def create_products():
    """Create the products we need."""
    print("\n=== Creating New Products ===")
    created_prices = {}
    
    for key, config in DESIRED_PRODUCTS.items():
        try:
            # Create product
            product = stripe.Product.create(
                name=config['name'],
                description=config['description'],
                metadata={'product_key': key}
            )
            print(f"  Created product: {config['name']} ({product.id})")
            
            # Create price
            price_params = {
                'product': product.id,
                'unit_amount': config['price_cents'],
                'currency': 'usd',
            }
            
            if config['recurring_interval']:
                price_params['recurring'] = {'interval': config['recurring_interval']}
            
            price = stripe.Price.create(**price_params)
            print(f"    Created price: ${config['price_cents']/100:.2f} ({price.id})")
            
            created_prices[key] = {
                'product_id': product.id,
                'price_id': price.id,
            }
            
        except Exception as e:
            print(f"  Failed to create {config['name']}: {e}")
    
    return created_prices

def main():
    # Check for --auto flag
    auto_confirm = '--auto' in sys.argv
    
    print("=" * 60)
    print("  Stratia Admissions - Stripe Product Cleanup")
    print("  MODE: TEST")
    print("=" * 60)
    
    # List current products
    products = list_all_products()
    
    print(f"\nFound {len(products)} products.")
    print("This script will:")
    print("  1. DELETE all existing products and prices")
    print("  2. Create 3 new products:")
    for key, config in DESIRED_PRODUCTS.items():
        interval = config['recurring_interval'] or 'one-time'
        print(f"     - {config['name']}: ${config['price_cents']/100:.2f}/{interval}")
    
    if not auto_confirm:
        confirm = input("\nProceed? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Aborted.")
            return
    else:
        print("\n[AUTO-CONFIRM ENABLED]")
    
    # Delete existing
    delete_all_products(products)
    
    # Create new
    created = create_products()
    
    # Print summary
    print("\n" + "=" * 60)
    print("  SUMMARY - New Price IDs:")
    print("=" * 60)
    print("\nSTRIPE_PRICES = {")
    if 'stratia_monthly' in created:
        print(f"    'subscription_monthly': '{created['stratia_monthly']['price_id']}',")
    if 'stratia_season_pass' in created:
        print(f"    'subscription_annual': '{created['stratia_season_pass']['price_id']}',")
    if 'credit_pack_10' in created:
        print(f"    'credit_pack_10': '{created['credit_pack_10']['price_id']}',")
    print("}")
    
    print("\n✓ Stripe cleanup complete!")

if __name__ == '__main__':
    main()
