/**
 * ExecutiveSummary renders the headline narrative + 7d/30d pass rates
 * + per-surface health badges. Fetches the summary from qa-agent's
 * GET /summary on mount.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';

const summaryFn = vi.fn();
const getPrefsFn = vi.fn();
const savePrefsFn = vi.fn();
vi.mock('../services/qaAgent', () => ({
    getSummary: (...args) => summaryFn(...args),
    getDashboardPrefs: (...args) => getPrefsFn(...args),
    saveDashboardPrefs: (...args) => savePrefsFn(...args),
}));

import ExecutiveSummary from '../components/qa/ExecutiveSummary';
import userEvent from '@testing-library/user-event';

beforeEach(() => {
    summaryFn.mockReset();
    getPrefsFn.mockReset();
    savePrefsFn.mockReset();
    // Sane defaults so tests that don't care don't have to mock these.
    getPrefsFn.mockResolvedValue({ success: true, prefs: { recent_n: 20 } });
    savePrefsFn.mockResolvedValue({ success: true });
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
                pass_rate_recent: 100,
                recent_n: 20,
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
        // Recent + 7d are both 100, so 100% appears twice.
        expect(screen.getAllByText(/100%/).length).toBeGreaterThanOrEqual(1);
        expect(screen.getByText(/95%/)).toBeInTheDocument();
        expect(screen.getByText(/profile/i)).toBeInTheDocument();
        expect(screen.getByText(/roadmap/i)).toBeInTheDocument();
    });

    it('shows the recent-N pill as PRIMARY when present', async () => {
        summaryFn.mockResolvedValue({
            success: true,
            summary: {
                narrative: 'recent runs all green',
                pass_rate_recent: 100,
                recent_n: 20,
                pass_rate_7d: 80,    // would be visually loud if it were primary
                pass_rate_30d: 60,
                trend: 'improving',
                surfaces: {},
            },
        });
        render(<ExecutiveSummary />);
        await waitFor(() => {
            expect(screen.getByText(/recent runs all green/i)).toBeInTheDocument();
        });
        // The recent-N pill should be displayed (100%); both 7d/30d should
        // also appear but as secondary numbers.
        expect(screen.getByText('100%')).toBeInTheDocument();
        expect(screen.getByText('80%')).toBeInTheDocument();
        expect(screen.getByText('60%')).toBeInTheDocument();
        // The N selector should reflect the loaded value.
        const select = screen.getByLabelText(/Number of recent runs/i);
        expect(select).toHaveValue('20');
    });

    it('refetches summary with the new N when the user changes the selector', async () => {
        summaryFn.mockResolvedValue({
            success: true,
            summary: {
                narrative: 'ok',
                pass_rate_recent: 100,
                recent_n: 20,
                pass_rate_7d: 100,
                pass_rate_30d: 100,
                trend: 'steady',
                surfaces: {},
            },
        });
        const user = userEvent.setup();
        render(<ExecutiveSummary />);
        await waitFor(() => {
            expect(screen.getByText(/ok/i)).toBeInTheDocument();
        });
        // Pick N=50.
        await user.selectOptions(
            screen.getByLabelText(/Number of recent runs/i),
            '50',
        );
        // Summary refetch is called with recentN=50.
        await waitFor(() => {
            const calls = summaryFn.mock.calls;
            expect(calls.some((c) => c[0]?.recentN === 50)).toBe(true);
        });
        // Saved prefs round-trip the new value.
        await waitFor(() => {
            expect(savePrefsFn).toHaveBeenCalledWith({ recent_n: 50 });
        });
    });

    it('uses recent_n from saved prefs on initial load', async () => {
        getPrefsFn.mockResolvedValue({ success: true, prefs: { recent_n: 50 } });
        summaryFn.mockResolvedValue({
            success: true,
            summary: {
                narrative: 'ok',
                pass_rate_recent: 100,
                recent_n: 50,
                pass_rate_7d: null,
                pass_rate_30d: null,
                trend: 'steady',
                surfaces: {},
            },
        });
        render(<ExecutiveSummary />);
        await waitFor(() => {
            // First fetch should already have used the loaded N=50.
            const seen = summaryFn.mock.calls.map((c) => c[0]?.recentN);
            expect(seen).toContain(50);
        });
    });

    it('renders an error message on fetch failure', async () => {
        summaryFn.mockRejectedValue(new Error('boom'));
        render(<ExecutiveSummary />);
        await waitFor(() => {
            expect(screen.getByText(/couldn't load summary|boom/i)).toBeInTheDocument();
        });
    });
});
