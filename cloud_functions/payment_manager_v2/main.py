"""
Payment Manager V2 Cloud Function
Handles Stripe integration with Firestore backend.
Migrated from ES-based payment_manager to Firebase/Firestore.

Features:
- Stripe Checkout sessions for subscriptions and credit packs
- Webhook handling for payment events
- Subscription lifecycle management (cancel, reactivate)
- Credit balance tracking (synced with profile_manager_v2)
"""

import os
import json
import logging
import requests
from datetime import datetime, timezone, timedelta
from flask import jsonify
import stripe
from firestore_db import get_payment_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY', 'sk_test_placeholder')

# Profile Manager V2 URL (for credits sync)
PROFILE_MANAGER_V2_URL = os.environ.get('PROFILE_MANAGER_V2_URL', 'https://profile-manager-v2-pfnwjfp26a-ue.a.run.app')

# Price IDs - Created via Stripe API
STRIPE_PRICES = {
    # Subscriptions
    'subscription_monthly': 'price_1SfBO6Ifpb0uVZkCWaSvtevk',  # $15/mo
    'subscription_annual': 'price_1SfBO7Ifpb0uVZkCkY6JgQrx',   # $99/yr
    
    # Add-on Packs
    'addon_1_college': 'price_1SfBO7Ifpb0uVZkC7mEzsNeN',     # $9
    'addon_3_colleges': 'price_1SfBO8Ifpb0uVZkCJgHqELLf',    # $20
    'addon_5_colleges': 'price_1SfBO8Ifpb0uVZkCUtd6xh7o',    # $29
    'addon_10_colleges': 'price_1SfBO8Ifpb0uVZkCZhG9slEP',   # $49
    
    # Credit Packs
    'credit_pack_10': 'price_1SfBO8Ifpb0uVZkCZhG9slEP',  # $9 for 10 credits
}

# Product details for display and fulfillment
PRODUCTS = {
    'subscription_monthly': {
        'name': 'Stratia Admissions Monthly',
        'description': 'Full access to AI tools. Includes 20 fit analyses per month + unlimited AI chat.',
        'price': 1500,  # $15
        'type': 'subscription',
        'interval': 'month',
        'grants': {'access_full': True, 'ai_messages': -1, 'fit_analysis': 20}  # -1 = unlimited chat
    },
    'subscription_annual': {
        'name': 'Stratia Admissions Season Pass',
        'description': 'Best Value. 150 fit analyses + unlimited AI chat for one year.',
        'price': 9900,  # $99
        'type': 'subscription',
        'interval': 'year',
        'grants': {'access_full': True, 'ai_messages': -1, 'fit_analysis': 150}  # -1 = unlimited chat
    },
    'credit_pack_10': {
        'name': '10 Credit Pack',
        'description': 'Add 10 more fit analyses to your account.',
        'price': 900,  # $9
        'type': 'addon',
        'grants': {'fit_analysis': 10}
    },
}

def add_cors_headers(response_data, status_code=200):
    """Add CORS headers to response"""
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-User-Email',
        'Access-Control-Max-Age': '3600'
    }
    return (jsonify(response_data), status_code, headers)


def get_user_purchases(user_id):
    """Get user's current purchases and usage limits from Firestore"""
    try:
        db = get_payment_db()
        purchases = db.get_purchases(user_id)
        if purchases:
            return purchases
        return get_default_purchases()
    except Exception as e:
        logger.info(f"No purchases found for user {user_id}: {e}")
        return get_default_purchases()


