import React from 'react';
import { Link } from 'react-router-dom';
import { LockClosedIcon, SparklesIcon } from '@heroicons/react/24/outline';

/**
 * UpgradePrompt - Shows when user hits free tier limits
 * Can be used inline in any component
 */
const UpgradePrompt = ({
    feature,
    message = "Upgrade to unlock this feature",
    compact = false
}) => {
    const featureMessages = {
        explorer: {
            title: "Unlock Full University Database",
            desc: "Get access to all 150+ universities with the Explorer Pass",
            cta: "Get Explorer Pass - $29"
        },
        colleges: {
            title: "Add More Colleges",
            desc: "You've used all your college slots. Add more to your list.",
            cta: "Get More Colleges"
        },
        fit_analysis: {
            title: "Unlock Fit Analysis",
            desc: "Get detailed admission probability and personalized recommendations",
            cta: "Get Fit Analysis - $19"
        },
        ai_messages: {
            title: "Get More AI Messages",
            desc: "Continue your conversation with our AI counselor",
            cta: "Get 50 Messages - $9"
        },
        default: {
            title: "Upgrade Required",
            desc: message,
            cta: "View Pricing"
        }
    };

    const content = featureMessages[feature] || featureMessages.default;

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
            <div className="w-12 h-12 mx-auto bg-gradient-to-br from-amber-400 to-orange-500 rounded-xl flex items-center justify-center mb-4">
                <LockClosedIcon className="h-6 w-6 text-white" />
            </div>
            <h3 className="text-lg font-bold text-gray-900 mb-2">{content.title}</h3>
            <p className="text-gray-600 mb-4">{content.desc}</p>
            <Link
                to="/pricing"
                className="inline-flex items-center px-6 py-3 bg-gradient-to-r from-amber-500 to-orange-500 text-white font-bold rounded-xl hover:from-amber-400 hover:to-orange-400 transition-all shadow-lg shadow-amber-200"
            >
                <SparklesIcon className="h-5 w-5 mr-2" />
                {content.cta}
            </Link>
        </div>
    );
};

export default UpgradePrompt;
