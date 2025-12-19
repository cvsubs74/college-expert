"""
Payment Manager Cloud Function
Handles Stripe integration for CollegeAI Pro pricing:
- Explorer Pass ($29)
- College slots ($9 each, bundles available)
- Add-ons (Fit Analysis $19, Essay Strategy $29, App Readiness $39)
- Premium bundles ($99, $249, $499)
"""

import os
import json
import logging
import hashlib
from datetime import datetime, timezone, timedelta
from flask import jsonify
import stripe
from elasticsearch import Elasticsearch

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY', 'sk_test_placeholder')

# Initialize Elasticsearch
ES_HOST = os.environ.get('ES_HOST', 'https://college-search-9522040934.us-east1.run.app')
ES_API_KEY = os.environ.get('ES_API_KEY', '')
ES_USER_PURCHASES_INDEX = 'user_purchases'
ES_USER_USAGE_INDEX = 'user_usage'

try:
    es_client = Elasticsearch(
        ES_HOST,
        api_key=ES_API_KEY,
        verify_certs=True,
        request_timeout=30
    )
except Exception as e:
    logger.error(f"Failed to initialize Elasticsearch: {e}")
    es_client = None

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
    'credit_pack_10': 'price_1SfBO8Ifpb0uVZkCZhG9slEP',  # $5 for 10 credits (using placeholder)
}

