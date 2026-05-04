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

    it('renders one row per tested university with id + count', () => {
        render(<UniversitiesCard universities={sampleCoverage} />);
        expect(screen.getByText('mit')).toBeInTheDocument();
        expect(screen.getByText('stanford_university')).toBeInTheDocument();
        expect(screen.getByText('university_of_california_berkeley')).toBeInTheDocument();
        // Per-row counts.
        expect(screen.getByText(/^8×$/)).toBeInTheDocument();
        expect(screen.getByText(/^3×$/)).toBeInTheDocument();
    });

    it('shows the "covered of total" count in the header', () => {
        render(<UniversitiesCard universities={sampleCoverage} />);
        expect(screen.getByText(/3 of 6 covered/i)).toBeInTheDocument();
    });

    it('lists untested schools', () => {
        render(<UniversitiesCard universities={sampleCoverage} />);
        // The untested section calls out how many are left.
        expect(screen.getByText(/Not yet tested \(3\)/i)).toBeInTheDocument();
        expect(screen.getByText(/princeton/)).toBeInTheDocument();
        expect(screen.getByText(/yale_university/)).toBeInTheDocument();
        expect(screen.getByText(/brown_university/)).toBeInTheDocument();
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
});
