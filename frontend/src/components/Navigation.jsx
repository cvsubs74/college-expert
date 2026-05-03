import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
    DocumentTextIcon,
    BookOpenIcon,
    BuildingLibraryIcon,
    SparklesIcon,
    RocketLaunchIcon,
    StarIcon,
    ArrowRightOnRectangleIcon,
} from '@heroicons/react/24/outline';
import { useAuth } from '../context/AuthContext';
import { logout } from '../services/authService';

// Single Navigation component used by:
//   1. AppLayout (protected pages — Profile/Discover/Launchpad/Roadmap/Resources)
//   2. ResourcesPage and ResourcePaperPage (public pages — Resources alone for
//      logged-out visitors, full nav for signed-in users)
//
// Auth-aware: links with `requiresAuth: true` are hidden when there is no
// `currentUser`. The right-side action area also adapts — signed-in users
// see Sign Out + Upgrade; logged-out visitors see Sign in + Try Stratia.
//
// Extracted from App.jsx so the public Resources routes share the exact same
// visual treatment as the in-app pages — no second header to maintain.

const NAV_LINKS = [
    { path: '/profile', label: 'Profile', icon: DocumentTextIcon, requiresAuth: true },
    { path: '/universities', label: 'Discover', icon: BuildingLibraryIcon, requiresAuth: true },
    { path: '/launchpad', label: 'Launchpad', icon: RocketLaunchIcon, requiresAuth: true },
    { path: '/roadmap', label: 'Roadmap', icon: SparklesIcon, requiresAuth: true },
    { path: '/resources', label: 'Resources', icon: BookOpenIcon, requiresAuth: false },
];

const Navigation = () => {
    const location = useLocation();
    const { currentUser } = useAuth();

    const isActive = (path) =>
        path === '/resources'
            ? location.pathname.startsWith('/resources')
            : location.pathname === path;

    const handleLogout = async () => {
        try {
            await logout();
        } catch (error) {
            console.error('Failed to log out', error);
        }
    };

    // Filter links by auth state. When logged out, only public links remain
    // (today: just Resources). When logged in, every link is visible.
    const visibleLinks = NAV_LINKS.filter((l) => !l.requiresAuth || currentUser);

    return (
        <nav className="bg-[#FDFCF7]/95 backdrop-blur-sm border-b border-[#E0DED8] sticky top-0 z-50">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex justify-between items-center h-36">
                    {/* Logo + nav links */}
                    <div className="flex items-center">
                        <Link to="/" className="flex items-center">
                            <img
                                src="/logo.png"
                                alt="Stratia Admissions"
                                className="h-32 w-auto object-contain object-left mix-blend-multiply"
                            />
                        </Link>

                        <div className="hidden sm:ml-8 sm:flex sm:items-center sm:gap-1">
                            {visibleLinks.map((link) => (
                                <Link
                                    key={link.path}
                                    to={link.path}
                                    className={`px-4 py-2 rounded-full text-sm font-medium transition-all flex items-center gap-2
                                        ${
                                            isActive(link.path)
                                                ? 'bg-[#D6E8D5] text-[#1A4D2E]'
                                                : 'text-[#4A4A4A] hover:bg-[#F8F6F0] hover:text-[#1A4D2E]'
                                        }`}
                                >
                                    <link.icon className="h-4 w-4" />
                                    {link.label}
                                </Link>
                            ))}

                            {/* Admin-only Knowledge Base link, preserved from
                                the previous in-app Navigation. */}
                            {currentUser?.email === 'cvsubs@gmail.com' && (
                                <Link
                                    to="/knowledge-base"
                                    className={`px-4 py-2 rounded-full text-sm font-medium transition-all flex items-center gap-2
                                        ${
                                            isActive('/knowledge-base')
                                                ? 'bg-[#D6E8D5] text-[#1A4D2E]'
                                                : 'text-[#4A4A4A] hover:bg-[#F8F6F0] hover:text-[#1A4D2E]'
                                        }`}
                                >
                                    Knowledge Base
                                </Link>
                            )}
                        </div>
                    </div>

                    {/* Right-side: auth-state-dependent */}
                    <div className="flex items-center gap-3">
                        {currentUser ? (
                            <>
                                <div className="hidden md:flex items-center gap-2">
                                    {currentUser.photoURL && (
                                        <img
                                            src={currentUser.photoURL}
                                            alt={currentUser.displayName}
                                            className="h-8 w-8 rounded-full ring-2 ring-[#D6E8D5]"
                                        />
                                    )}
                                    <span className="text-sm text-[#4A4A4A] font-medium">
                                        {currentUser.displayName || currentUser.email}
                                    </span>
                                </div>
                                <button
                                    onClick={handleLogout}
                                    className="px-3 py-2 text-sm font-medium text-[#4A4A4A] border border-[#E0DED8] rounded-full hover:bg-[#F8F6F0] hover:border-[#1A4D2E] transition-all"
                                >
                                    Sign Out
                                </button>
                                <Link
                                    to="/pricing"
                                    className="hidden sm:inline-flex items-center px-4 py-2 bg-[#1A4D2E] text-white text-sm font-medium rounded-full hover:bg-[#2D6B45] transition-all shadow-md"
                                >
                                    <StarIcon className="h-4 w-4 mr-1" />
                                    Upgrade
                                </Link>
                            </>
                        ) : (
                            <>
                                <Link
                                    to="/"
                                    className="hidden sm:inline-flex items-center text-sm font-medium text-[#4A4A4A] hover:text-[#1A4D2E] transition-colors"
                                >
                                    <ArrowRightOnRectangleIcon className="h-4 w-4 mr-1" />
                                    Sign in
                                </Link>
                                <Link
                                    to="/"
                                    className="inline-flex items-center px-5 py-2.5 bg-[#1A4D2E] text-white text-sm font-semibold rounded-full hover:bg-[#2D6B45] transition-all shadow-md"
                                >
                                    Try Stratia
                                </Link>
                            </>
                        )}
                    </div>
                </div>
            </div>
        </nav>
    );
};

export default Navigation;
