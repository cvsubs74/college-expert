import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useAuth } from './AuthContext';
import { getUserPurchases, checkAccess, useCredit } from '../services/paymentService';

const PaymentContext = createContext();

// Constants for free tier
const FREE_AI_MESSAGES_LIMIT = 30;  // Per month
const FREE_FIT_ANALYSIS_CREDITS = 3;  // Total forever

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

    // Monthly message tracking with localStorage
    const [monthlyMessagesUsed, setMonthlyMessagesUsed] = useState(() => {
        try {
            const stored = localStorage.getItem('monthlyMessagesUsed');
            if (stored) {
                const data = JSON.parse(stored);
                // Check if it's from this month
                if (data.month === getMonthKey()) {
                    return data.count;
                }
            }
            return 0;
        } catch {
            return 0;
        }
    });

    // Fit analysis tracking with localStorage (persists forever)
    const [fitAnalysesUsed, setFitAnalysesUsed] = useState(() => {
        try {
            const stored = localStorage.getItem('fitAnalysesUsed');
            return stored ? JSON.parse(stored) : [];
        } catch {
            return [];
        }
    });

    // Save monthly messages to localStorage when it changes
    useEffect(() => {
        localStorage.setItem('monthlyMessagesUsed', JSON.stringify({
            month: getMonthKey(),
            count: monthlyMessagesUsed
        }));
    }, [monthlyMessagesUsed]);

    // Save fit analyses to localStorage when it changes
    useEffect(() => {
        localStorage.setItem('fitAnalysesUsed', JSON.stringify(fitAnalysesUsed));
    }, [fitAnalysesUsed]);

    // Fetch purchases on user change
    useEffect(() => {
        if (currentUser?.email) {
            fetchPurchases();
        } else {
            setPurchases(null);
            setLoading(false);
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

    // Check if user has an active subscription
    const hasActiveSubscription = purchases?.subscription_active || false;

    // Calculate AI messages available
    const aiMessagesLimit = hasActiveSubscription
        ? (purchases?.ai_messages_limit || 100)
        : FREE_AI_MESSAGES_LIMIT;
    const aiMessagesUsed = hasActiveSubscription
        ? (purchases?.ai_messages_used || 0)
        : monthlyMessagesUsed;
    const aiMessagesAvailable = Math.max(0, aiMessagesLimit - aiMessagesUsed);

    // Calculate fit analysis credits
    const fitAnalysisCredits = hasActiveSubscription
        ? (purchases?.fit_analysis_credits || 3) + (purchases?.college_slots_purchased || 0)
        : FREE_FIT_ANALYSIS_CREDITS;
    const fitAnalysisUsed = hasActiveSubscription
        ? (purchases?.fit_analysis_used || 0)
        : fitAnalysesUsed.length;
    const fitAnalysisAvailable = Math.max(0, fitAnalysisCredits - fitAnalysisUsed);

    // Analyze a college (consume fit credit)
    const canAnalyzeCollege = useCallback((collegeId) => {
        // If already analyzed, can view for free
        if (hasActiveSubscription) {
            const analyzed = purchases?.analyzed_colleges || [];
            if (analyzed.includes(collegeId)) return true;
        } else {
            if (fitAnalysesUsed.includes(collegeId)) return true;
        }

        // Check if credits available
        return fitAnalysisAvailable > 0;
    }, [hasActiveSubscription, purchases, fitAnalysesUsed, fitAnalysisAvailable]);

    const consumeFitAnalysis = useCallback((collegeId) => {
        // Check if already analyzed
        if (hasActiveSubscription) {
            const analyzed = purchases?.analyzed_colleges || [];
            if (analyzed.includes(collegeId)) return true;
        } else {
            if (fitAnalysesUsed.includes(collegeId)) return true;
        }

        // Check credits
        if (fitAnalysisAvailable <= 0) {
            promptUpgrade('fit_analysis', 'You\'ve used all your fit analysis credits');
            return false;
        }

        // Consume credit
        if (!hasActiveSubscription) {
            setFitAnalysesUsed(prev => [...prev, collegeId]);
        }
        // For subscribed users, the backend tracks this

        return true;
    }, [hasActiveSubscription, purchases, fitAnalysesUsed, fitAnalysisAvailable]);

    // Consume an AI message
    const consumeAiMessage = useCallback(() => {
        if (aiMessagesAvailable <= 0) {
            promptUpgrade('ai_messages', 'You\'ve used all your monthly messages');
            return false;
        }

        if (!hasActiveSubscription) {
            setMonthlyMessagesUsed(prev => prev + 1);
        }
        // For subscribed users, backend tracks this

        return true;
    }, [aiMessagesAvailable, hasActiveSubscription]);

    // Show upgrade modal with reason
    const promptUpgrade = useCallback((feature, reason) => {
        setUpgradeFeature(feature);
        setUpgradeReason(reason);
        setShowUpgradeModal(true);
    }, []);

    // Close upgrade modal
    const closeUpgradeModal = useCallback(() => {
        setShowUpgradeModal(false);
        setUpgradeReason('');
        setUpgradeFeature('');
    }, []);

    const value = {
        // State
        purchases,
        loading,
        showUpgradeModal,
        upgradeReason,
        upgradeFeature,

        // Subscription status
        hasActiveSubscription,
        subscriptionPlan: purchases?.subscription_plan || null,

        // AI Messages
        aiMessagesLimit,
        aiMessagesUsed,
        aiMessagesAvailable,

        // Fit Analysis
        fitAnalysisCredits,
        fitAnalysisUsed,
        fitAnalysisAvailable,
        analyzedColleges: hasActiveSubscription
            ? (purchases?.analyzed_colleges || [])
            : fitAnalysesUsed,

        // Computed
        isFreeTier: !hasActiveSubscription,
        isPro: hasActiveSubscription,

        // Actions
        fetchPurchases,
        consumeAiMessage,
        canAnalyzeCollege,
        consumeFitAnalysis,
        promptUpgrade,
        closeUpgradeModal,
    };

    return (
        <PaymentContext.Provider value={value}>
            {children}
        </PaymentContext.Provider>
    );
};

export default PaymentContext;