def get_default_purchases():
    """Default purchases for new/free users"""
    return {
        # Subscription status
        'subscription_active': False,
        'subscription_plan': None,
        'subscription_end_date': None,
        'subscription_cancel_at_period_end': False,
        'subscription_current_period_end': None,
        'trial_started': None,
        'trial_ended': False,
        
        # Stripe IDs for subscription management
        'stripe_customer_id': None,
        'stripe_subscription_id': None,
        
        # Monthly AI messages (resets each month)
        'ai_messages_limit': 30,
        'ai_messages_used': 0,
        'ai_messages_reset_date': None,
        
        # Fit analysis credits (3 total for free, replenished on subscription)
        'fit_analysis_credits': 3,
        'fit_analysis_used': 0,
        'analyzed_colleges': [],
        
        # Add-on college slots
        'college_slots_purchased': 0,
        
        # Credit packs
        'credit_packs_purchased': 0,
        
        # Purchase history
        'purchases': [],
        'created_at': datetime.now(timezone.utc).isoformat(),
        'updated_at': datetime.now(timezone.utc).isoformat()
    }


def update_user_purchases(user_id, grants, purchase_details):
    """Update user's purchases after successful payment - saves to Firestore"""
    try:
        db = get_payment_db()
        
        # Get current purchases
        current = get_user_purchases(user_id)
        
        # Store Stripe IDs if available
        if 'stripe_customer_id' in purchase_details and purchase_details['stripe_customer_id']:
            current['stripe_customer_id'] = purchase_details['stripe_customer_id']
        if 'stripe_subscription_id' in purchase_details and purchase_details['stripe_subscription_id']:
            current['stripe_subscription_id'] = purchase_details['stripe_subscription_id']
        if 'subscription_current_period_end' in purchase_details:
            current['subscription_current_period_end'] = purchase_details['subscription_current_period_end']
        
        # Apply grants based on type
        for key, value in grants.items():
            if key == 'access_full' and value:
                # Subscription activated
                current['subscription_active'] = True
                current['subscription_plan'] = purchase_details.get('plan', 'monthly')
                if purchase_details.get('plan') == 'annual':
                    end_date = datetime.now(timezone.utc) + timedelta(days=365)
                else:
                    end_date = datetime.now(timezone.utc) + timedelta(days=30)
                current['subscription_end_date'] = end_date.isoformat()
                current['subscription_cancel_at_period_end'] = False
                
            elif key == 'ai_messages':
                current['ai_messages_limit'] = value if value != -1 else 999999
                current['ai_messages_used'] = 0
                current['ai_messages_reset_date'] = datetime.now(timezone.utc).isoformat()
                
            elif key == 'fit_analysis':
                current['fit_analysis_credits'] = current.get('fit_analysis_credits', 0) + value
                
            elif key == 'college_slots':
                current['college_slots_purchased'] = current.get('college_slots_purchased', 0) + value
        
        # Add purchase record
        if 'purchases' not in current:
            current['purchases'] = []
        current['purchases'].append({
            **purchase_details,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        current['updated_at'] = datetime.now(timezone.utc).isoformat()
        current['user_email'] = user_id
        
        # Save to Firestore (purchases collection)
        db.save_purchases(user_id, current)
        
        # Also add to purchase_history subcollection
        db.add_purchase_record(user_id, purchase_details)
        
        # Sync credits collection for frontend consistency
        credits_update = {
            'credits_remaining': current.get('fit_analysis_credits', 0),
            'credits_total': current.get('fit_analysis_credits', 0),
            'subscription_active': current.get('subscription_active', False),
            'subscription_plan': current.get('subscription_plan'),
            'subscription_expires': current.get('subscription_end_date'),
            'tier': 'season_pass' if current.get('subscription_plan') == 'annual' else ('monthly' if current.get('subscription_active') else 'free')
        }
        db.save_credits(user_id, credits_update)
        
        logger.info(f"[PaymentManagerV2] Updated purchases and credits for {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to update purchases for {user_id}: {e}")
        return False


def handle_create_checkout(request, user_id):
    """Create Stripe Checkout session"""
    try:
        data = request.get_json()
        product_id = data.get('product_id')
        quantity = data.get('quantity', 1)
        college_id = data.get('college_id')
        
        if product_id not in PRODUCTS:
            return add_cors_headers({'error': 'Invalid product'}, 400)
        
        product = PRODUCTS[product_id]
        
        FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://stratiaadmissions.com')
        success_url = f"{FRONTEND_URL}/payment-success?session_id={{CHECKOUT_SESSION_ID}}&product_id={product_id}"
        cancel_url = f"{FRONTEND_URL}/pricing"
        
        line_item = {
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': product['name'],
                    'description': product.get('description', ''),
                },
                'unit_amount': product['price'],
            },
            'quantity': quantity,
        }

        if product['type'] == 'subscription':
            line_item['price_data']['recurring'] = {
                'interval': product['interval']
            }

        customer_id = None
        if product['type'] == 'subscription':
            purchases = get_user_purchases(user_id)
            customer_id = purchases.get('stripe_customer_id')

        session_params = {
            'payment_method_types': ['card'],
            'line_items': [line_item],
            'mode': 'payment' if product['type'] != 'subscription' else 'subscription',
            'success_url': success_url,
            'cancel_url': cancel_url,
            'client_reference_id': user_id,
            'metadata': {
                'product_id': product_id,
                'quantity': quantity,
                'college_id': college_id or '',
                'user_email': user_id
            }
        }
        
        if customer_id:
            session_params['customer'] = customer_id
        else:
            session_params['customer_email'] = user_id

        session = stripe.checkout.Session.create(**session_params)
        
        return add_cors_headers({
            'success': True,
            'checkout_url': session.url,
            'session_id': session.id
        })
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {e}")
        return add_cors_headers({'error': str(e)}, 400)
    except Exception as e:
        logger.error(f"Checkout error: {e}")
        return add_cors_headers({'error': 'Failed to create checkout'}, 500)


