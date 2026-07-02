/**
 * api.js wrappers added for Major Strategy phase 1 (#283):
 *   - setMajorChoice   → POST {PM}/set-major-choice (source:'app', X-User-Email)
 *   - getUniversityMajors → GET {KB}?id&action=majors[&college][&q]
 *   - computeSingleFit → optional intendedMajor adds intended_major to the
 *     body WITHOUT disturbing existing callers or the 402 handling.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('axios', () => {
    const mockAxios = {
        post: vi.fn(),
        get: vi.fn(),
        create: vi.fn(() => ({
            post: vi.fn(),
            get: vi.fn(),
        })),
    };
    return { default: mockAxios };
});

import axios from 'axios';
import {
    setMajorChoice,
    getUniversityMajors,
    computeSingleFit,
    rankCollegeMajors,
    getCollegeMajorChances,
} from '../services/api';

beforeEach(() => {
    axios.post.mockReset();
    axios.get.mockReset();
});

describe('setMajorChoice', () => {
    it('POSTs to /set-major-choice with source:app and the X-User-Email header', async () => {
        axios.post.mockResolvedValue({
            data: { success: true, major_choice: { primary: 'Computer Science', matched: true } },
        });

        const result = await setMajorChoice('s@x.com', 'uw', 'Computer Science');

        expect(axios.post).toHaveBeenCalledTimes(1);
        const [url, body, config] = axios.post.mock.calls[0];
        expect(url).toMatch(/\/set-major-choice$/);
        expect(body).toEqual({
            user_email: 's@x.com',
            university_id: 'uw',
            primary_major: 'Computer Science',
            source: 'app',
        });
        expect(config.headers['X-User-Email']).toBe('s@x.com');
        expect(result.success).toBe(true);
        expect(result.major_choice.matched).toBe(true);
    });

    it('includes backup_major and rationale only when provided', async () => {
        axios.post.mockResolvedValue({ data: { success: true } });

        await setMajorChoice('s@x.com', 'uw', 'CS', { backupMajor: 'Math', rationale: 'strong math record' });

        const body = axios.post.mock.calls[0][1];
        expect(body.backup_major).toBe('Math');
        expect(body.rationale).toBe('strong math record');
    });

    it('surfaces the server error message on failure', async () => {
        axios.post.mockRejectedValue({
            response: { data: { error: 'university not on your college list' } },
            message: 'Request failed with status code 400',
        });

        const result = await setMajorChoice('s@x.com', 'nowhere', 'CS');
        expect(result.success).toBe(false);
        expect(result.error).toBe('university not on your college list');
    });
});

describe('getUniversityMajors', () => {
    it('GETs the KB base URL with id + action=majors', async () => {
        axios.get.mockResolvedValue({ data: { success: true, colleges: [] } });

        const result = await getUniversityMajors('uw');

        expect(axios.get).toHaveBeenCalledTimes(1);
        const [url, config] = axios.get.mock.calls[0];
        expect(url).toBe('http://test-kb.example'); // from setup.js env mocks
        expect(config.params).toEqual({ id: 'uw', action: 'majors' });
        expect(result.success).toBe(true);
    });

    it('passes college and q filters when provided', async () => {
        axios.get.mockResolvedValue({ data: { success: true, colleges: [] } });

        await getUniversityMajors('uw', { college: 'College of Engineering', query: 'bio' });

        const config = axios.get.mock.calls[0][1];
        expect(config.params).toEqual({
            id: 'uw',
            action: 'majors',
            college: 'College of Engineering',
            q: 'bio',
        });
    });

    it('returns success:false with the error on failure', async () => {
        axios.get.mockRejectedValue({ message: 'Network Error' });
        const result = await getUniversityMajors('uw');
        expect(result.success).toBe(false);
        expect(result.error).toBe('Network Error');
    });
});

describe('computeSingleFit — intendedMajor extension', () => {
    it('omits intended_major when not passed (existing callers unchanged)', async () => {
        axios.post.mockResolvedValue({ data: { success: true, fit_analysis: {} } });

        await computeSingleFit('s@x.com', 'uw', false);

        const body = axios.post.mock.calls[0][1];
        expect(body).toEqual({
            user_email: 's@x.com',
            university_id: 'uw',
            force_recompute: false,
        });
        expect(body).not.toHaveProperty('intended_major');
    });

    it('adds intended_major to the body when passed', async () => {
        axios.post.mockResolvedValue({ data: { success: true, fit_analysis: {} } });

        await computeSingleFit('s@x.com', 'uw', true, 'Computer Science');

        const body = axios.post.mock.calls[0][1];
        expect(body.force_recompute).toBe(true);
        expect(body.intended_major).toBe('Computer Science');
    });

    it('keeps the 402 insufficient-credits handling intact', async () => {
        axios.post.mockRejectedValue({
            response: { status: 402, data: { credits_remaining: 0, message: 'need credits' } },
        });

        const result = await computeSingleFit('s@x.com', 'uw', true, 'Computer Science');
        expect(result.success).toBe(false);
        expect(result.insufficientCredits).toBe(true);
        expect(result.error).toBe('insufficient_credits');
        expect(result.creditsRemaining).toBe(0);
    });
});

describe('rankCollegeMajors (#302)', () => {
    it('POSTs to /rank-college-majors with the X-User-Email header', async () => {
        axios.post.mockResolvedValue({ data: { success: true, ranking: { tiers: {} }, gaps: [] } });

        const result = await rankCollegeMajors('s@x.com', 'uw');

        const [url, body, config] = axios.post.mock.calls[0];
        expect(url).toMatch(/\/rank-college-majors$/);
        expect(body).toEqual({ user_email: 's@x.com', university_id: 'uw' });
        expect(config.headers['X-User-Email']).toBe('s@x.com');
        expect(result.success).toBe(true);
    });

    it('maps a 402 to insufficientCredits (server-billed; no client deduct)', async () => {
        axios.post.mockRejectedValue({
            response: { status: 402, data: { credits_remaining: 1 } },
        });
        const result = await rankCollegeMajors('s@x.com', 'uw');
        expect(result.success).toBe(false);
        expect(result.insufficientCredits).toBe(true);
        expect(result.creditsRemaining).toBe(1);
    });

    it('passes the never-charged KB miss through untouched', async () => {
        axios.post.mockResolvedValue({
            data: { success: true, ranking: null, gaps: ['Computer Science'], note: 'no data' },
        });
        const result = await rankCollegeMajors('s@x.com', 'uw');
        expect(result.success).toBe(true);
        expect(result.ranking).toBeNull();
        expect(result.gaps).toEqual(['Computer Science']);
    });
});

describe('getCollegeMajorChances (#302)', () => {
    it('GETs /get-college-major-chances with user_email + university_id params', async () => {
        axios.get.mockResolvedValue({
            data: { success: true, ranking: { tiers: {} }, stale: false, current_kb_year: 2026 },
        });

        const result = await getCollegeMajorChances('s@x.com', 'uw');

        const [url, config] = axios.get.mock.calls[0];
        expect(url).toMatch(/\/get-college-major-chances$/);
        expect(config.params).toEqual({ user_email: 's@x.com', university_id: 'uw' });
        expect(config.headers['X-User-Email']).toBe('s@x.com');
        expect(result.success).toBe(true);
        expect(result.current_kb_year).toBe(2026);
    });

    it('returns success:false with the error on failure', async () => {
        axios.get.mockRejectedValue({ message: 'Network Error' });
        const result = await getCollegeMajorChances('s@x.com', 'uw');
        expect(result.success).toBe(false);
        expect(result.error).toBe('Network Error');
    });
});