# Product details for display and fulfillment
PRODUCTS = {
    'subscription_monthly': {
        'name': 'CollegeAI Monthly',
        'price': 1500,  # $15
        'type': 'subscription',
        'interval': 'month',
        'grants': {'access_full': True, 'ai_messages': -1, 'fit_analysis': 20}  # -1 = unlimited chat
    },
    'subscription_annual': {
        'name': 'CollegeAI Season Pass',
        'price': 9900,  # $99
        'type': 'subscription',
        'interval': 'year',
        'grants': {'access_full': True, 'ai_messages': -1, 'fit_analysis': 150}  # -1 = unlimited chat
    },
    'credit_pack_10': {
        'name': '10 Credit Pack',
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

def get_user_hash(user_id):
    """Generate consistent hash for user ID"""
    return hashlib.md5(user_id.encode()).hexdigest()[:12]

def get_user_purchases(user_id):
    """Get user's current purchases and usage limits"""
    if not es_client:
        return get_default_purchases()
    
    try:
        user_hash = get_user_hash(user_id)
        doc_id = f"purchases_{user_hash}"
        
        result = es_client.get(index=ES_USER_PURCHASES_INDEX, id=doc_id)
        return result['_source']
    except Exception as e:
        logger.info(f"No purchases found for user {user_id}: {e}")
        return get_default_purchases()

def get_default_purchases():
    """Default purchases for new/free users (30-day trial eligible)"""
    return {
        # Subscription status
        'subscription_active': False,
        'subscription_plan': None,  # 'monthly' or 'annual'
        'subscription_end_date': None,
        'trial_started': None,
        'trial_ended': False,
        
        # Monthly AI messages (resets each month)
        'ai_messages_limit': 30,  # Free tier: 30/month
        'ai_messages_used': 0,
        'ai_messages_reset_date': None,
        
        # Fit analysis credits (3 total for free, replenished on subscription)
        'fit_analysis_credits': 3,
        'fit_analysis_used': 0,
        'analyzed_colleges': [],  # List of college IDs already analyzed
        
        # Add-on college slots (beyond free 3)
        'college_slots_purchased': 0,
        
        # Purchase history
        'purchases': [],
        'created_at': datetime.now(timezone.utc).isoformat(),
        'updated_at': datetime.now(timezone.utc).isoformat()
    }

def update_user_purchases(user_id, grants, purchase_details):
    """Update user's purchases after successful payment"""
    if not es_client:
        logger.error("Elasticsearch not available")
        return False
    
    try:
        user_hash = get_user_hash(user_id)
        doc_id = f"purchases_{user_hash}"
        
        # Get current purchases
        current = get_user_purchases(user_id)
        
        # Apply grants based on type
        for key, value in grants.items():
            if key == 'access_full' and value:
                # Subscription activated
                current['subscription_active'] = True
                current['subscription_plan'] = purchase_details.get('plan', 'monthly')
                # Set end date based on plan
                if purchase_details.get('plan') == 'annual':
                    end_date = datetime.now(timezone.utc) + timedelta(days=365)
                else:
                    end_date = datetime.now(timezone.utc) + timedelta(days=30)
                current['subscription_end_date'] = end_date.isoformat()
                
            elif key == 'ai_messages':
                # Subscription sets monthly limit to 100
                current['ai_messages_limit'] = value
                # Reset used count for new billing period
                current['ai_messages_used'] = 0
                current['ai_messages_reset_date'] = datetime.now(timezone.utc).isoformat()
                
            elif key == 'fit_analysis':
                # Add fit analysis credits
                current['fit_analysis_credits'] = current.get('fit_analysis_credits', 0) + value
                
            elif key == 'college_slots':
                # Add purchased college slots
                current['college_slots_purchased'] = current.get('college_slots_purchased', 0) + value
        
        # Add purchase record
        current['purchases'].append({
            **purchase_details,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        current['updated_at'] = datetime.now(timezone.utc).isoformat()
        current['user_email'] = user_id
        
        # Save to Elasticsearch
        es_client.index(index=ES_USER_PURCHASES_INDEX, id=doc_id, body=current)
        
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
        college_id = data.get('college_id')  # For per-college add-ons
        
        if product_id not in PRODUCTS:
            return add_cors_headers({'error': 'Invalid product'}, 400)
        
        product = PRODUCTS[product_id]
        price_id = STRIPE_PRICES.get(product_id)
        
        if not price_id:
            return add_cors_headers({
                'error': 'Stripe not configured',
                'message': 'Payment system is being set up. Please check back soon.',
                'setup_required': True
            }, 503)
        
        # Create checkout session - redirect to frontend, not backend
        FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://college-strategy.web.app')
        success_url = f"{FRONTEND_URL}/payment-success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{FRONTEND_URL}/pricing"
        
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': quantity,
            }],
            mode='payment' if product['type'] != 'subscription' else 'subscription',
            success_url=success_url,
            cancel_url=cancel_url,
            client_reference_id=user_id,
            metadata={
                'product_id': product_id,
                'quantity': quantity,
                'college_id': college_id or '',
                'user_email': user_id
            }
        )
        
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
            # For testing without webhook signature verification
            event = json.loads(payload)
            logger.warning("Webhook signature verification skipped - no secret configured")
        
        # Handle the event
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            handle_successful_payment(session)
        elif event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            logger.info(f"Payment succeeded: {payment_intent['id']}")
        
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
    
    # Update user's purchases
    success = update_user_purchases(user_id, grants, purchase_details)
    
    if success:
        logger.info(f"Successfully processed payment for {user_id}: {product_id} x{quantity}")
    else:
        logger.error(f"Failed to update purchases for {user_id}")

def handle_get_purchases(request, user_id):
    """Get user's current purchases and available credits"""
    purchases = get_user_purchases(user_id)
    
    # Calculate available credits
    available = {
        'explorer_access': purchases.get('explorer_access', False),
        'college_slots_available': purchases.get('college_slots', 2) - purchases.get('college_slots_used', 0),
        'college_slots_total': purchases.get('college_slots', 2),
        'fit_analysis_available': purchases.get('fit_analysis', 1) - purchases.get('fit_analysis_used', 0),
        'fit_analysis_total': purchases.get('fit_analysis', 1),
        'essay_strategy_available': purchases.get('essay_strategy', 0) - purchases.get('essay_strategy_used', 0),
        'app_readiness_available': purchases.get('app_readiness', 0) - purchases.get('app_readiness_used', 0),
        'ai_messages_available': purchases.get('ai_messages', 5) - purchases.get('ai_messages_used', 0) if not purchases.get('ai_unlimited') else 'unlimited',
        'ai_unlimited': purchases.get('ai_unlimited', False),
        'is_free_tier': not purchases.get('explorer_access', False) and len(purchases.get('purchases', [])) == 0
    }
    
    return add_cors_headers({
        'success': True,
        'purchases': available,
        'purchase_history': purchases.get('purchases', [])
    })

def handle_use_credit(request, user_id):
    """Use a credit (e.g., when adding a college to list or running fit analysis)"""
    try:
        data = request.get_json()
        credit_type = data.get('credit_type')  # college_slots, fit_analysis, essay_strategy, app_readiness, ai_messages
        college_id = data.get('college_id')  # For tracking which college
        
        valid_types = ['college_slots', 'fit_analysis', 'essay_strategy', 'app_readiness', 'ai_messages']
        if credit_type not in valid_types:
            return add_cors_headers({'error': 'Invalid credit type'}, 400)
        
        # Get current purchases
        purchases = get_user_purchases(user_id)
        
        # Check if unlimited (for AI messages)
        if credit_type == 'ai_messages' and purchases.get('ai_unlimited'):
            return add_cors_headers({'success': True, 'unlimited': True})
        
        # Check availability
        available = purchases.get(credit_type, 0) - purchases.get(f'{credit_type}_used', 0)
        if available <= 0:
            return add_cors_headers({
                'error': 'No credits available',
                'credit_type': credit_type,
                'available': 0,
                'upgrade_required': True
            }, 403)
        
        # Use the credit
        user_hash = get_user_hash(user_id)
        doc_id = f"purchases_{user_hash}"
        
        purchases[f'{credit_type}_used'] = purchases.get(f'{credit_type}_used', 0) + 1
        purchases['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        # Track college-specific usage if applicable
        if college_id and credit_type in ['fit_analysis', 'essay_strategy', 'app_readiness']:
            if 'college_usage' not in purchases:
                purchases['college_usage'] = {}
            if college_id not in purchases['college_usage']:
                purchases['college_usage'][college_id] = {}
            purchases['college_usage'][college_id][credit_type] = True
        
        es_client.index(index=ES_USER_PURCHASES_INDEX, id=doc_id, body=purchases)
        
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
        
        # Check specific feature access
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
            available = purchases.get('fit_analysis', 1) - purchases.get('fit_analysis_used', 0)
            has_access = available > 0
            # Check if already used for this college
            if college_id and purchases.get('college_usage', {}).get(college_id, {}).get('fit_analysis'):
                has_access = True  # Already purchased for this college
                reason = 'Already unlocked for this college'
            else:
                reason = f'{available} analyses available' if has_access else 'No fit analyses available'
                
        elif feature == 'ai_chat':
            if purchases.get('ai_unlimited'):
                has_access = True
                reason = 'Unlimited access'
            else:
                available = purchases.get('ai_messages', 5) - purchases.get('ai_messages_used', 0)
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

def payment_manager(request):
    """Main entry point for payment manager cloud function"""
    
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
        elif endpoint == 'products' and request.method == 'GET':
            return add_cors_headers({
                'success': True,
                'products': PRODUCTS,
                'stripe_configured': not any(p.startswith('price_') for p in STRIPE_PRICES.values())
            })
        else:
            return add_cors_headers({'error': 'Endpoint not found'}, 404)
            
    except Exception as e:
        logger.error(f"Payment manager error: {e}")
        return add_cors_headers({'error': str(e)}, 500)