def handle_webhook(request):
    """Handle Stripe webhooks for payment confirmation"""
    webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature', '')
    
    try:
        if webhook_secret:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        else:
            event = json.loads(payload)
            logger.warning("Webhook signature verification skipped - no secret configured")
        
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            handle_successful_payment(session)
        elif event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            logger.info(f"Payment succeeded: {payment_intent['id']}")
        elif event['type'] in ['customer.subscription.created', 'customer.subscription.updated', 
                                 'customer.subscription.deleted', 'invoice.payment_succeeded', 
                                 'invoice.payment_failed']:
            handle_subscription_lifecycle_webhooks(event)
        
        return add_cors_headers({'received': True})
        
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        return add_cors_headers({'error': 'Invalid payload'}, 400)
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {e}")
        return add_cors_headers({'error': 'Invalid signature'}, 400)


def handle_successful_payment(session):
    """Process successful payment and grant access"""
    user_id = session.get('client_reference_id')
    metadata = session.get('metadata', {})
    product_id = metadata.get('product_id')
    quantity = int(metadata.get('quantity', 1))
    college_id = metadata.get('college_id')
    
    if not user_id or not product_id:
        logger.error(f"Missing user_id or product_id in session: {session['id']}")
        return
    
    product = PRODUCTS.get(product_id)
    if not product:
        logger.error(f"Unknown product: {product_id}")
        return
    
    # Calculate grants based on quantity
    grants = {}
    for key, value in product['grants'].items():
        if isinstance(value, int):
            grants[key] = value * quantity
        else:
            grants[key] = value
    
    # Record purchase details
    purchase_details = {
        'product_id': product_id,
        'product_name': product['name'],
        'amount': session.get('amount_total', product['price'] * quantity),
        'quantity': quantity,
        'college_id': college_id,
        'stripe_session_id': session['id'],
        'payment_status': session.get('payment_status', 'paid')
    }
    
    # For subscriptions, capture Stripe IDs
    if product['type'] == 'subscription':
        purchase_details['stripe_customer_id'] = session.get('customer')
        purchase_details['stripe_subscription_id'] = session.get('subscription')
        purchase_details['plan'] = product.get('interval', 'monthly')
        if session.get('subscription'):
            try:
                subscription = stripe.Subscription.retrieve(session['subscription'])
                purchase_details['subscription_current_period_end'] = datetime.fromtimestamp(
                    subscription.current_period_end, tz=timezone.utc
                ).isoformat()
            except Exception as e:
                logger.error(f"Error retrieving subscription details: {e}")
    
    # Update user's purchases
    success = update_user_purchases(user_id, grants, purchase_details)
    
    if success:
        logger.info(f"Successfully processed payment for {user_id}: {product_id} x{quantity}")
    else:
        logger.error(f"Failed to update purchases for {user_id}")


