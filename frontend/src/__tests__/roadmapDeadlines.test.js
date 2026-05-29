/**
 * roadmapDeadlines — date helpers for the Roadmap "Upcoming Deadlines" list.
 *
 * Regression for issue #187: unparseable due_dates ("Varies", "Rolling", or
 * any non-date string) were producing "NaN days left". getDaysUntil must
 * return null for invalid dates, and deadlineLabel must render "Date TBD"
 * rather than "NaN days left".
 */

// Pin TZ so date-only strings ('YYYY-MM-DD', parsed as UTC) and the local
// "today" agree regardless of the machine/CI timezone.
process.env.TZ = 'UTC';

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { getDaysUntil, getUrgencyColor, deadlineLabel } from '../utils/roadmapDeadlines';

const NOW = new Date('2026-05-28T12:00:00Z');

beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(NOW);
});

afterEach(() => {
    vi.useRealTimers();
});

describe('getDaysUntil', () => {
    it('returns null for empty input', () => {
        expect(getDaysUntil(null)).toBeNull();
        expect(getDaysUntil(undefined)).toBeNull();
        expect(getDaysUntil('')).toBeNull();
    });

    it('returns null for unparseable / free-text dates (no more NaN)', () => {
        expect(getDaysUntil('Varies')).toBeNull();
        expect(getDaysUntil('Rolling')).toBeNull();
        expect(getDaysUntil('not a date')).toBeNull();
    });

    it('returns positive days for a future date', () => {
        expect(getDaysUntil('2026-06-04')).toBe(7);
    });

    it('returns negative days for a past date', () => {
        expect(getDaysUntil('2026-05-21')).toBe(-7);
    });

    it('returns 0 for today', () => {
        expect(getDaysUntil('2026-05-28')).toBe(0);
    });
});

describe('deadlineLabel', () => {
    it('renders "Date TBD" for null (never "NaN days left")', () => {
        expect(deadlineLabel(null)).toBe('Date TBD');
    });

    it('renders overdue / today / tomorrow / future', () => {
        expect(deadlineLabel(-5)).toBe('5d overdue');
        expect(deadlineLabel(0)).toBe('Due today');
        expect(deadlineLabel(1)).toBe('Due tomorrow');
        expect(deadlineLabel(10)).toBe('10 days left');
    });
});

describe('getUrgencyColor', () => {
    it('maps day counts to buckets', () => {
        expect(getUrgencyColor(null)).toBe('stone');
        expect(getUrgencyColor(-1)).toBe('red');
        expect(getUrgencyColor(2)).toBe('red');
        expect(getUrgencyColor(5)).toBe('amber');
        expect(getUrgencyColor(30)).toBe('emerald');
    });
});
