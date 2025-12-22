import React from 'react';
import { SparklesIcon } from '@heroicons/react/24/outline';

const LoadingModal = ({ isOpen, message, title = "Analyzing Fit", subMessage }) => {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
            <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full text-center transform transition-all">
                <div className="flex justify-center mb-6">
                    <div className="relative">
                        {/* Animated rings */}
                        <div className="absolute inset-0 border-4 border-amber-200 rounded-full animate-ping opacity-25"></div>
                        <div className="absolute inset-0 border-4 border-orange-100 rounded-full animate-pulse"></div>

                        {/* Spinner */}
                        <div className="w-16 h-16 border-4 border-amber-100 border-t-amber-500 rounded-full animate-spin relative z-10"></div>

                        {/* Center Icon */}
                        <div className="absolute inset-0 flex items-center justify-center z-10">
                            <SparklesIcon className="w-6 h-6 text-amber-500 animate-pulse" />
                        </div>
                    </div>
                </div>

                <h3 className="text-xl font-bold text-gray-900 mb-2">{title}</h3>
                <p className="text-gray-600 font-medium mb-4">{message}</p>
                {subMessage && (
                    <p className="text-sm text-gray-400 animate-pulse">{subMessage}</p>
                )}
            </div>
        </div>
    );
};

export default LoadingModal;
