/**
 * ExecutiveSummary renders the headline narrative + 7d/30d pass rates
 * + per-surface health badges. Fetches the summary from qa-agent's
 * GET /summary on mount.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';

const summaryFn = vi.fn();
vi.mock('../services/qaAgent', () => ({
    getSummary: (...args) => summaryFn(...args),
}));

import ExecutiveSummary from '../components/qa/ExecutiveSummary';

beforeEach(() => {
    summaryFn.mockReset();
});

describe('ExecutiveSummary', () => {
    it('shows a loading state initially', () => {
        summaryFn.mockReturnValue(new Promise(() => {})); // never resolves
        render(<ExecutiveSummary />);
        expect(screen.getByText(/loading/i)).toBeInTheDocument();
    });

    it('renders pass rates and narrative once summary loads', async () => {
        summaryFn.mockResolvedValue({
            success: true,
            summary: {
                narrative: 'All systems green for 18 of the last 21 days.',
                pass_rate_7d: 100,
                pass_rate_30d: 95,
                trend: 'improving',
                surfaces: {
                    profile: { total: 10, fails: 0, status: 'green' },
                    roadmap: { total: 10, fails: 1, status: 'yellow' },
                },
            },
        });
        render(<ExecutiveSummary />);
        await waitFor(() => {
            expect(screen.getByText(/All systems green/i)).toBeInTheDocument();
        });
        expect(screen.getByText(/100%/)).toBeInTheDocument();
        expect(screen.getByText(/95%/)).toBeInTheDocument();
        expect(screen.getByText(/profile/i)).toBeInTheDocument();
        expect(screen.getByText(/roadmap/i)).toBeInTheDocument();
    });

    it('renders an error message on fetch failure', async () => {
        summaryFn.mockRejectedValue(new Error('boom'));
        render(<ExecutiveSummary />);
        await waitFor(() => {
            expect(screen.getByText(/couldn't load summary|boom/i)).toBeInTheDocument();
        });
    });
});
