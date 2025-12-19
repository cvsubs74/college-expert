import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useAuth } from './AuthContext';
import { getUserPurchases } from '../services/paymentService';
import { getUserCredits } from '../services/api';

const PaymentContext = createContext();

// =============================================================================
// TIER DEFINITIONS
// =============================================================================
export const TIERS = {
    FREE: 'free',
    PRO: 'pro',
    ELITE: 'elite'
};

// Tier feature limits
const TIER_FEATURES = {
    [TIERS.FREE]: {
        aiMessagesLimit: 10,           // 10 messages per month
        canAccessLaunchpad: false,     // No launchpad access
        canAnalyzeFit: false,          // No fit analysis
        hasFullFitAnalysis: false,     // N/A
        canDeepResearch: false,        // No deep research
        price: 0,
        label: 'Free'
    },
    [TIERS.PRO]: {
        aiMessagesLimit: 30,           // 30 messages per month
        canAccessLaunchpad: true,      // Full launchpad access
        canAnalyzeFit: true,           // Basic fit analysis
        hasFullFitAnalysis: false,     // No recommendations/advanced features
        canDeepResearch: false,        // No deep research
        price: 99,
        label: 'Pro'
    },
    [TIERS.ELITE]: {
        aiMessagesLimit: 50,           // 50 messages per month
        canAccessLaunchpad: true,      // Full launchpad access
        canAnalyzeFit: true,           // Full fit analysis
        hasFullFitAnalysis: true,      // Includes recommendations, essay angles, etc.
        canDeepResearch: true,         // Full deep research
        price: 199,
        label: 'Elite'
    }
};

// Helper to get current month key for localStorage
const getMonthKey = () => {
    const now = new Date();
    return `${now.getFullYear()}-${now.getMonth() + 1}`;
};

export const usePayment = () => {
    const context = useContext(PaymentContext);
    if (!context) {
        throw new Error('usePayment must be used within a PaymentProvider');
    }
    return context;
};

