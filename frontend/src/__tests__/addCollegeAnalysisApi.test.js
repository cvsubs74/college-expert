/**
 * addCollegeAnalysis (#310): the bundled add-to-Launchpad call — ONE credit
 * generates BOTH the fit analysis and the major chances, server-billed. Pins the
 * request shape, the force flag, and the 402 / 503 handling (no client deduct).
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('axios', () => {
  const mockAxios = {
    post: vi.fn(),
    get: vi.fn(),
    create: vi.fn(() => ({ post: vi.fn(), get: vi.fn() })),
  };
  return { default: mockAxios };
});

import axios from 'axios';
import { addCollegeAnalysis } from '../services/api';

beforeEach(() => {
  axios.post.mockReset();
});

describe('addCollegeAnalysis (#310)', () => {
  it('POSTs to /add-college-analysis with the bundle body + X-User-Email header', async () => {
    axios.post.mockResolvedValue({
      data: { success: true, fit_analysis: { fit_category: 'TARGET' },
              major_chances: { tiers: {} }, credits_remaining: 4 },
    });

    const result = await addCollegeAnalysis('s@x.com', 'uw');

    expect(axios.post).toHaveBeenCalledTimes(1);
    const [url, body, config] = axios.post.mock.calls[0];
    expect(url).toMatch(/\/add-college-analysis$/);
    expect(body).toEqual({ user_email: 's@x.com', university_id: 'uw', force: false });
    expect(config.headers['X-User-Email']).toBe('s@x.com');
    // Both artifacts come back.
    expect(result.success).toBe(true);
    expect(result.fit_analysis.fit_category).toBe('TARGET');
    expect(result.major_chances).toEqual({ tiers: {} });
  });

  it('passes force=true for the card regenerate', async () => {
    axios.post.mockResolvedValue({ data: { success: true, fit_analysis: {}, major_chances: null } });
    await addCollegeAnalysis('s@x.com', 'uw', true);
    expect(axios.post.mock.calls[0][1].force).toBe(true);
  });

  it('maps a 402 to insufficientCredits (server-billed; never client-deducted)', async () => {
    axios.post.mockRejectedValue({
      response: { status: 402, data: { credits_remaining: 0, message: 'need credits' } },
    });
    const result = await addCollegeAnalysis('s@x.com', 'uw');
    expect(result.success).toBe(false);
    expect(result.insufficientCredits).toBe(true);
    expect(result.error).toBe('insufficient_credits');
    expect(result.creditsRemaining).toBe(0);
  });

  it('maps a 503 credits-read blip to a retryable error (not the upsell)', async () => {
    axios.post.mockRejectedValue({ response: { status: 503, data: {} } });
    const result = await addCollegeAnalysis('s@x.com', 'uw');
    expect(result.success).toBe(false);
    expect(result.retryable).toBe(true);
    expect(result.insufficientCredits).toBeUndefined();
  });

  it('passes a KB-majors miss through untouched (chances null + note, not a failure)', async () => {
    axios.post.mockResolvedValue({
      data: { success: true, fit_analysis: { fit_category: 'REACH' },
              major_chances: null, note: 'no major data yet' },
    });
    const result = await addCollegeAnalysis('s@x.com', 'uw');
    expect(result.success).toBe(true);
    expect(result.major_chances).toBeNull();
    expect(result.note).toMatch(/no major data/);
  });
});
