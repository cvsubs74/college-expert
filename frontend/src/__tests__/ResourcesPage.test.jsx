/**
 * Vitest coverage for the /resources hub.
 *
 * Asserts:
 *  - Hub renders both whitepaper cards from the data registry.
 *  - Each card links to the right /resources/<slug>.
 *  - Per-paper page renders title, hero visual, and at least one section.
 *  - Unknown slug redirects to /resources.
 *  - The cross-promo footer links to the *other* paper.
 *
 * Auth context is mocked to "logged out" — Resources is a public surface
 * and the header should still render (showing the Try Stratia CTA).
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

// Mock auth context — Resources is public, but the header reads currentUser.
vi.mock('../context/AuthContext', () => ({
    useAuth: () => ({ currentUser: null }),
    AuthProvider: ({ children }) => children,
}));

import ResourcesPage from '../pages/ResourcesPage';
import ResourcePaperPage from '../pages/ResourcePaperPage';
import { papers } from '../data/resources';

const renderAt = (path) =>
    render(
        <MemoryRouter initialEntries={[path]}>
            <Routes>
                <Route path="/resources" element={<ResourcesPage />} />
                <Route path="/resources/:slug" element={<ResourcePaperPage />} />
            </Routes>
        </MemoryRouter>
    );

describe('ResourcesPage hub', () => {
    it('renders a card for every registered paper', () => {
        renderAt('/resources');
        for (const paper of papers) {
            // Title appears in the card; heading role is too strict because the
            // title might render with custom styling, so check by text.
            expect(screen.getByText(paper.title)).toBeInTheDocument();
        }
    });

    it('exposes the hero copy and signup-free messaging', () => {
        renderAt('/resources');
        expect(screen.getByText(/Why and how Stratia works/i)).toBeInTheDocument();
        expect(screen.getByText(/no signup/i)).toBeInTheDocument();
    });

    it('each card links to its /resources/<slug>', () => {
        renderAt('/resources');
        for (const paper of papers) {
            // The card is a Link wrapping the title. The closest anchor's href
            // should match.
            const titleEl = screen.getByText(paper.title);
            const anchor = titleEl.closest('a');
            expect(anchor).not.toBeNull();
            expect(anchor.getAttribute('href')).toBe(`/resources/${paper.slug}`);
        }
    });
});

describe('ResourcePaperPage per-paper view', () => {
    it('renders the title, subtitle, and at least one section for paper 1', () => {
        const paper1 = papers[0];
        renderAt(`/resources/${paper1.slug}`);

        // The paper title and subtitle render inside PaperHero
        expect(screen.getByRole('heading', { level: 1, name: paper1.title })).toBeInTheDocument();
        expect(screen.getByText(paper1.subtitle)).toBeInTheDocument();

        // First section's title rendered
        expect(screen.getByRole('heading', { level: 2, name: new RegExp(paper1.sections[0].title.split(':')[0], 'i') })).toBeInTheDocument();
    });

    it('renders the cross-promo footer pointing at the other paper', () => {
        const [paper1, paper2] = papers;
        renderAt(`/resources/${paper1.slug}`);

        expect(screen.getByText(/read next/i)).toBeInTheDocument();
        // Cross-promo CTA link is the only "Read paper" CTA on a per-paper page
        const readCta = screen.getByRole('link', { name: /read paper/i });
        expect(readCta.getAttribute('href')).toBe(`/resources/${paper2.slug}`);
    });

    it('redirects to /resources when the slug is unknown', () => {
        renderAt('/resources/this-slug-does-not-exist');
        // After the Navigate, ResourcesPage renders. Hub heading is the signal.
        expect(screen.getByText(/Why and how Stratia works/i)).toBeInTheDocument();
    });
});
