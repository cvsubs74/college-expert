import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import {
    Bars3Icon,
    XMarkIcon,
    UserCircleIcon,
    BookOpenIcon,
    KeyIcon
} from '@heroicons/react/24/outline';

/**
 * StratiaNavBar - M3 TopAppBar with transparent-to-frosted scroll behavior
 * 
 * Features:
 * - Transparent when at top, frosted glass on scroll
 * - Book & Key logo placeholder
 * - Pill-shaped active link indicators
 * - Mobile responsive hamburger menu
 */
const StratiaNavBar = () => {
    const [isScrolled, setIsScrolled] = useState(false);
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
    const { currentUser, logout } = useAuth();
    const location = useLocation();

    // Handle scroll for transparent → frosted transition
    useEffect(() => {
        const handleScroll = () => {
            setIsScrolled(window.scrollY > 20);
        };
        window.addEventListener('scroll', handleScroll);
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    const navLinks = [
        { path: '/launchpad', label: 'My Schools' },
        { path: '/explorer', label: 'Discover' },
        { path: '/profile', label: 'Profile' },
    ];

    const isActive = (path) => location.pathname === path;

    return (
        <nav className={`stratia-nav ${isScrolled ? 'stratia-nav-solid' : 'stratia-nav-transparent'}`}>
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex items-center justify-between h-16">
                    {/* Logo */}
                    <Link to="/" className="flex items-center gap-2 group">
                        {/* Book & Key Icon Placeholder */}
                        <div className="relative w-10 h-10 flex items-center justify-center rounded-xl bg-gradient-to-br from-[#1A4D2E] to-[#2D6B45] shadow-md group-hover:shadow-lg transition-shadow">
                            <BookOpenIcon className="w-5 h-5 text-white absolute" style={{ top: '8px', left: '8px' }} />
                            <KeyIcon className="w-4 h-4 text-[#D6E8D5] absolute" style={{ bottom: '6px', right: '6px' }} />
                        </div>

                        {/* Brand Text - Serif for "Stratia", Sans for "Admissions" */}
                        <div className="flex items-baseline gap-1">
                            <span className="font-serif text-xl font-semibold text-[#1A4D2E]">
                                Stratia
                            </span>
                            <span className="font-sans text-sm font-medium text-[#4A4A4A]">
                                Admissions
                            </span>
                        </div>
                    </Link>

                    {/* Desktop Navigation */}
                    <div className="hidden md:flex items-center gap-2">
                        {navLinks.map((link) => (
                            <Link
                                key={link.path}
                                to={link.path}
                                className={`stratia-nav-link ${isActive(link.path) ? 'stratia-nav-link-active' : ''}`}
                            >
                                {link.label}
                            </Link>
                        ))}

                        {/* User Menu */}
                        {currentUser ? (
                            <div className="flex items-center gap-3 ml-4 pl-4 border-l border-[#E0DED8]">
                                <span className="text-sm text-[#4A4A4A]">
                                    {currentUser.displayName || currentUser.email?.split('@')[0]}
                                </span>
                                <button
                                    onClick={logout}
                                    className="stratia-btn-outlined text-sm py-1.5 px-3"
                                >
                                    Sign Out
                                </button>
                            </div>
                        ) : (
                            <Link to="/login" className="stratia-btn-filled ml-4">
                                Sign In
                            </Link>
                        )}
                    </div>

                    {/* Mobile Menu Button */}
                    <button
                        className="md:hidden p-2 rounded-lg hover:bg-[rgba(26,77,46,0.08)] transition-colors"
                        onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                    >
                        {mobileMenuOpen ? (
                            <XMarkIcon className="w-6 h-6 text-[#2C2C2C]" />
                        ) : (
                            <Bars3Icon className="w-6 h-6 text-[#2C2C2C]" />
                        )}
                    </button>
                </div>

                {/* Mobile Menu */}
                {mobileMenuOpen && (
                    <div className="md:hidden py-4 border-t border-[#E0DED8] animate-fade-up">
                        <div className="flex flex-col gap-2">
                            {navLinks.map((link) => (
                                <Link
                                    key={link.path}
                                    to={link.path}
                                    className={`stratia-nav-link ${isActive(link.path) ? 'stratia-nav-link-active' : ''}`}
                                    onClick={() => setMobileMenuOpen(false)}
                                >
                                    {link.label}
                                </Link>
                            ))}

                            {currentUser ? (
                                <button
                                    onClick={() => { logout(); setMobileMenuOpen(false); }}
                                    className="stratia-btn-outlined mt-2"
                                >
                                    Sign Out
                                </button>
                            ) : (
                                <Link
                                    to="/login"
                                    className="stratia-btn-filled mt-2 text-center"
                                    onClick={() => setMobileMenuOpen(false)}
                                >
                                    Sign In
                                </Link>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </nav>
    );
};

export default StratiaNavBar;
