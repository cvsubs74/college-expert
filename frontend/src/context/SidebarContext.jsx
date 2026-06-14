import React, { createContext, useContext, useState, useCallback } from 'react';

/**
 * SidebarContext — shared state for the collapsible left navigation rail.
 *
 * `collapsed` (desktop): icon-only rail vs. full icons+labels. Persisted to
 * localStorage so the choice survives reloads.
 * `mobileOpen`: whether the off-canvas drawer is open on small screens.
 *
 * Consumers (AppLayout, Resources pages) read `collapsed` to offset their
 * content (`lg:pl-16` vs `lg:pl-60`) so the fixed rail never overlaps content.
 */

const STORAGE_KEY = 'stratia_nav_collapsed';

const SidebarContext = createContext(null);

export function SidebarProvider({ children }) {
    const [collapsed, setCollapsedState] = useState(() => {
        try {
            return localStorage.getItem(STORAGE_KEY) === 'true';
        } catch {
            return false;
        }
    });
    const [mobileOpen, setMobileOpen] = useState(false);

    const setCollapsed = useCallback((next) => {
        setCollapsedState((prev) => {
            const value = typeof next === 'function' ? next(prev) : next;
            try {
                localStorage.setItem(STORAGE_KEY, String(value));
            } catch {
                /* storage unavailable — keep in-memory state only */
            }
            return value;
        });
    }, []);

    const toggleCollapsed = useCallback(() => setCollapsed((c) => !c), [setCollapsed]);

    return (
        <SidebarContext.Provider
            value={{ collapsed, setCollapsed, toggleCollapsed, mobileOpen, setMobileOpen }}
        >
            {children}
        </SidebarContext.Provider>
    );
}

/**
 * useSidebar — access the rail state. Falls back to a safe expanded/no-op
 * default when rendered outside a provider (e.g. an isolated unit test), so a
 * stray <Navigation/> never crashes.
 */
export function useSidebar() {
    const ctx = useContext(SidebarContext);
    if (!ctx) {
        return {
            collapsed: false,
            setCollapsed: () => {},
            toggleCollapsed: () => {},
            mobileOpen: false,
            setMobileOpen: () => {},
        };
    }
    return ctx;
}

/** Tailwind left-padding for a content area sitting beside the rail. */
export function sidebarContentPad(collapsed) {
    return collapsed ? 'lg:pl-16' : 'lg:pl-60';
}