def handle_subscription_lifecycle_webhooks(event):
    """Process subscription lifecycle webhook events - uses Firestore"""
    event_type = event['type']
    
    try:
        db = get_payment_db()
        
        if event_type == 'customer.subscription.created':
            subscription = event['data']['object']
            customer_id = subscription.get('customer')
            subscription_id = subscription.get('id')
            logger.info(f"Subscription created: {subscription_id} for customer: {customer_id}")
            
        elif event_type == 'customer.subscription.updated':
            subscription = event['data']['object']
            customer_id = subscription.get('customer')
            subscription_id = subscription.get('id')
            cancel_at_period_end = subscription.get('cancel_at_period_end', False)
            
            logger.info(f"Subscription updated: {subscription_id}, cancel_at_period_end={cancel_at_period_end}")
            
            # Get user email from Stripe customer
            try:
                customer = stripe.Customer.retrieve(customer_id)
                user_email = customer.get('email')
                
                if user_email:
                    purchases = db.get_purchases(user_email)
                    if purchases and purchases.get('stripe_subscription_id') == subscription_id:
                        purchases['subscription_cancel_at_period_end'] = cancel_at_period_end
                        purchases['updated_at'] = datetime.now(timezone.utc).isoformat()
                        
                        if subscription.get('current_period_end'):
                            purchases['subscription_current_period_end'] = datetime.fromtimestamp(
                                subscription.get('current_period_end'), timezone.utc
                            ).isoformat()
                        
                        db.save_purchases(user_email, purchases)
                        logger.info(f"Updated subscription for {user_email}: cancel_at_period_end={cancel_at_period_end}")
                    else:
                        logger.warning(f"Subscription ID mismatch for user: {user_email}")
                else:
                    logger.warning(f"No email found for customer: {customer_id}")
                    
            except Exception as e:
                logger.error(f"Error updating user for subscription {subscription_id}: {e}")
            
        elif event_type == 'customer.subscription.deleted':
            subscription = event['data']['object']
            customer_id = subscription.get('customer')
            subscription_id = subscription.get('id')
            
            logger.info(f"Subscription deleted: {subscription_id}")
            
            try:
                customer = stripe.Customer.retrieve(customer_id)
                user_email = customer.get('email')
                
                if user_email:
                    purchases = db.get_purchases(user_email)
                    if purchases and purchases.get('stripe_subscription_id') == subscription_id:
                        purchases['subscription_active'] = False
                        purchases['updated_at'] = datetime.now(timezone.utc).isoformat()
                        db.save_purchases(user_email, purchases)
                        
                        # Downgrade tier in credits
                        db.save_credits(user_email, {
                            'tier': 'free',
                            'subscription_active': False,
                            'subscription_plan': None
                        })
                        
                        logger.info(f"Deactivated subscription for {user_email}")
                    else:
                        logger.warning(f"Subscription ID mismatch for deleted sub: {user_email}")
                else:
                    logger.warning(f"No email found for customer: {customer_id}")
                    
            except Exception as e:
                logger.error(f"Error finding user for subscription {subscription_id}: {e}")
                
        elif event_type == 'invoice.payment_succeeded':
            invoice = event['data']['object']
            subscription_id = invoice.get('subscription')
            if subscription_id:
                logger.info(f"Payment succeeded for subscription: {subscription_id}")
                
        elif event_type == 'invoice.payment_failed':
            invoice = event['data']['object']
            subscription_id = invoice.get('subscription')
            customer_email = invoice.get('customer_email')
            logger.warning(f"Payment failed for subscription: {subscription_id}, customer: {customer_email}")
            
    except Exception as e:
        logger.error(f"Error handling subscription webhook {event_type}: {e}")


