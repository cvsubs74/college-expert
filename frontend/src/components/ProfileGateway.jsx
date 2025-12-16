import React from 'react';
import {
    CloudArrowUpIcon,
    ChatBubbleBottomCenterTextIcon,
    PencilSquareIcon,
    SparklesIcon
} from '@heroicons/react/24/outline'; // Using outline icons for a clean look

const ProfileGateway = ({ onSelectMethod }) => {
    return (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 max-w-5xl mx-auto my-8">
            <div className="text-center mb-10">
                <h2 className="text-3xl font-bold text-gray-900 mb-3">
                    Let's Build Your Academic Story
                </h2>
                <p className="text-lg text-gray-500 max-w-2xl mx-auto">
                    Your profile helps our AI find the perfect college matches for you.
                    Choose how you'd like to tell us about your achievements.
                </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Option 1: Upload (The Parser) */}
                <button
                    onClick={() => onSelectMethod('upload')}
                    className="group relative flex flex-col items-center p-8 bg-blue-50 border-2 border-blue-100 rounded-xl hover:border-blue-500 hover:shadow-lg transition-all duration-300 text-left"
                >
                    <div className="absolute top-4 right-4 bg-blue-100 text-blue-700 text-xs font-semibold px-2 py-1 rounded-full">
                        Quickest
                    </div>
                    <div className="h-16 w-16 bg-blue-100 rounded-full flex items-center justify-center mb-6 text-blue-600 group-hover:scale-110 transition-transform">
                        <CloudArrowUpIcon className="h-8 w-8" />
                    </div>
                    <h3 className="text-xl font-semibold text-gray-900 mb-2">Upload Transcript</h3>
                    <p className="text-gray-600 text-center text-sm leading-relaxed">
                        Have your transcript or resume ready? Upload it now and our AI will instantly extract your grades and courses.
                    </p>
                </button>

                {/* Option 2: Interview (The Assessment) */}
                <button
                    onClick={() => onSelectMethod('chat')}
                    className="group relative flex flex-col items-center p-8 bg-purple-50 border-2 border-purple-100 rounded-xl hover:border-purple-500 hover:shadow-lg transition-all duration-300 text-left"
                >
                    <div className="absolute top-4 right-4 bg-purple-100 text-purple-700 text-xs font-semibold px-2 py-1 rounded-full flex items-center gap-1">
                        <SparklesIcon className="h-3 w-3" /> Guided
                    </div>
                    <div className="h-16 w-16 bg-purple-100 rounded-full flex items-center justify-center mb-6 text-purple-600 group-hover:scale-110 transition-transform">
                        <ChatBubbleBottomCenterTextIcon className="h-8 w-8" />
                    </div>
                    <h3 className="text-xl font-semibold text-gray-900 mb-2">Chat with Counselor</h3>
                    <p className="text-gray-600 text-center text-sm leading-relaxed">
                        Prefer a conversation? Our AI counselor will interview you step-by-step to uncover your hidden strengths.
                    </p>
                </button>

                {/* Option 3: Form (Direct Entry) */}
                <button
                    onClick={() => onSelectMethod('form')}
                    className="group relative flex flex-col items-center p-8 bg-teal-50 border-2 border-teal-100 rounded-xl hover:border-teal-500 hover:shadow-lg transition-all duration-300 text-left"
                >
                    <div className="absolute top-4 right-4 bg-teal-100 text-teal-700 text-xs font-semibold px-2 py-1 rounded-full">
                        Most Thorough
                    </div>
                    <div className="h-16 w-16 bg-teal-100 rounded-full flex items-center justify-center mb-6 text-teal-600 group-hover:scale-110 transition-transform">
                        <PencilSquareIcon className="h-8 w-8" />
                    </div>
                    <h3 className="text-xl font-semibold text-gray-900 mb-2">Fill Out Form</h3>
                    <p className="text-gray-600 text-center text-sm leading-relaxed">
                        Want full control? Manually enter your grades, activities, and awards in our structured editor.
                    </p>
                </button>
            </div>
        </div>
    );
};

export default ProfileGateway;
