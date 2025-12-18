import React from 'react';
import { Link } from 'react-router-dom';
import { LockClosedIcon, SparklesIcon, RocketLaunchIcon, ChartBarIcon, StarIcon } from '@heroicons/react/24/outline';

/**
 * UpgradePrompt - Shows when user hits tier limits
 * Can be used inline in any component
 */
const UpgradePrompt = ({
    feature,
    message = "Upgrade to unlock this feature",
    compact = false
}) => {
    const featureMessages = {
        launchpad: {
            title: "Unlock Your Launchpad",
            desc: "Build your personalized college list with AI-powered fit analysis",
            cta: "Upgrade to Pro — $99/year",
            icon: RocketLaunchIcon,
            tier: 'pro'
        },
        fit_analysis: {
            title: "Unlock Fit Analysis",
            desc: "Get admission probability and personalized fit scores for each college",
            cta: "Upgrade to Pro — $99/year",
            icon: ChartBarIcon,
            tier: 'pro'
        },
        recommendations: {
            title: "Unlock Full Analysis",
            desc: "Get personalized recommendations, essay angles, and scholarship matching",
            cta: "Upgrade to Elite — $199/year",
            icon: StarIcon,
            tier: 'elite'
        },
        deep_research: {
            title: "Unlock Deep Research",
            desc: "Access AI-powered deep research with university insights and strategic angles",
            cta: "Upgrade to Elite — $199/year",
            icon: StarIcon,
            tier: 'elite'
        },
        ai_messages: {
            title: "Get More AI Messages",
            desc: "You've used your 10 free messages this month. Upgrade for unlimited access!",
            cta: "Upgrade to Pro — $99/year",
            icon: SparklesIcon,
            tier: 'pro'
        },
        default: {
            title: "Upgrade Required",
            desc: message,
            cta: "View Pricing",
            icon: LockClosedIcon,
            tier: null
        }
    };

    const content = featureMessages[feature] || featureMessages.default;
    const IconComponent = content.icon || LockClosedIcon;

    if (compact) {
        return (
            <div className="inline-flex items-center gap-2 px-3 py-2 bg-amber-50 border border-amber-200 rounded-xl">
                <LockClosedIcon className="h-4 w-4 text-amber-600" />
                <span className="text-sm text-amber-800">{content.desc}</span>
                <Link
                    to="/pricing"
                    className="text-sm font-bold text-amber-600 hover:text-amber-700 underline"
                >
                    Upgrade
                </Link>
            </div>
        );
    }

    return (
        <div className="bg-gradient-to-br from-amber-50 to-orange-50 border border-amber-200 rounded-2xl p-6 text-center">
            <div className={`w-12 h-12 mx-auto rounded-xl flex items-center justify-center mb-4 ${content.tier === 'elite'
                    ? 'bg-gradient-to-br from-purple-400 to-indigo-500'
                    : 'bg-gradient-to-br from-amber-400 to-orange-500'
                }`}>
                <IconComponent className="h-6 w-6 text-white" />
            </div>
            <h3 className="text-lg font-bold text-gray-900 mb-2">{content.title}</h3>
            <p className="text-gray-600 mb-4">{content.desc}</p>
            <Link
                to="/pricing"
                className={`inline-flex items-center px-6 py-3 text-white font-bold rounded-xl transition-all shadow-lg ${content.tier === 'elite'
                        ? 'bg-gradient-to-r from-purple-500 to-indigo-600 hover:from-purple-400 hover:to-indigo-500 shadow-purple-200'
                        : 'bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 shadow-amber-200'
                    }`}
            >
                <SparklesIcon className="h-5 w-5 mr-2" />
                {content.cta}
            </Link>
        </div>
    );
};

export default UpgradePrompt;
