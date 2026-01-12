"""
Credit management system for user subscriptions and credit tracking.
Handles free tier, pro subscriptions, credit packs, and usage tracking.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from firestore_db import get_db

logger = logging.getLogger(__name__)

# Credit tier configuration
FREE_TIER_CREDITS = 3
MONTHLY_TIER_CREDITS = 20
SEASON_PASS_CREDITS = 150
CREDIT_PACK_SIZE = 10
CREDIT_PACK_PRICE = 9.00  # $9 for 10 credits


def get_user_credits(user_id: str) -> Dict:
    """
    Get user's credit balance and tier info.
    
    Args:
        user_id: User's email address
        
    Returns:
        Dict with credit information:
        {
            "user_id": "...",
            "tier": "free" | "pro",
            "credits_total": 50,
            "credits_used": 12,
            "credits_remaining": 38,
            "subscription_active": bool,
            "subscription_expires": "...",
            "subscription_plan": "monthly" | "season_pass"
        }
    """
    try:
        db = get_db()
        credits = db.get_credits(user_id)
        
        if not credits:
            # Initialize for new user
            credits = initialize_user_credits(user_id)
        
        return credits
        
    except Exception as e:
        logger.error(f"[CREDITS] Error getting credits for {user_id}: {e}")
        # Return default free tier
        return initialize_user_credits(user_id)


def initialize_user_credits(user_id: str, tier: str = "free") -> Dict:
    """
    Initialize credit record for  new user.
    
    Args:
        user_id: User's email address
        tier: Initial tier ("free" or "pro")
        
    Returns:
        Initialized credit record
    """
    try:
        credits_total = FREE_TIER_CREDITS if tier == "free" else MONTHLY_TIER_CREDITS
        
        credit_record = {
            "user_id": user_id,
            "tier": tier,
            "credits_total": credits_total,
            "credits_used": 0,
            "credits_remaining": credits_total,
            "subscription_active": tier == "pro",
            "subscription_expires": None,
            "subscription_plan": None,
            "credit_history": [],
            "created_at": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat()
        }
        
        db = get_db()
        db.save_credits(user_id, credit_record)
        
        logger.info(f"[CREDITS] Initialized {tier} tier for {user_id}")
        return credit_record
        
    except Exception as e:
        logger.error(f"[CREDITS] Error initializing credits: {e}")
        return {
            "user_id": user_id,
            "tier": "free",
            "credits_total": FREE_TIER_CREDITS,
            "credits_used": 0,
            "credits_remaining": FREE_TIER_CREDITS
        }


def check_credits_available(user_id: str, credits_needed: int = 1) -> Dict:
    """
    Check if user has enough credits.
    
    Args:
        user_id: User's email address
        credits_needed: Number of credits required
        
    Returns:
        {
            "has_credits": bool,
            "credits_remaining": int,
            "credits_needed": int
        }
    """
    try:
        credits = get_user_credits(user_id)
        credits_remaining = credits.get('credits_remaining', 0)
        
        return {
            "has_credits": credits_remaining >= credits_needed,
            "credits_remaining": credits_remaining,
            "credits_needed": credits_needed
        }
        
    except Exception as e:
        logger.error(f"[CREDITS] Error checking credits: {e}")
        return {
            "has_credits": False,
            "credits_remaining": 0,
            "credits_needed": credits_needed
        }


def deduct_credit(user_id: str, credit_count: int = 1, reason: str = "fit_analysis") -> Dict:
    """
    Deduct credit(s) from user's balance.
    
    Args:
        user_id: User's email address
        credit_count: Number of credits to deduct
        reason: Reason for deduction
        
    Returns:
        {
            "success": bool,
            "credits_remaining": int,
            "credits_deducted": int,
            "reason": str
        }
    """
    try:
        db = get_db()
        credits = get_user_credits(user_id)
        
        # Check if enough credits
        if credits['credits_remaining'] < credit_count:
            logger.warning(f"[CREDITS] Insufficient credits for {user_id}")
            return {
                "success": False,
                "error": "Insufficient credits",
                "credits_remaining": credits['credits_remaining'],
                "credits_needed": credit_count
            }
        
        # Deduct credits
        credits['credits_used'] += credit_count
        credits['credits_remaining'] -= credit_count
        credits['last_updated'] = datetime.utcnow().isoformat()
        
        # Add to history
        if 'credit_history' not in credits:
            credits['credit_history'] = []
        
        credits['credit_history'].append({
            'date': datetime.utcnow().isoformat(),
            'amount': -credit_count,
            'reason': reason,
            'balance_after': credits['credits_remaining']
        })
        
        # Save to Firestore
        db.save_credits(user_id, credits)
        
        logger.info(f"[CREDITS] Deducted {credit_count} credits from {user_id}, remaining: {credits['credits_remaining']}")
        
        return {
            "success": True,
            "credits_remaining": credits['credits_remaining'],
            "credits_deducted": credit_count,
            "reason": reason
        }
        
    except Exception as e:
        logger.error(f"[CREDITS] Error deducting credits: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def add_credits(user_id: str, credit_count: int, source: str = "credit_pack") -> Dict:
    """
    Add credits to user's balance (from pack purchase or subscription).
    
    Args:
        user_id: User's email address
        credit_count: Number of credits to add
        source: Source of credits ("credit_pack", "subscription", "bonus")
        
    Returns:
        {
            "success": bool,
            "credits_added": int,
            "credits_remaining": int,
            "source": str
        }
    """
    try:
        db = get_db()
        credits = get_user_credits(user_id)
        
        # Add credits
        credits['credits_total'] += credit_count
        credits['credits_remaining'] += credit_count
        credits['last_updated'] = datetime.utcnow().isoformat()
        
        # Add to history
        if 'credit_history' not in credits:
            credits['credit_history'] = []
        
        credits['credit_history'].append({
            'date': datetime.utcnow().isoformat(),
            'amount': credit_count,
            'source': source,
            'balance_after': credits['credits_remaining']
        })
        
        # Save to Firestore
        db.save_credits(user_id, credits)
        
        logger.info(f"[CREDITS] Added {credit_count} credits to {user_id} from {source}")
        
        return {
            "success": True,
            "credits_added": credit_count,
            "credits_remaining": credits['credits_remaining'],
            "source": source
        }
        
    except Exception as e:
        logger.error(f"[CREDITS] Error adding credits: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def upgrade_subscription(user_id: str, subscription_expires: str = None, plan_type: str = 'monthly') -> Dict:
    """
    Upgrade user to Monthly or Season Pass tier.
    
    Args:
        user_id: User's email address
        subscription_expires: ISO format expiration date
        plan_type: "monthly" or "season_pass"
        
    Returns:
        {
            "success": bool,
            "tier": str,
            "credits_added": int,
            "subscription_expires": str
        }
    """
    try:
        db = get_db()
        credits = get_user_credits(user_id)
        
        # Determine credits to add
        if plan_type == 'season_pass':
            new_credits = SEASON_PASS_CREDITS
        else:  # monthly
            new_credits = MONTHLY_TIER_CREDITS
        
        # Set expiration if not provided
        if not subscription_expires:
            if plan_type == 'season_pass':
                # Season pass: 6 months
                expiry_date = datetime.utcnow() + timedelta(days=180)
            else:
                # Monthly: 30 days
                expiry_date = datetime.utcnow() + timedelta(days=30)
            subscription_expires = expiry_date.isoformat()
        
        # Update credits
        credits['tier'] = 'pro'
        credits['subscription_active'] = True
        credits['subscription_expires'] = subscription_expires
        credits['subscription_plan'] = plan_type
        credits['credits_total'] += new_credits
        credits['credits_remaining'] += new_credits
        credits['last_updated'] = datetime.utcnow().isoformat()
        
        # Add to history
        if 'credit_history' not in credits:
            credits['credit_history'] = []
        
        credits['credit_history'].append({
            'date': datetime.utcnow().isoformat(),
            'amount': new_credits,
            'source': f'subscription_{plan_type}',
            'balance_after': credits['credits_remaining']
        })
        
        # Save to Firestore
        db.save_credits(user_id, credits)
        
        logger.info(f"[CREDITS] Upgraded {user_id} to {plan_type}, added {new_credits} credits")
        
        return {
            "success": True,
            "tier": "pro",
            "credits_added": new_credits,
            "subscription_expires": subscription_expires,
            "subscription_plan": plan_type
        }
        
    except Exception as e:
        logger.error(f"[CREDITS] Error upgrading subscription: {e}")
        return {
            "success": False,
            "error": str(e)
        }
