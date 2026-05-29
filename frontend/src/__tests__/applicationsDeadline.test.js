/**
 * ApplicationsPage deadline-badge helpers (issue #189).
 *
 * ApplicationsPage previously had its own unguarded getDaysUntil duplicate.
 * It now reuses the shared (Invalid-Date-guarded) getDaysUntil, so daysUntil
 * can be null. These page-specific presentation helpers must handle null
 * gracefully ("Date TBD" / neutral class) rather than showing "Passed" /
 * "urgent" for an unparseable deadline.
 */

import { describe, it, expect } from 'vitest';
import { deadlineUrgencyClass, deadlineDaysLabel } from '../pages/ApplicationsPage';

describe('deadlineDaysLabel', () => {
    it('renders "Date TBD" for null (no parseable date)', () => {
        expect(deadlineDaysLabel(null)).toBe('Date TBD');
    });

    it('renders future / today / passed', () => {
        expect(deadlineDaysLabel(12)).toBe('12 days');
        expect(deadlineDaysLabel(0)).toBe('Today!');
        expect(deadlineDaysLabel(-3)).toBe('Passed');
    });
});

describe('deadlineUrgencyClass', () => {
    it('null maps to a neutral class, not "urgent"', () => {
        expect(deadlineUrgencyClass(null)).toBe('later');
    });

    it('maps day counts to urgent / soon / later', () => {
        expect(deadlineUrgencyClass(3)).toBe('urgent');
        expect(deadlineUrgencyClass(7)).toBe('urgent');
        expect(deadlineUrgencyClass(20)).toBe('soon');
        expect(deadlineUrgencyClass(45)).toBe('later');
    });
});
