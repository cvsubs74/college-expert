/**
 * UniversitiesCard renders the list of schools the QA agent has
 * exercised in recent passing scenarios + the schools from the
 * allowlist that haven't been tested yet.
 *
 * Spec: docs/prd/qa-universities-tracking.md +
 *       docs/design/qa-universities-tracking.md.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import UniversitiesCard from '../components/qa/UniversitiesCard';

describe('UniversitiesCard', () => {
    const sampleCoverage = {
        universities_tested: [
            { id: 'mit', count: 8, last_tested_at: '2026-05-04T05:00:00Z' },
            { id: 'stanford_university', count: 3, last_tested_at: '2026-05-04T04:42:00Z' },
            { id: 'university_of_california_berkeley', count: 2, last_tested_at: '2026-05-04T03:15:00Z' },
        ],
        total_universities_tested: 3,
        universities_untested: ['princeton', 'yale_university', 'brown_university'],
        allowlist_size: 6,
    };

    it('renders one row per tested university with friendly name + count', () => {
        render(<UniversitiesCard universities={sampleCoverage} />);
        // Snake-case ids get prettified by formatUniversityName before
        // hitting the DOM — see the dedicated "Friendly labels" suite
        // below for the full spec.
        expect(screen.getByText('MIT')).toBeInTheDocument();
        expect(screen.getByText('Stanford University')).toBeInTheDocument();
        expect(screen.getByText('UC Berkeley')).toBeInTheDocument();
        // Per-row counts.
        expect(screen.getByText(/^8×$/)).toBeInTheDocument();
        expect(screen.getByText(/^3×$/)).toBeInTheDocument();
    });

    it('shows the "covered of total" count in the header', () => {
        render(<UniversitiesCard universities={sampleCoverage} />);
        expect(screen.getByText(/3 of 6 covered/i)).toBeInTheDocument();
    });

    it('lists untested schools (prettified)', () => {
        render(<UniversitiesCard universities={sampleCoverage} />);
        // The untested section calls out how many are left.
        expect(screen.getByText(/Not yet tested \(3\)/i)).toBeInTheDocument();
        // Auto-prettified names (no overrides for these three).
        expect(screen.getByText(/Princeton/)).toBeInTheDocument();
        expect(screen.getByText(/Yale University/)).toBeInTheDocument();
        expect(screen.getByText(/Brown University/)).toBeInTheDocument();
    });

    it('renders nothing when universities data is missing', () => {
        const { container } = render(<UniversitiesCard />);
        expect(container.firstChild).toBeNull();
    });

    it('renders nothing when no schools tested AND no allowlist', () => {
        const { container } = render(
            <UniversitiesCard
                universities={{
                    universities_tested: [],
                    total_universities_tested: 0,
                    universities_untested: [],
                    allowlist_size: 0,
                }}
            />
        );
        expect(container.firstChild).toBeNull();
    });

    it('renders empty state for untested when allowlist is fully covered', () => {
        render(
            <UniversitiesCard
                universities={{
                    universities_tested: [
                        { id: 'mit', count: 1, last_tested_at: '2026-05-04T05:00:00Z' },
                    ],
                    total_universities_tested: 1,
                    universities_untested: [],
                    allowlist_size: 1,
                }}
            />
        );
        // No "Not yet tested" section when the untested list is empty.
        expect(screen.queryByText(/Not yet tested/i)).toBeNull();
    });

    it('shows truncation hint when tested list is longer than the visible cap', () => {
        const big = {
            universities_tested: Array.from({ length: 25 }, (_, i) => ({
                id: `school_${i}`,
                count: 25 - i,
                last_tested_at: '2026-05-04T05:00:00Z',
            })),
            total_universities_tested: 25,
            universities_untested: [],
            allowlist_size: 25,
        };
        render(<UniversitiesCard universities={big} />);
        // Cap is 15 in the visible list — expect a "+ 10 more" indicator.
        expect(screen.getByText(/\+ 10 more/i)).toBeInTheDocument();
    });

    it('tolerates legacy /summary responses without the universities fields', () => {
        const { container } = render(
            <UniversitiesCard universities={{ journeys: [] }} />
        );
        expect(container.firstChild).toBeNull();
    });

    // ---- Friendly label rendering -------------------------------------
    // Spec: docs/prd/qa-university-friendly-labels.md.

    describe('Friendly labels', () => {
        const sampleWithCanonicalIds = {
            universities_tested: [
                { id: 'massachusetts_institute_of_technology',
                  count: 3, last_tested_at: '2026-05-04T05:00:00Z' },
                { id: 'georgia_institute_of_technology',
                  count: 2, last_tested_at: '2026-05-04T04:42:00Z' },
                { id: 'tufts_university',
                  count: 1, last_tested_at: '2026-05-04T03:15:00Z' },
            ],
            total_universities_tested: 3,
            universities_untested: ['boston_college', 'rice_university'],
            allowlist_size: 5,
        };

        it('renders the friendly override label instead of the snake_case id', () => {
            render(<UniversitiesCard universities={sampleWithCanonicalIds} />);
            expect(screen.getByText('MIT')).toBeInTheDocument();
            expect(screen.getByText('Georgia Tech')).toBeInTheDocument();
            // Snake-case form should not appear in the visible body.
            expect(screen.queryByText(
                'massachusetts_institute_of_technology'
            )).toBeNull();
        });

        it('auto-prettifies an id without an override entry', () => {
            render(<UniversitiesCard universities={sampleWithCanonicalIds} />);
            // Tufts has no override; underscore→space + titlecase wins.
            expect(screen.getByText('Tufts University')).toBeInTheDocument();
        });

        it('preserves canonical id as a tooltip / aria-label for debugging', () => {
            render(<UniversitiesCard universities={sampleWithCanonicalIds} />);
            // The MIT row's title attribute exposes the canonical id so an
            // operator can copy it for queries / tickets.
            const mitRow = screen.getByText('MIT').closest('li');
            expect(mitRow).toHaveAttribute('title',
                'massachusetts_institute_of_technology');
        });

        it('prettifies the untested list', () => {
            render(<UniversitiesCard universities={sampleWithCanonicalIds} />);
            // The untested chunk should read "Boston College, Rice University"
            // — not the snake_case form.
            const node = screen.getByText(/Boston College/);
            expect(node.textContent).toContain('Boston College');
            expect(node.textContent).toContain('Rice University');
            expect(node.textContent).not.toContain('boston_college');
        });
    });
});
