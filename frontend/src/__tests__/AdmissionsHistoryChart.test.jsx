/**
 * AdmissionsHistoryChart (#286) — the AdmissionsTab acceptance-rate chart,
 * now fed by the KB's `action=history` two-axis view.
 *
 * These tests pin the honesty rules:
 *   - TWO labeled groups (KB snapshots vs school-reported), never merged
 *   - vintage_estimated rows get an "estimated year" marker
 *   - school-reported group is explicitly captioned unverified/different axis
 *   - selectivity indicator computed within ONE series only (reported ≥2,
 *     else snapshots ≥2, never across)
 *   - 1 total row → plain stat + "history builds up" note, no chart groups
 *   - history fetch failure → old longitudinal_trends fallback rendering
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';

vi.mock('../services/api', () => ({
    getUniversityHistory: vi.fn(),
}));
import { getUniversityHistory } from '../services/api';
import AdmissionsHistoryChart from '../components/UniversityProfilePage/AdmissionsHistoryChart';

const HISTORY = {
    success: true,
    university_id: 'testu',
    official_name: 'Test University',
    available_years: [2025, 2026],
    snapshots: [
        { year: 2026, cycle_label: '2026–27', source: 'kb_snapshot', vintage_estimated: false, acceptance_rate: 25.0 },
        { year: 2025, cycle_label: '2025–26', source: 'kb_snapshot', vintage_estimated: true, acceptance_rate: 30.0 },
    ],
    reported_trends: [
        { year: 2024, cycle_name: 'Class of 2028', acceptance_rate_overall: 6.0, source: 'profile_trend', verified: false },
        { year: 2023, cycle_name: 'Class of 2027', acceptance_rate_overall: 6.6, source: 'profile_trend', verified: false },
    ],
    notes: [],
};

const LEGACY_TRENDS = [
    { year: 2024, acceptance_rate_overall: 0.48 },
    { year: 2023, acceptance_rate_overall: 0.52 },
];

beforeEach(() => {
    getUniversityHistory.mockReset();
});

const renderChart = (props = {}) =>
    render(<AdmissionsHistoryChart universityId="testu" fallbackTrends={[]} {...props} />);

describe('AdmissionsHistoryChart — states', () => {
    it('shows a loading placeholder while fetching', () => {
        getUniversityHistory.mockReturnValue(new Promise(() => { })); // never resolves
        renderChart();
        expect(screen.getByTestId('history-loading')).toBeInTheDocument();
        expect(getUniversityHistory).toHaveBeenCalledWith('testu');
    });

    it('renders two labeled groups from the history payload — never merged', async () => {
        getUniversityHistory.mockResolvedValue(HISTORY);
        renderChart();

        expect(await screen.findByText('Stratia KB snapshots')).toBeInTheDocument();
        expect(screen.getByText('School-reported (unverified)')).toBeInTheDocument();

        // Snapshot bars labeled by cycle, reported bars by entering-class year.
        expect(screen.getByText('2026–27')).toBeInTheDocument();
        expect(screen.getByText('2025–26')).toBeInTheDocument();
        expect(screen.getByText('25.0%')).toBeInTheDocument();
        expect(screen.getByText('30.0%')).toBeInTheDocument();
        expect(screen.getByText('2024')).toBeInTheDocument();
        expect(screen.getByText('2023')).toBeInTheDocument();
        expect(screen.getByText('6.0%')).toBeInTheDocument();
        expect(screen.getByText('6.6%')).toBeInTheDocument();

        // Explicit different-axis / unverified caption on the reported group.
        expect(screen.getByText(/different year axis \(entering class\)/i)).toBeInTheDocument();
        expect(screen.getByText(/not verified by Stratia/i)).toBeInTheDocument();
    });

    it('marks vintage_estimated snapshot rows with an "estimated year" marker', async () => {
        getUniversityHistory.mockResolvedValue(HISTORY);
        renderChart();
        await screen.findByText('Stratia KB snapshots');
        // Exactly one: only the 2025 row is vintage_estimated.
        expect(screen.getAllByText('estimated year')).toHaveLength(1);
    });

    it('renders a single total row as a plain stat with the builds-up note', async () => {
        getUniversityHistory.mockResolvedValue({
            ...HISTORY,
            snapshots: [HISTORY.snapshots[0]],
            reported_trends: [],
        });
        renderChart();

        expect(await screen.findByText('25.0%')).toBeInTheDocument();
        expect(screen.getByText(/2026–27 cycle \(Stratia KB\)/)).toBeInTheDocument();
        expect(screen.getByText(/year-over-year history builds up each admission cycle/i)).toBeInTheDocument();
        expect(screen.queryByText('Stratia KB snapshots')).toBeNull();
        expect(screen.queryByText('School-reported (unverified)')).toBeNull();
    });

    it('falls back to the legacy longitudinal_trends chart when the fetch fails', async () => {
        getUniversityHistory.mockResolvedValue({ success: false, error: 'kb unreachable' });
        renderChart({ fallbackTrends: LEGACY_TRENDS });

        // Legacy path normalizes decimals (0.48 → 48.0%).
        expect(await screen.findByText('48.0%')).toBeInTheDocument();
        expect(screen.getByText('52.0%')).toBeInTheDocument();
        expect(screen.queryByText('Stratia KB snapshots')).toBeNull();
        expect(screen.queryByText('School-reported (unverified)')).toBeNull();
    });

    it('falls back to the legacy chart when the api call rejects', async () => {
        getUniversityHistory.mockRejectedValue(new Error('network down'));
        renderChart({ fallbackTrends: LEGACY_TRENDS });
        expect(await screen.findByText('48.0%')).toBeInTheDocument();
    });

    it('renders nothing when the fetch fails and there are no fallback trends', async () => {
        getUniversityHistory.mockResolvedValue({ success: false, error: 'nope' });
        const { container } = renderChart({ fallbackTrends: [] });
        await waitFor(() => expect(container.innerHTML).toBe(''));
    });
});

describe('AdmissionsHistoryChart — selectivity indicator (single-series only)', () => {
    it('computes from reported_trends when it has ≥2 rows', async () => {
        getUniversityHistory.mockResolvedValue(HISTORY);
        renderChart();

        expect(await screen.findByText('Getting more selective')).toBeInTheDocument();
        // 6.0 - 6.6 = -0.6 across the school-reported series.
        expect(screen.getByText(/-0\.6% across 2 school-reported years/)).toBeInTheDocument();
    });

    it('computes from snapshots when reported_trends has <2 rows', async () => {
        getUniversityHistory.mockResolvedValue({ ...HISTORY, reported_trends: [] });
        renderChart();

        expect(await screen.findByText('Getting more selective')).toBeInTheDocument();
        // 25.0 - 30.0 = -5.0 across the KB cycle series.
        expect(screen.getByText(/-5\.0% across 2 KB cycles/)).toBeInTheDocument();
    });

    it('never computes across the two series (1 snapshot + 1 reported row)', async () => {
        getUniversityHistory.mockResolvedValue({
            ...HISTORY,
            snapshots: [HISTORY.snapshots[0]],
            reported_trends: [HISTORY.reported_trends[0]],
        });
        renderChart();

        // Both groups render (2 total rows) but no cross-series delta.
        expect(await screen.findByText('Stratia KB snapshots')).toBeInTheDocument();
        expect(screen.getByText('School-reported (unverified)')).toBeInTheDocument();
        expect(screen.queryByText(/getting (more|less) selective/i)).toBeNull();
    });
});