def handle_cancel_subscription(request, user_id):
    """Cancel subscription at period end"""
    try:
        db = get_payment_db()
        purchases = get_user_purchases(user_id)
        subscription_id = purchases.get('stripe_subscription_id')
        
        if not subscription_id:
            return add_cors_headers({'error': 'No active subscription found'}, 404)
        
        if not purchases.get('subscription_active'):
            return add_cors_headers({'error': 'Subscription is not active'}, 400)
        
        try:
            stripe.Subscription.modify(subscription_id, cancel_at_period_end=True)
            
            purchases['subscription_cancel_at_period_end'] = True
            purchases['updated_at'] = datetime.now(timezone.utc).isoformat()
            db.save_purchases(user_id, purchases)
            
            return add_cors_headers({
                'success': True,
                'message': 'Subscription will be canceled at period end',
                'cancel_at': purchases.get('subscription_current_period_end') or purchases.get('subscription_end_date'),
                'credits_valid_until': purchases.get('subscription_end_date')
            })
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error canceling subscription: {e}")
            return add_cors_headers({'error': f'Failed to cancel subscription: {str(e)}'}, 500)
            
    except Exception as e:
        logger.error(f"Error canceling subscription for {user_id}: {e}")
        return add_cors_headers({'error': 'Failed to cancel subscription'}, 500)


def handle_reactivate_subscription(request, user_id):
    """Reactivate a scheduled cancellation"""
    try:
        db = get_payment_db()
        purchases = get_user_purchases(user_id)
        subscription_id = purchases.get('stripe_subscription_id')
        
        if not subscription_id:
            return add_cors_headers({'error': 'No subscription found'}, 404)
        
        if not purchases.get('subscription_cancel_at_period_end'):
            return add_cors_headers({'error': 'Subscription is not scheduled for cancellation'}, 400)
        
        try:
            stripe.Subscription.modify(subscription_id, cancel_at_period_end=False)
            
            purchases['subscription_cancel_at_period_end'] = False
            purchases['updated_at'] = datetime.now(timezone.utc).isoformat()
            db.save_purchases(user_id, purchases)
            
            return add_cors_headers({
                'success': True,
                'message': 'Subscription reactivated successfully',
                'next_billing_date': purchases.get('subscription_current_period_end') or purchases.get('subscription_end_date')
            })
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error reactivating subscription: {e}")
            return add_cors_headers({'error': f'Failed to reactivate subscription: {str(e)}'}, 500)
            
    except Exception as e:
        logger.error(f"Error reactivating subscription for {user_id}: {e}")
        return add_cors_headers({'error': 'Failed to reactivate subscription'}, 500)


def handle_get_subscription_status(request, user_id):
    """Get current subscription status including cancellation details"""
    try:
        purchases = get_user_purchases(user_id)
        
        subscription_info = {
            'subscription_active': purchases.get('subscription_active', False),
            'subscription_plan': purchases.get('subscription_plan'),
            'subscription_end_date': purchases.get('subscription_end_date'),
            'subscription_cancel_at_period_end': purchases.get('subscription_cancel_at_period_end', False),
            'subscription_current_period_end': purchases.get('subscription_current_period_end'),
            'fit_analysis_credits': purchases.get('fit_analysis_credits', 0),
            'ai_messages_limit': purchases.get('ai_messages_limit', 30),
            'stripe_customer_id': purchases.get('stripe_customer_id'),
            'stripe_subscription_id': purchases.get('stripe_subscription_id')
        }
        
        return add_cors_headers({
            'success': True,
            'subscription': subscription_info
        })
        
    except Exception as e:
        logger.error(f"Error getting subscription status for {user_id}: {e}")
        return add_cors_headers({'error': 'Failed to get subscription status'}, 500)


