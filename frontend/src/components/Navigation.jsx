import React, { useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
    DocumentTextIcon,
    BookOpenIcon,
    BuildingLibraryIcon,
    SparklesIcon,
    RocketLaunchIcon,
    StarIcon,
    BeakerIcon,
    CpuChipIcon,
    CircleStackIcon,
    AcademicCapIcon,
    ScaleIcon,
    ArrowRightOnRectangleIcon,
    Bars3Icon,
    XMarkIcon,
    ChevronDoubleLeftIcon,
    ChevronDoubleRightIcon,
} from '@heroicons/react/24/outline';
import { useAuth } from '../context/AuthContext';
import { useSidebar } from '../context/SidebarContext';
import { logout } from '../services/authService';

// Single Navigation component used by:
//   1. AppLayout (protected pages — Profile/Discover/Launchpad/Roadmap/Resources)
//   2. ResourcesPage and ResourcePaperPage (public pages — signed-in visitors get
//      the in-app rail; logged-out visitors get MarketingHeader instead)
//
// #231 — converted from a top bar into a collapsible LEFT sidebar:
//   • Desktop (lg+): a fixed left rail. Expanded = icons + labels (240px);
//     collapsed = icon-only rail (64px) with hover/focus tooltips. A chevron
//     toggle flips between them; the choice persists (SidebarContext → localStorage).
//   • Mobile (<lg): an off-canvas drawer opened from a slim sticky top bar
//     (hamburger). Tapping a link or the backdrop closes it.
//
// Auth-aware: links with `requiresAuth: true` are hidden when logged out. The
// footer shows the user + Upgrade + Sign out when signed in, or Sign in / Try
// Stratia when logged out.

const NAV_LINKS = [
    { path: '/profile', label: 'Profile', icon: DocumentTextIcon, requiresAuth: true },
    { path: '/universities', label: 'Discover', icon: BuildingLibraryIcon, requiresAuth: true },
    { path: '/major-map', label: 'Major Map', icon: AcademicCapIcon, requiresAuth: true },
    { path: '/launchpad', label: 'Launchpad', icon: RocketLaunchIcon, requiresAuth: true },
    { path: '/decision-ledger', label: 'Decision Ledger', icon: ScaleIcon, requiresAuth: true },
    { path: '/roadmap', label: 'Roadmap', icon: SparklesIcon, requiresAuth: true },
    { path: '/research', label: 'Research', icon: BeakerIcon, requiresAuth: true },
    { path: '/connect', label: 'Agents', icon: CpuChipIcon, requiresAuth: true },
    { path: '/resources', label: 'Resources', icon: BookOpenIcon, requiresAuth: false },
];

const ADMIN_EMAIL = 'cvsubs@gmail.com';

/** A single nav row — icon always; label hidden (with tooltip) when collapsed. */
function NavItem({ to, label, icon: Icon, active, collapsed, onNavigate }) {
    return (
        <Link
            to={to}
            onClick={onNavigate}
            title={collapsed ? label : undefined}
            aria-label={label}
            aria-current={active ? 'page' : undefined}
            className={`group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all
                ${collapsed ? 'lg:justify-center lg:px-0' : ''}
                ${
                    active
                        ? 'bg-[#D6E8D5] text-[#1A4D2E]'
                        : 'text-[#4A4A4A] hover:bg-[#F8F6F0] hover:text-[#1A4D2E]'
                }`}
        >
            <Icon className="h-5 w-5 shrink-0" aria-hidden="true" />
            <span className={collapsed ? 'lg:hidden' : ''}>{label}</span>
        </Link>
    );
}

