/**
 * Navigation — collapsible left sidebar (#231).
 *
 * Replaces the legacy top-bar overflow test (#133). Asserts the sidebar's
 * accessibility + behavior contract: the Primary nav landmark, its links,
 * active-route marking, the footer actions, the mobile drawer trigger, and the
 * collapse/expand toggle. jsdom has no layout engine, so we assert
 * roles/labels/attributes rather than computed pixels.
 */

import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Navigation from '../components/Navigation';
import { SidebarProvider } from '../context/SidebarContext';

// AuthContext is globally mocked in setup.js (returns a signed-in test user).

function renderNav(initialPath = '/profile') {
    return render(
        <MemoryRouter initialEntries={[initialPath]}>
            <SidebarProvider>
                <Navigation />
            </SidebarProvider>
        </MemoryRouter>,
    );
}

describe('Navigation — collapsible left sidebar (#231)', () => {
    it('renders the Primary nav landmark with every in-app link', () => {
        renderNav();
        expect(screen.getByRole('navigation', { name: /primary/i })).toBeInTheDocument();
        for (const label of ['Profile', 'Discover', 'Launchpad', 'Roadmap', 'Research', 'Agents', 'Resources']) {
            expect(screen.getByRole('link', { name: label })).toBeInTheDocument();
        }
    });

    it('marks the current route as active', () => {
        renderNav('/profile');
        expect(screen.getByRole('link', { name: 'Profile' })).toHaveAttribute('aria-current', 'page');
        expect(screen.getByRole('link', { name: 'Discover' })).not.toHaveAttribute('aria-current');
    });

    it('exposes the user actions (Upgrade + Sign Out) in the footer', () => {
        renderNav();
        expect(screen.getByRole('link', { name: 'Upgrade' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Sign Out' })).toBeInTheDocument();
    });

    it('provides a mobile drawer trigger', () => {
        renderNav();
        expect(screen.getByRole('button', { name: /open navigation/i })).toBeInTheDocument();
    });

    it('toggles between Collapse and Expand', () => {
        renderNav();
        const collapseBtn = screen.getByRole('button', { name: /collapse sidebar/i });
        expect(collapseBtn).toHaveAttribute('aria-expanded', 'true');

        fireEvent.click(collapseBtn);

        const expandBtn = screen.getByRole('button', { name: /expand sidebar/i });
        expect(expandBtn).toHaveAttribute('aria-expanded', 'false');
    });
});