export const PaymentProvider = ({ children }) => {
    const { currentUser } = useAuth();
    const [purchases, setPurchases] = useState(null);
    const [loading, setLoading] = useState(true);
    const [showUpgradeModal, setShowUpgradeModal] = useState(false);
    const [upgradeReason, setUpgradeReason] = useState('');
    const [upgradeFeature, setUpgradeFeature] = useState('');

    // Credits state
    const [credits, setCredits] = useState({
        tier: 'free',
        credits_remaining: 3,
        credits_total: 3,
        credits_used: 0,
        subscription_active: false
    });
    const [creditsLoading, setCreditsLoading] = useState(true);
    const [showCreditsModal, setShowCreditsModal] = useState(false);
    const [creditsModalFeature, setCreditsModalFeature] = useState('fit analysis');

    // Monthly message tracking with localStorage (for free tier)
    const [monthlyMessagesUsed, setMonthlyMessagesUsed] = useState(() => {
        try {
            const stored = localStorage.getItem('monthlyMessagesUsed');
            if (stored) {
                const data = JSON.parse(stored);
                if (data.month === getMonthKey()) {
                    return data.count;
                }
            }
            return 0;
        } catch {
            return 0;
        }
    });

    // Save monthly messages to localStorage when it changes
    useEffect(() => {
        localStorage.setItem('monthlyMessagesUsed', JSON.stringify({
            month: getMonthKey(),
            count: monthlyMessagesUsed
        }));
    }, [monthlyMessagesUsed]);

    // Fetch purchases and credits on user change
    useEffect(() => {
        if (currentUser?.email) {
            fetchPurchases();
            fetchCredits();
        } else {
            setPurchases(null);
            setCredits({ tier: 'free', credits_remaining: 3, credits_total: 3, credits_used: 0 });
            setLoading(false);
            setCreditsLoading(false);
        }
    }, [currentUser?.email]);

    const fetchPurchases = useCallback(async () => {
        if (!currentUser?.email) return;

        setLoading(true);
        try {
            const result = await getUserPurchases(currentUser.email);
            if (result.success) {
                setPurchases(result.purchases);
            }
        } catch (error) {
            console.error('Error fetching purchases:', error);
        } finally {
            setLoading(false);
        }
    }, [currentUser?.email]);

    const fetchCredits = useCallback(async () => {
        if (!currentUser?.email) return;

        setCreditsLoading(true);
        try {
            const result = await getUserCredits(currentUser.email);
            if (result.success && result.credits) {
                setCredits(result.credits);
            }
        } catch (error) {
            console.error('Error fetching credits:', error);
        } finally {
            setCreditsLoading(false);
        }
    }, [currentUser?.email]);

    // =============================================================================
    // DETERMINE USER'S TIER
    // =============================================================================
    const getUserTier = useCallback(() => {
        if (!purchases?.subscription_active) {
            return TIERS.FREE;
        }
        // Check subscription plan from backend
        const plan = purchases?.subscription_plan?.toLowerCase() || '';
        if (plan.includes('elite')) {
            return TIERS.ELITE;
        }
        if (plan.includes('pro')) {
            return TIERS.PRO;
        }
        // Default to PRO if has active subscription but unclear plan
        return TIERS.PRO;
    }, [purchases]);

    const currentTier = getUserTier();
    const tierFeatures = TIER_FEATURES[currentTier];

    // =============================================================================
    // FEATURE ACCESS HELPERS
    // =============================================================================

    // Can access Launchpad?
    const canAccessLaunchpad = tierFeatures.canAccessLaunchpad;

    // Can analyze fit?
    const canAnalyzeFit = tierFeatures.canAnalyzeFit;

    // Has full fit analysis (with recommendations)?
    const hasFullFitAnalysis = tierFeatures.hasFullFitAnalysis;

    // Can do deep research?
    const canDeepResearch = tierFeatures.canDeepResearch;

    // =============================================================================
    // AI MESSAGE TRACKING
    // =============================================================================
    const aiMessagesLimit = tierFeatures.aiMessagesLimit;
    const aiMessagesUsed = currentTier === TIERS.FREE ? monthlyMessagesUsed : 0;
    const aiMessagesAvailable = aiMessagesLimit === 'unlimited'
        ? 'unlimited'
        : Math.max(0, aiMessagesLimit - aiMessagesUsed);

    // =============================================================================
    // UPGRADE PROMPT
    // =============================================================================
    const promptUpgrade = useCallback((feature, reason) => {
        setUpgradeFeature(feature);
        setUpgradeReason(reason);
        setShowUpgradeModal(true);
    }, []);

    const closeUpgradeModal = useCallback(() => {
        setShowUpgradeModal(false);
        setUpgradeReason('');
        setUpgradeFeature('');
    }, []);

    // Consume an AI message
    const consumeAiMessage = useCallback(() => {
        if (aiMessagesAvailable <= 0) {
            promptUpgrade('ai_messages', 'You\'ve used all your monthly messages. Upgrade for more!');
            return false;
        }

        setMonthlyMessagesUsed(prev => prev + 1);
        return true;
    }, [aiMessagesAvailable, promptUpgrade]);

    // =============================================================================
    // CONTEXT VALUE
    // =============================================================================

    // Derived credits values
    const creditsRemaining = credits?.credits_remaining ?? 0;
    const creditsTier = credits?.tier ?? 'free';
    const hasCredits = creditsRemaining > 0;
    const canRunFitAnalysis = hasCredits;

    const value = {
        // State
        purchases,
        loading,
        showUpgradeModal,
        upgradeReason,
        upgradeFeature,

        // Current Tier
        currentTier,
        tierLabel: tierFeatures.label,

        // Tier checks
        isFreeTier: currentTier === TIERS.FREE,
        isPro: currentTier === TIERS.PRO || creditsTier === 'pro',
        isElite: currentTier === TIERS.ELITE,
        hasActiveSubscription: currentTier !== TIERS.FREE,

        // Feature access
        canAccessLaunchpad,
        canAnalyzeFit,
        hasFullFitAnalysis,
        canDeepResearch,

        // AI Messages
        aiMessagesLimit,
        aiMessagesUsed,
        aiMessagesAvailable,

        // Credits
        credits,
        creditsRemaining,
        creditsTier,
        creditsLoading,
        hasCredits,
        canRunFitAnalysis,
        fetchCredits,

        // Credits Modal
        showCreditsModal,
        creditsModalFeature,
        promptCreditsUpgrade: (feature = 'fit analysis') => {
            setCreditsModalFeature(feature);
            setShowCreditsModal(true);
        },
        closeCreditsModal: () => setShowCreditsModal(false),

        // Actions
        fetchPurchases,
        consumeAiMessage,
        promptUpgrade,
        closeUpgradeModal,

        // Tier definitions (for pricing page)
        TIERS,
        TIER_FEATURES,
    };

    return (
        <PaymentContext.Provider value={value}>
            {children}
        </PaymentContext.Provider>
    );
};

export default PaymentContext;
