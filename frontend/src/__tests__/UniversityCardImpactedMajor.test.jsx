/**
 * UniversityCard — ImpactedMajorCallout (#284).
 *
 * Deterministic, zero LLM: the amber callout renders exactly when the saved
 * major_choice carries door_flags.entry_risk === 'capped_door' (stamped
 * server-side from the KB's structural signal at set-major-choice time).
 * Anything else — elevated, standard, missing flags — renders NOTHING; a
 * guessed door warning is the trust failure this feature exists to prevent.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import UniversityCard from '../components/stratia/UniversityCard';

const baseUni = {
    university_name: 'University of Washington',
    university_id: 'uw',
    location: 'Seattle, Washington',
    fit_category: 'TARGET',
    match_score: 70,
    available_majors: ['Computer Science', 'Biology'],
};

describe('UniversityCard — impacted-major callout', () => {
    it('renders the amber callout for a capped_door major choice', () => {
        render(
            <UniversityCard
                university={{
                    ...baseUni,
                    major_choice: {
                        primary: 'Computer Science',
                        matched: true,
                        door_flags: { entry_path: 'direct_admit', entry_risk: 'capped_door' },
                    },
                }}
                onMajorChange={vi.fn()}
            />
        );
        const callout = screen.getByTestId('impacted-major-callout');
        expect(callout).toHaveTextContent(
            /Computer Science at University of Washington is direct-admit only/);
        expect(callout).toHaveTextContent(/you can't switch in later/);
        expect(callout).toHaveTextContent(/essays must make the case for this major/);
    });

    it('renders nothing for elevated risk — capped_door only', () => {
        render(
            <UniversityCard
                university={{
                    ...baseUni,
                    major_choice: {
                        primary: 'Computer Science',
                        matched: true,
                        door_flags: { entry_path: 'pre_major', entry_risk: 'elevated' },
                    },
                }}
                onMajorChange={vi.fn()}
            />
        );
        expect(screen.queryByTestId('impacted-major-callout')).toBeNull();
    });

    it('renders nothing without door_flags (no guessed warnings)', () => {
        render(
            <UniversityCard
                university={{
                    ...baseUni,
                    major_choice: { primary: 'Computer Science', matched: true },
                }}
                onMajorChange={vi.fn()}
            />
        );
        expect(screen.queryByTestId('impacted-major-callout')).toBeNull();
    });

    it('renders nothing when no major is chosen even if flags linger', () => {
        render(
            <UniversityCard
                university={{
                    ...baseUni,
                    major_choice: {
                        primary: null,
                        door_flags: { entry_path: 'direct_admit', entry_risk: 'capped_door' },
                    },
                }}
                onMajorChange={vi.fn()}
            />
        );
        expect(screen.queryByTestId('impacted-major-callout')).toBeNull();
    });
});
