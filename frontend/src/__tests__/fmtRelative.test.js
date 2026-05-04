/**
 * fmtRelative(isoString) — short relative-time string suitable for
 * dashboard cards ("just now", "5m ago", "3h ago", "2d ago").
 *
 * Previously duplicated inline across CoverageCard, ResolvedIssuesCard,
 * and UniversitiesCard. Consolidated into a shared util.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { fmtRelative } from '../utils/fmtRelative';

const NOW = new Date('2026-05-04T12:00:00Z');

beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(NOW);
});

afterEach(() => {
    vi.useRealTimers();
});

describe('fmtRelative', () => {
    it('returns "just now" for the current minute', () => {
        expect(fmtRelative('2026-05-04T11:59:30Z')).toBe('just now');
    });

    it('returns minutes ago for the last hour', () => {
        expect(fmtRelative('2026-05-04T11:55:00Z')).toBe('5m ago');
        expect(fmtRelative('2026-05-04T11:01:00Z')).toBe('59m ago');
    });

    it('returns hours ago for the last day', () => {
        expect(fmtRelative('2026-05-04T09:00:00Z')).toBe('3h ago');
        expect(fmtRelative('2026-05-03T13:00:00Z')).toBe('23h ago');
    });

    it('returns days ago beyond 24h', () => {
        expect(fmtRelative('2026-05-02T12:00:00Z')).toBe('2d ago');
        expect(fmtRelative('2026-04-27T12:00:00Z')).toBe('7d ago');
    });

    it('returns empty string for missing / falsy input', () => {
        expect(fmtRelative('')).toBe('');
        expect(fmtRelative(null)).toBe('');
        expect(fmtRelative(undefined)).toBe('');
    });

    it('returns empty string for invalid date strings', () => {
        // Don't crash on bad data from Firestore round-trips.
        expect(fmtRelative('not-a-date')).toBe('');
    });
});
