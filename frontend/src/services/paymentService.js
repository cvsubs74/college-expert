/**
 * Payment Service
 * Handles Stripe integration for CollegeAI Pro
 */

// Stripe publishable key (safe to expose in frontend)
export const STRIPE_PUBLISHABLE_KEY = 'pk_test_51OYhyQIfpb0uVZkCY2fFSbJmDVGbhyMuAoE2AiM9MdKbdeT2sS0cdTlbMcEhBOY3wTQpqjR0lhbHnyJ9odPGpX7d001ZO1oHjB';

// API endpoint - will be set after deploying cloud function
const PAYMENT_API_URL = import.meta.env.VITE_PAYMENT_API_URL || 'https://payment-manager-pfnwjfp26a-ue.a.run.app';

/**
 * Get user's current purchases and available credits
 */
export const getUserPurchases = async (userEmail) => {
    try {
        const response = await fetch(`${PAYMENT_API_URL}/purchases`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-User-Email': userEmail,
            },
        });

        if (!response.ok) {
            throw new Error('Failed to fetch purchases');
        }

        return await response.json();
    } catch (error) {
        console.error('Error fetching purchases:', error);
        // Return default free tier
        return {
            success: true,
            purchases: {
                explorer_access: false,
                college_slots_available: 2,
                college_slots_total: 2,
                fit_analysis_available: 1,
                fit_analysis_total: 1,
                essay_strategy_available: 0,
                app_readiness_available: 0,
                ai_messages_available: 5,
                ai_unlimited: false,
                is_free_tier: true
            },
            purchase_history: []
        };
    }
};

/**
 * Create Stripe checkout session
 */
export const createCheckoutSession = async (userEmail, productId, quantity = 1, collegeId = null) => {
    try {
        const response = await fetch(`${PAYMENT_API_URL}/checkout`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-User-Email': userEmail,
            },
            body: JSON.stringify({
                product_id: productId,
                quantity,
                college_id: collegeId,
                user_email: userEmail,
            }),
        });

        const data = await response.json();

        if (data.setup_required) {
            // Stripe not yet configured
            return {
                success: false,
                setup_required: true,
                message: data.message || 'Payment system is being set up'
            };
        }

        if (data.checkout_url) {
            // Redirect to Stripe Checkout
            window.location.href = data.checkout_url;
            return { success: true, redirecting: true };
        }

        return data;
    } catch (error) {
        console.error('Error creating checkout:', error);
        return {
            success: false,
            error: error.message
        };
    }
};

/**
 * Check if user has access to a specific feature
 */
export const checkAccess = async (userEmail, feature, collegeId = null) => {
    try {
        const params = new URLSearchParams({ feature });
        if (collegeId) params.append('college_id', collegeId);

        const response = await fetch(`${PAYMENT_API_URL}/check-access?${params}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-User-Email': userEmail,
            },
        });

        if (!response.ok) {
            // Default to free tier limits
            return getDefaultAccess(feature);
        }

        return await response.json();
    } catch (error) {
        console.error('Error checking access:', error);
        return getDefaultAccess(feature);
    }
};

/**
 * Use a credit (when performing an action)
 */
export const useCredit = async (userEmail, creditType, collegeId = null) => {
    try {
        const response = await fetch(`${PAYMENT_API_URL}/use-credit`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-User-Email': userEmail,
            },
            body: JSON.stringify({
                credit_type: creditType,
                college_id: collegeId,
                user_email: userEmail,
            }),
        });

        return await response.json();
    } catch (error) {
        console.error('Error using credit:', error);
        return {
            success: false,
            error: error.message
        };
    }
};

/**
 * Get available products and prices
 */
export const getProducts = async () => {
    try {
        const response = await fetch(`${PAYMENT_API_URL}/products`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
        });

        return await response.json();
    } catch (error) {
        console.error('Error fetching products:', error);
        return { success: false, products: {} };
    }
};

/**
 * Default access for free tier (fallback)
 */
const getDefaultAccess = (feature) => {
    const defaults = {
        explorer: { has_access: false, reason: 'Explorer Pass required' },
        add_college: { has_access: true, reason: '2 slots available' },
        fit_analysis: { has_access: true, reason: '1 analysis available' },
        ai_chat: { has_access: true, reason: '5 messages remaining' },
    };

    return {
        success: true,
        ...(defaults[feature] || { has_access: false, reason: 'Unknown feature' }),
        feature
    };
};

/**
 * Product definitions (mirrors backend)
 * Updated with new credits-based pricing model
 */
export const PRODUCTS = {
    // New Credits-Based Pricing
    pro_annual: { name: 'Pro Annual', price: 99, type: 'subscription', credits: 50, description: '50 credits + priority support' },
    credit_pack_50: { name: '50 Credit Pack', price: 10, type: 'one_time', credits: 50, description: 'Add 50 fit analysis credits' },

    // Legacy products
    explorer_pass: { name: 'Explorer Pass', price: 29, type: 'one_time' },
    college_1: { name: '1 College', price: 9, type: 'one_time' },
    college_5: { name: '5 Colleges', price: 39, type: 'one_time', savings: 6 },
    college_10: { name: '10 Colleges', price: 69, type: 'one_time', savings: 21 },
    college_15: { name: '15 Colleges', price: 89, type: 'one_time', savings: 46 },
    fit_analysis: { name: 'Deep Fit Analysis', price: 19, type: 'per_college' },
    essay_strategy: { name: 'Essay Strategy Pack', price: 29, type: 'per_college' },
    app_readiness: { name: 'Application Readiness', price: 39, type: 'per_college' },
    bundle_starter: { name: 'Starter Pack', price: 99, originalPrice: 125, type: 'bundle' },
    bundle_application: { name: 'Application Ready', price: 249, originalPrice: 453, type: 'bundle' },
    bundle_full: { name: 'Full Counselor', price: 499, originalPrice: 1000, type: 'bundle' },
};

export default {
    getUserPurchases,
    createCheckoutSession,
    checkAccess,
    useCredit,
    getProducts,
    PRODUCTS,
};