def handle_get_purchases(request, user_id):
    """Get user's current purchases and available credits"""
    purchases = get_user_purchases(user_id)
    
    available = {
        'explorer_access': purchases.get('explorer_access', False),
        'college_slots_available': purchases.get('college_slots', 2) - purchases.get('college_slots_used', 0),
        'college_slots_total': purchases.get('college_slots', 2),
        'fit_analysis_available': purchases.get('fit_analysis_credits', 3) - purchases.get('fit_analysis_used', 0),
        'fit_analysis_total': purchases.get('fit_analysis_credits', 3),
        'essay_strategy_available': purchases.get('essay_strategy', 0) - purchases.get('essay_strategy_used', 0),
        'app_readiness_available': purchases.get('app_readiness', 0) - purchases.get('app_readiness_used', 0),
        'ai_messages_available': purchases.get('ai_messages_limit', 30) - purchases.get('ai_messages_used', 0) if not purchases.get('ai_unlimited') else 'unlimited',
        'ai_unlimited': purchases.get('ai_unlimited', False),
        'is_free_tier': not purchases.get('subscription_active', False) and len(purchases.get('purchases', [])) == 0,
        
        # Subscription Details
        'subscription_active': purchases.get('subscription_active', False),
        'subscription_plan': purchases.get('subscription_plan'),
        'subscription_end_date': purchases.get('subscription_end_date'),
        'subscription_cancel_at_period_end': purchases.get('subscription_cancel_at_period_end', False),
        'subscription_current_period_end': purchases.get('subscription_current_period_end')
    }
    
    return add_cors_headers({
        'success': True,
        'purchases': available,
        'purchase_history': purchases.get('purchases', [])
    })


