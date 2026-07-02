/**
 * UniversityCard — the Major Chances action button (#302).
 *
 * The button appears only when onMajorChances is wired, sits in the action
 * row alongside Fit Analysis / Chat, and hands the whole university object to
 * the handler (the Launchpad opens MajorChancesView in place).
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
};

describe('UniversityCard — Major Chances button', () => {
    it('renders the button and calls onMajorChances with the university', () => {
        const onMajorChances = vi.fn();
        render(<UniversityCard university={baseUni} onMajorChances={onMajorChances} />);
        const btn = screen.getByRole('button', { name: /view major chances/i });
        expect(btn).toBeInTheDocument();
        fireEvent.click(btn);
        expect(onMajorChances).toHaveBeenCalledTimes(1);
        expect(onMajorChances).toHaveBeenCalledWith(expect.objectContaining({ university_id: 'uw' }));
    });

    it('is hidden when onMajorChances is not provided', () => {
        render(<UniversityCard university={baseUni} onViewAnalysis={vi.fn()} />);
        expect(screen.queryByRole('button', { name: /view major chances/i })).toBeNull();
    });
});
