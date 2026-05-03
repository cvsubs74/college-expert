import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { BookOpenIcon, KeyIcon } from '@heroicons/react/24/outline';
import { useAuth } from '../context/AuthContext';
import { signInWithGoogle } from '../services/authService';

// Compact marketing-style header used by every public route the
// prospective-user funnel touches (LandingPage and the public Resources
// pages). The visual layout — fixed top, gradient book-and-key logo,
// pill-style nav links, dark green CTA — is the brand for the marketing
// surface; flipping between Landing and Resources with the same chrome
// makes the transition feel continuous instead of "you've left the
// website."
//
// Auth-aware on the right: logged-out visitors see "Get Started" (kicks
// off the Google sign-in popup); signed-in visitors see "Open App"
// (deep-links into the launchpad).
//
// `rightSlot` lets a host page inject an extra element between the nav
// links and the CTA — Pricing uses it for the credits chip when the user
// is signed in. Optional; everything works without it.
//
// The signed-in shell of the actual app is the heavier `Navigation`
// component — that one's used inside `AppLayout` and on Resources pages
// for signed-in users. This header is specifically for the
// brochure-side experience.

const MarketingHeader = ({ rightSlot = null }) => {
    const { currentUser } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();

    const isActive = (path) =>
        path === '/resources'
            ? location.pathname.startsWith('/resources')
            : location.pathname === path;

    const handleSignIn = async () => {
        try {
            await signInWithGoogle();
            navigate('/universities');
        } catch (error) {
            console.error('Sign in failed:', error);
        }
    };

    const handleGetStarted = () => {
        if (currentUser) {
            navigate('/universities');
        } else {
            handleSignIn();
        }
    };

    return (
        <header className="fixed top-0 left-0 right-0 z-50 bg-[#FDFCF7]/80 backdrop-blur-lg border-b border-[#E0DED8]/50">
            <div className="max-w-7xl mx-auto px-6 lg:px-8">
                <div className="flex items-center justify-between h-16">
                    <Link to="/" className="flex items-center gap-2 group">
                        {/* Book & Key Logo — matches app brand */}
                        <div className="relative w-10 h-10 flex items-center justify-center rounded-xl bg-gradient-to-br from-[#1A4D2E] to-[#2D6B45] shadow-md group-hover:shadow-lg transition-shadow">
                            <BookOpenIcon
                                className="w-5 h-5 text-white absolute"
                                style={{ top: '8px', left: '8px' }}
                            />
                            <KeyIcon
                                className="w-4 h-4 text-[#D6E8D5] absolute"
                                style={{ bottom: '6px', right: '6px' }}
                            />
                        </div>

                        {/* Brand text */}
                        <div className="flex items-baseline gap-1">
                            <span className="font-serif text-xl font-semibold text-[#1A4D2E]">
                                Stratia
                            </span>
                            <span className="font-sans text-sm font-medium text-[#4A4A4A]">
                                Admissions
                            </span>
                        </div>
                    </Link>

                    <nav className="hidden md:flex items-center gap-8">
                        <Link
                            to="/resources"
                            className={`text-sm font-medium transition-colors ${
                                isActive('/resources')
                                    ? 'text-[#1A4D2E]'
                                    : 'text-[#4A4A4A] hover:text-[#1A4D2E]'
                            }`}
                        >
                            Resources
                        </Link>
                        <Link
                            to="/pricing"
                            className={`text-sm font-medium transition-colors ${
                                isActive('/pricing')
                                    ? 'text-[#1A4D2E]'
                                    : 'text-[#4A4A4A] hover:text-[#1A4D2E]'
                            }`}
                        >
                            Pricing
                        </Link>
                        {rightSlot}
                        {currentUser ? (
                            <Link
                                to="/launchpad"
                                className="px-4 py-2 bg-[#1A4D2E] text-white text-sm font-medium rounded-lg hover:bg-[#2D6B45] transition-all"
                            >
                                Open App
                            </Link>
                        ) : (
                            <button
                                onClick={handleSignIn}
                                className="px-4 py-2 bg-[#1A4D2E] text-white text-sm font-medium rounded-lg hover:bg-[#2D6B45] transition-all"
                            >
                                Get Started
                            </button>
                        )}
                    </nav>

                    {/* Mobile fallback CTA */}
                    <button
                        onClick={handleGetStarted}
                        className="md:hidden px-4 py-2 bg-[#1A4D2E] text-white text-sm font-medium rounded-lg"
                    >
                        Start
                    </button>
                </div>
            </div>
        </header>
    );
};

export default MarketingHeader;