/** Footer link/button — shares the icon-only-when-collapsed treatment. */
function FooterLink({ to, label, icon: Icon, collapsed, primary, onNavigate }) {
    return (
        <Link
            to={to}
            onClick={onNavigate}
            title={collapsed ? label : undefined}
            aria-label={label}
            className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold transition-all
                ${collapsed ? 'lg:justify-center lg:px-0' : ''}
                ${
                    primary
                        ? 'bg-[#1A4D2E] text-white hover:bg-[#2D6B45] shadow-sm'
                        : 'text-[#4A4A4A] hover:bg-[#F8F6F0] hover:text-[#1A4D2E]'
                }`}
        >
            {Icon && <Icon className="h-5 w-5 shrink-0" aria-hidden="true" />}
            <span className={collapsed ? 'lg:hidden' : ''}>{label}</span>
        </Link>
    );
}

const Navigation = () => {
    const location = useLocation();
    const { currentUser } = useAuth();
    const { collapsed, toggleCollapsed, mobileOpen, setMobileOpen } = useSidebar();

    const isActive = (path) =>
        path === '/resources'
            ? location.pathname.startsWith('/resources')
            : location.pathname === path;

    // Close the mobile drawer whenever the route changes.
    useEffect(() => {
        setMobileOpen(false);
    }, [location.pathname, setMobileOpen]);

    const handleLogout = async () => {
        try {
            await logout();
        } catch (error) {
            console.error('Failed to log out', error);
        }
    };

    const closeMobile = () => setMobileOpen(false);

    // When logged out, only public links remain (today: just Resources).
    const visibleLinks = NAV_LINKS.filter((l) => !l.requiresAuth || currentUser);
    const showKnowledgeBase = currentUser?.email === ADMIN_EMAIL;

    return (
        <>
            {/* Mobile-only slim top bar with the hamburger + logo. */}
            <div className="lg:hidden sticky top-0 z-30 flex items-center justify-between h-14 px-4 bg-[#FDFCF7]/95 backdrop-blur-sm border-b border-[#E0DED8]">
                <button
                    type="button"
                    onClick={() => setMobileOpen(true)}
                    aria-label="Open navigation"
                    aria-expanded={mobileOpen}
                    className="-ml-2 p-2 rounded-lg text-[#4A4A4A] hover:bg-[#F8F6F0] hover:text-[#1A4D2E] transition-colors"
                >
                    <Bars3Icon className="h-6 w-6" />
                </button>
                <Link to="/" className="flex items-center" aria-label="Stratia Admissions home">
                    <img
                        src="/logo.png"
                        alt="Stratia Admissions"
                        className="h-8 w-auto max-w-[140px] object-contain mix-blend-multiply"
                    />
                </Link>
                <span className="w-8" aria-hidden="true" />
            </div>

            {/* Backdrop behind the mobile drawer. */}
            {mobileOpen && (
                <div
                    className="lg:hidden fixed inset-0 z-40 bg-black/30 backdrop-blur-[1px]"
                    onClick={closeMobile}
                    aria-hidden="true"
                />
            )}

            {/* The rail. Fixed on the left for all breakpoints; on mobile it slides
                off-canvas (translate) unless `mobileOpen`. On lg+ it is always
                visible and its WIDTH animates between collapsed/expanded. */}
            <nav
                aria-label="Primary"
                className={`fixed inset-y-0 left-0 z-50 flex flex-col w-64 bg-[#FDFCF7] border-r border-[#E0DED8]
                    transition-transform duration-300 ease-in-out
                    ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}
                    lg:translate-x-0 lg:transition-[width] ${collapsed ? 'lg:w-16' : 'lg:w-60'}`}
            >
                {/* Header: brand + mobile close button. */}
                <div className="flex items-center justify-between h-16 px-3 border-b border-[#E0DED8] shrink-0">
                    <Link
                        to="/"
                        onClick={closeMobile}
                        className="flex items-center overflow-hidden"
                        aria-label="Stratia Admissions home"
                    >
                        {/* Collapsed desktop rail: compact monogram. */}
                        {collapsed && (
                            <span className="hidden lg:flex h-9 w-9 items-center justify-center rounded-lg bg-[#1A4D2E] text-white text-base font-bold">
                                S
                            </span>
                        )}
                        {/* Mobile + expanded desktop: full wordmark. */}
                        <img
                            src="/logo.png"
                            alt="Stratia Admissions"
                            className={`h-9 w-auto max-w-[150px] object-contain object-left mix-blend-multiply ${
                                collapsed ? 'lg:hidden' : ''
                            }`}
                        />
                    </Link>
                    <button
                        type="button"
                        onClick={closeMobile}
                        aria-label="Close navigation"
                        className="lg:hidden p-2 -mr-1 rounded-lg text-[#4A4A4A] hover:bg-[#F8F6F0] transition-colors"
                    >
                        <XMarkIcon className="h-5 w-5" />
                    </button>
                </div>

                {/* Links. */}
                <div className="flex-1 overflow-y-auto px-2 py-4 space-y-1">
                    {visibleLinks.map((link) => (
                        <NavItem
                            key={link.path}
                            to={link.path}
                            label={link.label}
                            icon={link.icon}
                            active={isActive(link.path)}
                            collapsed={collapsed}
                            onNavigate={closeMobile}
                        />
                    ))}
                    {showKnowledgeBase && (
                        <NavItem
                            to="/knowledge-base"
                            label="Knowledge Base"
                            icon={CircleStackIcon}
                            active={isActive('/knowledge-base')}
                            collapsed={collapsed}
                            onNavigate={closeMobile}
                        />
                    )}
                </div>

                {/* Footer: identity + actions, then the desktop collapse toggle. */}
                <div className="shrink-0 border-t border-[#E0DED8] p-2 space-y-1">
                    {currentUser ? (
                        <>
                            <div
                                className={`flex items-center gap-3 px-3 py-2 ${
                                    collapsed ? 'lg:justify-center lg:px-0' : ''
                                }`}
                                title={collapsed ? currentUser.displayName || currentUser.email : undefined}
                            >
                                {currentUser.photoURL ? (
                                    <img
                                        src={currentUser.photoURL}
                                        alt=""
                                        className="h-8 w-8 rounded-full ring-2 ring-[#D6E8D5] shrink-0"
                                    />
                                ) : (
                                    <span className="h-8 w-8 rounded-full bg-[#D6E8D5] text-[#1A4D2E] flex items-center justify-center text-sm font-semibold shrink-0">
                                        {(currentUser.displayName || currentUser.email || '?').charAt(0).toUpperCase()}
                                    </span>
                                )}
                                <span
                                    className={`text-sm text-[#4A4A4A] font-medium truncate ${
                                        collapsed ? 'lg:hidden' : ''
                                    }`}
                                >
                                    {currentUser.displayName || currentUser.email}
                                </span>
                            </div>
                            <FooterLink
                                to="/pricing"
                                label="Upgrade"
                                icon={StarIcon}
                                collapsed={collapsed}
                                primary
                                onNavigate={closeMobile}
                            />
                            <button
                                type="button"
                                onClick={() => {
                                    closeMobile();
                                    handleLogout();
                                }}
                                title={collapsed ? 'Sign Out' : undefined}
                                aria-label="Sign Out"
                                className={`w-full flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-[#4A4A4A] hover:bg-[#F8F6F0] hover:text-[#1A4D2E] transition-all ${
                                    collapsed ? 'lg:justify-center lg:px-0' : ''
                                }`}
                            >
                                <ArrowRightOnRectangleIcon className="h-5 w-5 shrink-0" aria-hidden="true" />
                                <span className={collapsed ? 'lg:hidden' : ''}>Sign Out</span>
                            </button>
                        </>
                    ) : (
                        <>
                            <FooterLink
                                to="/"
                                label="Sign in"
                                icon={ArrowRightOnRectangleIcon}
                                collapsed={collapsed}
                                onNavigate={closeMobile}
                            />
                            <FooterLink
                                to="/"
                                label="Try Stratia"
                                icon={StarIcon}
                                collapsed={collapsed}
                                primary
                                onNavigate={closeMobile}
                            />
                        </>
                    )}

                    {/* Desktop-only collapse/expand toggle. */}
                    <button
                        type="button"
                        onClick={toggleCollapsed}
                        aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
                        aria-expanded={!collapsed}
                        className={`hidden lg:flex items-center gap-3 w-full rounded-xl px-3 py-2.5 text-sm font-medium text-[#4A4A4A] hover:bg-[#F8F6F0] hover:text-[#1A4D2E] transition-all ${
                            collapsed ? 'lg:justify-center lg:px-0' : ''
                        }`}
                    >
                        {collapsed ? (
                            <ChevronDoubleRightIcon className="h-5 w-5 shrink-0" aria-hidden="true" />
                        ) : (
                            <>
                                <ChevronDoubleLeftIcon className="h-5 w-5 shrink-0" aria-hidden="true" />
                                <span>Collapse</span>
                            </>
                        )}
                    </button>
                </div>
            </nav>
        </>
    );
};

export default Navigation;
