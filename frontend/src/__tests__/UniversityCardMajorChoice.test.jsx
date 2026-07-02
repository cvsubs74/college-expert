/**
 * UniversityCard — major round-trip UI (#283).
 *
 * The dropdown persists the decision immediately (free, optimistic in the
 * parent); the recompute is a separate, explicit 1-credit chip that only
 * appears when the saved fit was computed for a different major. The old
 * confirm-then-recompute modal is gone. matched:false shows the amber
 * unmatched dot, never a rewrite of the student's wording.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import UniversityCard from '../components/stratia/UniversityCard';

const baseUni = {
    university_name: 'University of Washington',
    university_id: 'uw',
    location: 'Seattle, Washington',
    fit_category: 'TARGET',
    match_score: 70,
    available_majors: ['Computer Science', 'Biology', 'Mathematics'],
};

describe('UniversityCard — major dropdown persistence', () => {
    it('reads the current selection from major_choice.primary over selected_major', () => {
        render(
            <UniversityCard
                university={{
                    ...baseUni,
                    selected_major: 'Biology',
                    major_choice: { primary: 'Computer Science', matched: true },
                }}
                onMajorChange={vi.fn()}
            />
        );
        expect(screen.getByLabelText('Intended major')).toHaveValue('Computer Science');
    });

    it('falls back to legacy selected_major when major_choice is absent', () => {
        render(
            <UniversityCard
                university={{ ...baseUni, selected_major: 'Biology' }}
                onMajorChange={vi.fn()}
            />
        );
        expect(screen.getByLabelText('Intended major')).toHaveValue('Biology');
    });

    it('fires onMajorChange immediately on change — no confirmation modal', () => {
        const onMajorChange = vi.fn();
        render(
            <UniversityCard
                university={{ ...baseUni, selected_major: 'Biology' }}
                onMajorChange={onMajorChange}
            />
        );

        fireEvent.change(screen.getByLabelText('Intended major'), {
            target: { value: 'Mathematics' },
        });

        expect(onMajorChange).toHaveBeenCalledTimes(1);
        expect(onMajorChange).toHaveBeenCalledWith('uw', 'Mathematics');
        expect(screen.queryByText(/confirm major change/i)).toBeNull();
        expect(screen.queryByText(/uses.*1 credit/i)).toBeNull();
    });

    it('keeps an unmatched (as-given) name selectable in the dropdown', () => {
        render(
            <UniversityCard
                university={{
                    ...baseUni,
                    major_choice: { primary: 'Comp Sci & Stuff', matched: false },
                }}
                onMajorChange={vi.fn()}
            />
        );
        expect(screen.getByLabelText('Intended major')).toHaveValue('Comp Sci & Stuff');
    });

    it('shows the amber unmatched dot with tooltip when matched === false', () => {
        render(
            <UniversityCard
                university={{
                    ...baseUni,
                    major_choice: { primary: 'Comp Sci & Stuff', matched: false },
                    major_choice_note: 'stored as given; confirm the name',
                }}
                onMajorChange={vi.fn()}
            />
        );
        expect(screen.getByTestId('major-unmatched-dot')).toBeInTheDocument();
        expect(
            screen.getByText(/we couldn't match this name to University of Washington's official major list/i)
        ).toBeInTheDocument();
        expect(screen.getByText(/stored as given; confirm the name/i)).toBeInTheDocument();
    });

    it('hides the unmatched dot when the choice matched', () => {
        render(
            <UniversityCard
                university={{
                    ...baseUni,
                    major_choice: { primary: 'Computer Science', matched: true },
                }}
                onMajorChange={vi.fn()}
            />
        );
        expect(screen.queryByTestId('major-unmatched-dot')).toBeNull();
    });
});

describe('UniversityCard — explicit recompute chip', () => {
    it('offers recompute when the fit was computed for a different major', () => {
        const onRecomputeWithMajor = vi.fn();
        render(
            <UniversityCard
                university={{
                    ...baseUni,
                    major_choice: { primary: 'Computer Science', matched: true },
                    fit_analysis: { intended_major_used: 'Biology' },
                }}
                onMajorChange={vi.fn()}
                onRecomputeWithMajor={onRecomputeWithMajor}
            />
        );

        const chip = screen.getByRole('button', {
            name: /fit was computed for Biology — Recompute with Computer Science\? \(1 credit\)/i,
        });
        fireEvent.click(chip);
        expect(onRecomputeWithMajor).toHaveBeenCalledTimes(1);
        expect(onRecomputeWithMajor).toHaveBeenCalledWith(
            expect.objectContaining({ university_id: 'uw' }),
            'Computer Science'
        );
    });

    it('falls back to the old fit\'s major_strategy.intended_major for the comparison', () => {
        render(
            <UniversityCard
                university={{
                    ...baseUni,
                    selected_major: 'Mathematics',
                    fit_analysis: { major_strategy: { intended_major: 'Biology' } },
                }}
                onMajorChange={vi.fn()}
                onRecomputeWithMajor={vi.fn()}
            />
        );
        expect(
            screen.getByRole('button', { name: /fit was computed for Biology — Recompute with Mathematics/i })
        ).toBeInTheDocument();
    });

    it('renders no chip when the fit already matches the chosen major', () => {
        render(
            <UniversityCard
                university={{
                    ...baseUni,
                    major_choice: { primary: 'Computer Science', matched: true },
                    fit_analysis: { intended_major_used: 'computer science' }, // case-insensitive match
                }}
                onMajorChange={vi.fn()}
                onRecomputeWithMajor={vi.fn()}
            />
        );
        expect(screen.queryByText(/recompute with/i)).toBeNull();
    });

    it('renders no chip when the fit carries no major (nothing to compare)', () => {
        render(
            <UniversityCard
                university={{
                    ...baseUni,
                    major_choice: { primary: 'Computer Science', matched: true },
                    fit_analysis: {},
                }}
                onMajorChange={vi.fn()}
                onRecomputeWithMajor={vi.fn()}
            />
        );
        expect(screen.queryByText(/recompute with/i)).toBeNull();
    });
});
