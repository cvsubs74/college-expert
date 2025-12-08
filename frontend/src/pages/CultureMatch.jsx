import React, { useState } from 'react';
import { SparklesIcon, UserGroupIcon, ArrowRightIcon } from '@heroicons/react/24/outline';
import VideoUploader from '../components/CultureMatch/VideoUploader';
import { Link } from 'react-router-dom';

export default function CultureMatch() {
    const [analyzing, setAnalyzing] = useState(false);
    const [result, setResult] = useState(null);

    const handleUpload = async (file) => {
        setAnalyzing(true);
        // Simulate multimodal analysis duration
        setTimeout(() => {
            setResult({
                vibe: "Creative Maker & Social Butterfly",
                analysis: "Your energy is high and collaborative. You mentioned robotics and debate, suggesting you thrive in environments that mix technical rigor with vocal advocacy. You seem to value community over pure competition.",
                matches: [
                    { id: 'university_of_california_berkeley', name: 'UC Berkeley', badge: 'Activist Spirit', reason: 'Matches your debate background and high-energy social scene.' },
                    { id: 'university_of_michigan', name: 'University of Michigan', badge: 'Work Hard Play Hard', reason: 'Perfect fit for your balance of intense academics and social engagement.' },
                    { id: 'university_of_texas_austin', name: 'UT Austin', badge: 'Creative Innovator', reason: 'Your maker energy aligns with the vibrant Austin tech scene.' }
                ]
            });
            setAnalyzing(false);
        }, 3000);
    };

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            {/* Header */}
            <div className="text-center mb-12">
                <h1 className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-purple-600 to-blue-500 mb-4">
                    Find Your Tribe
                </h1>
                <p className="text-xl text-gray-600 max-w-2xl mx-auto">
                    Don't just pick a ranking. Pick a home. Upload a short video intro and let our AI analyze your vibe to find the campuses where you'll truly belong.
                </p>
            </div>

            {!result && !analyzing && (
                <div className="max-w-xl mx-auto">
                    <VideoUploader onUpload={handleUpload} processing={analyzing} />
                </div>
            )}

            {analyzing && (
                <div className="text-center py-20">
                    <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-purple-600 mx-auto mb-6"></div>
                    <h2 className="text-2xl font-semibold text-gray-900">Analyzing your vibe...</h2>
                    <p className="text-gray-500 mt-2">Extracting personality traits, tone, and interests from video frames...</p>
                </div>
            )}

            {result && (
                <div className="animate-fade-in">
                    <div className="bg-white rounded-2xl shadow-xl p-8 mb-12 border border-purple-100">
                        <div className="flex items-center gap-4 mb-6">
                            <div className="p-3 bg-purple-100 rounded-full text-purple-600">
                                <SparklesIcon className="w-8 h-8" />
                            </div>
                            <div>
                                <h2 className="text-2xl font-bold text-gray-900">Your Vibe: {result.vibe}</h2>
                            </div>
                        </div>
                        <p className="text-lg text-gray-700 leading-relaxed">{result.analysis}</p>
                    </div>

                    <h3 className="text-2xl font-bold text-gray-900 mb-6 flex items-center gap-2">
                        <UserGroupIcon className="w-7 h-7 text-blue-600" />
                        Best Cultural Fits
                    </h3>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        {result.matches.map((uni) => (
                            <div key={uni.id} className="bg-white rounded-xl shadow-md overflow-hidden hover:shadow-lg transition-shadow border border-gray-100">
                                <div className="h-2 bg-gradient-to-r from-blue-400 to-purple-500"></div>
                                <div className="p-6">
                                    <h4 className="text-xl font-bold text-gray-900 mb-2">{uni.name}</h4>
                                    <span className="inline-block px-3 py-1 bg-purple-50 text-purple-700 rounded-full text-sm font-medium mb-4">
                                        {uni.badge}
                                    </span>
                                    <p className="text-gray-600 mb-4">{uni.reason}</p>
                                    <Link
                                        to="/universities"
                                        className="text-blue-600 font-medium hover:text-blue-800 flex items-center gap-1"
                                    >
                                        Explore in Universe <ArrowRightIcon className="w-4 h-4" />
                                    </Link>
                                </div>
                            </div>
                        ))}
                    </div>

                    <button
                        onClick={() => setResult(null)}
                        className="mt-12 mx-auto block px-6 py-2 text-gray-500 hover:text-gray-900 transition-colors"
                    >
                        Try Another Video
                    </button>
                </div>
            )}
        </div>
    );
}
