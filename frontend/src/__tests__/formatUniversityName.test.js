/**
 * formatUniversityName(id) — turn a canonical college ID into a
 * human-readable label. Hybrid lookup + auto-prettify.
 *
 * Spec: docs/prd/qa-university-friendly-labels.md +
 *       docs/design/qa-university-friendly-labels.md.
 */

import { describe, it, expect } from 'vitest';
import { formatUniversityName } from '../utils/formatUniversityName';

describe('formatUniversityName', () => {
    it('returns the override for known schools', () => {
        expect(formatUniversityName('massachusetts_institute_of_technology'))
            .toBe('MIT');
        expect(formatUniversityName('university_of_california_berkeley'))
            .toBe('UC Berkeley');
        expect(formatUniversityName('university_of_california_los_angeles'))
            .toBe('UCLA');
        expect(formatUniversityName('georgia_institute_of_technology'))
            .toBe('Georgia Tech');
        expect(formatUniversityName('carnegie_mellon_university'))
            .toBe('Carnegie Mellon');
    });

    it('handles legacy short-form aliases gracefully', () => {
        // Even though the backend canonicalizes these, a stray legacy
        // record shouldn't render as bare "mit" or "ucla".
        expect(formatUniversityName('mit')).toBe('MIT');
        expect(formatUniversityName('ucla')).toBe('UCLA');
    });

    it('auto-prettifies unknown ids by underscore→space + titlecase', () => {
        expect(formatUniversityName('tufts_university')).toBe('Tufts University');
        expect(formatUniversityName('boston_college')).toBe('Boston College');
        expect(formatUniversityName('rice_university')).toBe('Rice University');
        // Also handles a brand new school ID we haven't seen yet.
        expect(formatUniversityName('new_school_xyz')).toBe('New School Xyz');
    });

    it('returns empty string for falsy input', () => {
        expect(formatUniversityName('')).toBe('');
        expect(formatUniversityName(null)).toBe('');
        expect(formatUniversityName(undefined)).toBe('');
    });

    it('does not mutate already-pretty input', () => {
        // If someone passes a pre-formatted name, we shouldn't double-process.
        // Default behavior for "MIT" with no underscores → titlecase pass = "MIT".
        expect(formatUniversityName('MIT')).toBe('MIT');
    });
});
