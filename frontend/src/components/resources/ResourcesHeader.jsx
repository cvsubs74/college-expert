import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
    BookOpenIcon,
    SparklesIcon,
    ArrowRightOnRectangleIcon,
} from '@heroicons/react/24/outline';
import { useAuth } from '../../context/AuthContext';

// Sticky header used on /resources and /resources/<slug>.
//
// Shapes itself to auth state:
//   - Logged in:  Logo · Roadmap · Resources · [user name] · Sign Out
//   - Logged out: Logo · Resources · [Go to app] CTA
//
// Matches the visual conventions of the existing PricingPage / ContactPage
// headers (Stratia palette, rounded-full pills, sticky w/ backdrop blur).

const ResourcesHeader = () => {
    const location = useLocation();
    const { currentUser } = useAuth();
    const isResources = location.pathname.startsWith('/resources');

    return (
        <header className="bg-[#FDFCF7]/95 backdrop-blur-sm border-b border-[#E0DED8] sticky top-0 z-40">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex justify-between items-center h-20">
                    {/* Left: logo + nav */}
                    <div className="flex items-center gap-2 sm:gap-6">
                        <Link to="/" className="flex items-center flex-shrink-0">
                            <img
                                src="/logo.png"
                                alt="Stratia Admissions"
                                className="h-14 sm:h-16 w-auto object-contain mix-blend-multiply"
                            />
                        </Link>

                        <nav className="hidden sm:flex items-center gap-1">
                            {currentUser && (
                                <Link
                                    to="/roadmap"
                                    className="px-3 py-2 rounded-full text-sm font-medium text-[#4A4A4A] hover:bg-[#F8F6F0] hover:text-[#1A4D2E] transition-all flex items-center gap-2"
                                >
                                    <SparklesIcon className="h-4 w-4" />
                                    Roadmap
                                </Link>
                            )}
                            <Link
                                to="/resources"
                                className={`px-3 py-2 rounded-full text-sm font-medium transition-all flex items-center gap-2 ${
                                    isResources
                                        ? 'bg-[#D6E8D5] text-[#1A4D2E]'
                                        : 'text-[#4A4A4A] hover:bg-[#F8F6F0] hover:text-[#1A4D2E]'
                                }`}
                            >
                                <BookOpenIcon className="h-4 w-4" />
                                Resources
                            </Link>
                        </nav>
                    </div>

                    {/* Right: auth-state-dependent */}
                    <div className="flex items-center gap-2 sm:gap-3">
                        {currentUser ? (
                            <>
                                <span className="hidden md:inline text-sm text-[#4A4A4A] font-medium">
                                    {currentUser.displayName || currentUser.email}
                                </span>
                                <Link
                                    to="/roadmap"
                                    className="hidden sm:inline-flex items-center px-4 py-2 bg-[#1A4D2E] text-white text-sm font-medium rounded-full hover:bg-[#2D6B45] transition-all shadow-md"
                                >
                                    Open app
                                </Link>
                            </>
                        ) : (
                            <>
                                <Link
                                    to="/"
                                    className="hidden sm:inline-flex items-center px-3 py-2 text-sm font-medium text-[#4A4A4A] hover:text-[#1A4D2E] transition-colors"
                                >
                                    Sign in
                                    <ArrowRightOnRectangleIcon className="h-4 w-4 ml-1" />
                                </Link>
                                <Link
                                    to="/"
                                    className="inline-flex items-center px-4 py-2 bg-[#1A4D2E] text-white text-sm font-medium rounded-full hover:bg-[#2D6B45] transition-all shadow-md"
                                >
                                    Try Stratia
                                </Link>
                            </>
                        )}
                    </div>
                </div>
            </div>
        </header>
    );
};

export default ResourcesHeader;