def handle_use_credit(request, user_id):
    """Use a credit (e.g., when running fit analysis)"""
    try:
        db = get_payment_db()
        data = request.get_json()
        credit_type = data.get('credit_type')
        college_id = data.get('college_id')
        
        valid_types = ['college_slots', 'fit_analysis', 'essay_strategy', 'app_readiness', 'ai_messages']
        if credit_type not in valid_types:
            return add_cors_headers({'error': 'Invalid credit type'}, 400)
        
        purchases = get_user_purchases(user_id)
        
        if credit_type == 'ai_messages' and purchases.get('ai_unlimited'):
            return add_cors_headers({'success': True, 'unlimited': True})
        
        available = purchases.get(credit_type, 0) - purchases.get(f'{credit_type}_used', 0)
        if available <= 0:
            return add_cors_headers({
                'error': 'No credits available',
                'credit_type': credit_type,
                'available': 0,
                'upgrade_required': True
            }, 403)
        
        purchases[f'{credit_type}_used'] = purchases.get(f'{credit_type}_used', 0) + 1
        purchases['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        if college_id and credit_type in ['fit_analysis', 'essay_strategy', 'app_readiness']:
            if 'college_usage' not in purchases:
                purchases['college_usage'] = {}
            if college_id not in purchases['college_usage']:
                purchases['college_usage'][college_id] = {}
            purchases['college_usage'][college_id][credit_type] = True
        
        db.save_purchases(user_id, purchases)
        
        return add_cors_headers({
            'success': True,
            'credit_type': credit_type,
            'remaining': purchases.get(credit_type, 0) - purchases.get(f'{credit_type}_used', 0)
        })
        
    except Exception as e:
        logger.error(f"Error using credit: {e}")
        return add_cors_headers({'error': 'Failed to use credit'}, 500)


def handle_check_access(request, user_id):
    """Check if user has access to a specific feature"""
    try:
        data = request.get_json() if request.method == 'POST' else {}
        feature = data.get('feature') or request.args.get('feature')
        college_id = data.get('college_id') or request.args.get('college_id')
        
        purchases = get_user_purchases(user_id)
        
        has_access = False
        reason = ''
        
        if feature == 'explorer':
            has_access = purchases.get('explorer_access', False)
            reason = 'Explorer Pass required' if not has_access else ''
            
        elif feature == 'add_college':
            available = purchases.get('college_slots', 2) - purchases.get('college_slots_used', 0)
            has_access = available > 0
            reason = f'{available} slots available' if has_access else 'No college slots available'
            
        elif feature == 'fit_analysis':
            available = purchases.get('fit_analysis_credits', 3) - purchases.get('fit_analysis_used', 0)
            has_access = available > 0
            if college_id and purchases.get('college_usage', {}).get(college_id, {}).get('fit_analysis'):
                has_access = True
                reason = 'Already unlocked for this college'
            else:
                reason = f'{available} analyses available' if has_access else 'No fit analyses available'
                
        elif feature == 'ai_chat':
            if purchases.get('ai_unlimited'):
                has_access = True
                reason = 'Unlimited access'
            else:
                available = purchases.get('ai_messages_limit', 30) - purchases.get('ai_messages_used', 0)
                has_access = available > 0
                reason = f'{available} messages remaining' if has_access else 'No messages available'
        
        return add_cors_headers({
            'success': True,
            'has_access': has_access,
            'reason': reason,
            'feature': feature
        })
        
    except Exception as e:
        logger.error(f"Error checking access: {e}")
        return add_cors_headers({'error': 'Failed to check access'}, 500)


def payment_manager_v2(request):
    """Main entry point for payment manager v2 cloud function"""
    
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return add_cors_headers({}, 204)
    
    # Get path
    path = request.path.strip('/')
    path_parts = path.split('/') if path else []
    
    # Get user ID from header or request
    user_id = request.headers.get('X-User-Email', '')
    if not user_id and request.method == 'POST':
        data = request.get_json(silent=True) or {}
        user_id = data.get('user_email', data.get('user_id', ''))
    
    if not path_parts:
        return add_cors_headers({'error': 'No endpoint specified'}, 400)
    
    endpoint = path_parts[0]
    
    try:
        # Webhook endpoint (no auth required)
        if endpoint == 'webhook' and request.method == 'POST':
            return handle_webhook(request)
        
        # All other endpoints require user_id
        if not user_id:
            return add_cors_headers({'error': 'User not authenticated'}, 401)
        
        # Route to handlers
        if endpoint == 'checkout' and request.method == 'POST':
            return handle_create_checkout(request, user_id)
        elif endpoint == 'purchases' and request.method == 'GET':
            return handle_get_purchases(request, user_id)
        elif endpoint == 'use-credit' and request.method == 'POST':
            return handle_use_credit(request, user_id)
        elif endpoint == 'check-access':
            return handle_check_access(request, user_id)
        elif endpoint == 'cancel-subscription' and request.method == 'POST':
            return handle_cancel_subscription(request, user_id)
        elif endpoint == 'reactivate-subscription' and request.method == 'POST':
            return handle_reactivate_subscription(request, user_id)
        elif endpoint == 'subscription-status' and request.method == 'GET':
            return handle_get_subscription_status(request, user_id)
        elif endpoint == 'products' and request.method == 'GET':
            return add_cors_headers({
                'success': True,
                'products': PRODUCTS,
                'stripe_configured': True
            })
        else:
            return add_cors_headers({'error': 'Endpoint not found'}, 404)
            
    except Exception as e:
        logger.error(f"Payment manager v2 error: {e}")
        return add_cors_headers({'error': str(e)}, 500)
