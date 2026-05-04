/**
 * CoverageCard renders the validated end-to-end journeys returned by
 * GET /summary's `coverage` block.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import CoverageCard from '../components/qa/CoverageCard';

describe('CoverageCard', () => {
    const sampleCoverage = {
        total_journeys: 2,
        journeys: [
            {
                id: 'abc123',
                surfaces: ['college_list', 'profile', 'roadmap'],
                summary: 'College list → profile build → roadmap',
                scenarios: [
                    { id: 'junior_spring_5school', verified_at: '2026-05-04T04:30:00Z' },
                    { id: 'senior_fall_application_crunch', verified_at: '2026-05-04T04:00:00Z' },
                ],
                verified_count: 12,
            },
            {
                id: 'def456',
                surfaces: ['profile'],
                summary: 'Profile only',
                scenarios: [
                    { id: 'profile_only_demo', verified_at: '2026-05-04T03:00:00Z' },
                ],
                verified_count: 3,
            },
        ],
    };

    it('renders one row per journey with summary + surfaces + count', () => {
        render(<CoverageCard coverage={sampleCoverage} />);
        // Both journey summaries appear.
        expect(screen.getByText(/College list → profile build → roadmap/i)).toBeInTheDocument();
        expect(screen.getByText(/Profile only/i)).toBeInTheDocument();
        // Surface badges (using surface text).
        expect(screen.getByText('college_list')).toBeInTheDocument();
        expect(screen.getByText('roadmap')).toBeInTheDocument();
        // verified_count is shown.
        expect(screen.getByText('12')).toBeInTheDocument();
        expect(screen.getByText('3')).toBeInTheDocument();
    });

    it('shows total_journeys in the header', () => {
        render(<CoverageCard coverage={sampleCoverage} />);
        expect(screen.getByText(/2 journeys/i)).toBeInTheDocument();
    });

    it('lists scenario IDs as evidence', () => {
        render(<CoverageCard coverage={sampleCoverage} />);
        expect(screen.getByText(/junior_spring_5school/i)).toBeInTheDocument();
    });

    it('renders nothing when coverage is empty', () => {
        const { container } = render(
            <CoverageCard coverage={{ total_journeys: 0, journeys: [] }} />
        );
        expect(container.firstChild).toBeNull();
    });

    it('renders nothing when coverage is missing', () => {
        const { container } = render(<CoverageCard />);
        expect(container.firstChild).toBeNull();
    });

    it("uses singular 'journey' when total is 1", () => {
        render(
            <CoverageCard
                coverage={{
                    total_journeys: 1,
                    journeys: [sampleCoverage.journeys[1]],
                }}
            />
        );
        // Header pill should read "1 journey" (singular).
        expect(screen.getByText(/^1 journey$/)).toBeInTheDocument();
    });

    it('truncates the verified-by list past 3 scenarios', () => {
        const heavyJourney = {
            id: 'heavy',
            surfaces: ['profile'],
            summary: 'Heavy',
            scenarios: [
                { id: 's1', verified_at: '2026-05-04T01:00:00Z' },
                { id: 's2', verified_at: '2026-05-04T02:00:00Z' },
                { id: 's3', verified_at: '2026-05-04T03:00:00Z' },
                { id: 's4', verified_at: '2026-05-04T04:00:00Z' },
                { id: 's5', verified_at: '2026-05-04T05:00:00Z' },
            ],
            verified_count: 5,
        };
        render(<CoverageCard coverage={{ total_journeys: 1, journeys: [heavyJourney] }} />);
        expect(screen.getByText(/\+ 2 more/i)).toBeInTheDocument();
    });
});
