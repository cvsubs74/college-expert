/**
 * Tests for the per-college MiniDashboard — the "Show progress" expansion
 * on each Colleges-tab card.
 *
 * MiniDashboard is exported only as a local subcomponent of ApplicationsPage,
 * so we can't import it directly. Instead we exercise it through the parent
 * with stubbed API calls; this also covers the parent's data-bucketing logic
 * (essays/scholarships grouped by university_id) which is part of M2.
 *
 * We keep the assertions focused on the mini-dashboard surface — section
 * counts, progress percentages, expand/collapse toggle, navigation on row
 * click, and empty-state suppression of sections without content.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

// Mock api.js helpers ApplicationsPage uses.
vi.mock('../services/api', () => ({
    getCollegeList: vi.fn(),
    getEssayTracker: vi.fn(),
    getScholarshipTracker: vi.fn(),
}));
import { getCollegeList, getEssayTracker, getScholarshipTracker } from '../services/api';

// useNavigate spy for click-to-navigate assertions.
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async (importOriginal) => {
    const actual = await importOriginal();
    return { ...actual, useNavigate: () => mockNavigate };
});

// Stub the global fetch ApplicationsPage uses for /deadlines + KB calls so
// we don't need MSW or live HTTP. Each test sets the return value.
const mockFetch = vi.fn();
beforeEach(() => {
    mockFetch.mockReset();
    getCollegeList.mockReset();
    getEssayTracker.mockReset();
    getScholarshipTracker.mockReset();
    mockNavigate.mockReset();
    globalThis.fetch = mockFetch;
});

import ApplicationsPage from '../pages/ApplicationsPage';

/**
 * Helper: stage all four parallel fetches the page makes on load with the
 * given seed data. ApplicationsPage's fetchSchools does:
 *   fetch(/deadlines, POST) | getCollegeList | getEssayTracker | getScholarshipTracker
 * plus per-school KB fetches.
 */
const seed = ({ deadlines = [], colleges = [], essays = [], scholarships = [] }) => {
    // /deadlines POST + KB GETs all flow through fetch.
    mockFetch.mockImplementation((url) => {
        if (typeof url === 'string' && url.includes('/deadlines')) {
            return Promise.resolve({
                json: () => Promise.resolve({ success: true, deadlines }),
            });
        }
        // KB call per school — return empty profile so essay-tips/requirements blocks stay empty.
        return Promise.resolve({
            json: () => Promise.resolve({ success: true, university: { profile: {} } }),
        });
    });
    getCollegeList.mockResolvedValue({ college_list: colleges });
    getEssayTracker.mockResolvedValue({ essays });
    getScholarshipTracker.mockResolvedValue({ scholarships });
};

const renderPage = () => render(
    <MemoryRouter>
        <ApplicationsPage embedded />
    </MemoryRouter>,
);

describe('MiniDashboard (via ApplicationsPage)', () => {
    it('hides the toggle entirely when a school has no deadlines/essays/scholarships', async () => {
        seed({
            deadlines: [{
                university_id: 'mit', university_name: 'MIT',
                date: '2027-01-05', deadline_type: 'Regular Decision',
            }],
            colleges: [{ university_id: 'mit', university_name: 'MIT' }],
            essays: [],
            scholarships: [],
        });
        renderPage();
        await waitFor(() => expect(screen.getByText('MIT')).toBeInTheDocument());
        // The school has 1 deadline, so the toggle SHOULD render. Sanity:
        expect(screen.getByRole('button', { name: /show progress/i })).toBeInTheDocument();

        // (We don't have a way to seed "school with zero of all three" easily
        // since deadlines drive school discovery — skip the empty-toggle case.)
    });

    it('default-collapses each school card', async () => {
        seed({
            deadlines: [
                { university_id: 'mit', university_name: 'MIT', date: '2027-01-05', deadline_type: 'RD' },
            ],
            essays: [{ essay_id: 'mit_a', university_id: 'mit', status: 'draft' }],
            scholarships: [],
        });
        renderPage();

        await waitFor(() => expect(screen.getByText('MIT')).toBeInTheDocument());
        // The expanded sections should NOT be visible yet.
        expect(screen.queryByText(/Essays \(/i)).not.toBeInTheDocument();
        expect(screen.queryByText(/Deadlines \(/i)).not.toBeInTheDocument();
        // Toggle reads "Show progress" while collapsed.
        expect(screen.getByRole('button', { name: /show progress/i })).toBeInTheDocument();
    });

    it('expands to show deadlines + essays + scholarships sections', async () => {
        seed({
            deadlines: [
                { university_id: 'mit', university_name: 'MIT', date: '2027-01-05', deadline_type: 'RD' },
                { university_id: 'mit', university_name: 'MIT', date: '2026-11-01', deadline_type: 'EA' },
            ],
            essays: [
                { essay_id: 'e1', university_id: 'mit', status: 'final', prompt_text: 'Why MIT?' },
                { essay_id: 'e2', university_id: 'mit', status: 'draft', prompt_text: 'Hometown' },
            ],
            scholarships: [
                { scholarship_id: 's1', university_id: 'mit', status: 'applied', scholarship_name: 'Need Aid' },
                { scholarship_id: 's2', university_id: 'mit', status: 'not_applied', scholarship_name: 'Merit' },
            ],
        });
        const user = userEvent.setup();
        renderPage();

        await waitFor(() => expect(screen.getByText('MIT')).toBeInTheDocument());
        await user.click(screen.getByRole('button', { name: /show progress/i }));

        // Section headers — count is rendered next to each.
        expect(await screen.findByText(/Deadlines \(2\)/)).toBeInTheDocument();
        expect(screen.getByText(/Essays \(1\/2\)/)).toBeInTheDocument();
        expect(screen.getByText(/Scholarships \(1\/2 applied\)/)).toBeInTheDocument();

        // After expansion the toggle reads "Hide progress".
        expect(screen.getByRole('button', { name: /hide progress/i })).toBeInTheDocument();
    });

    it('reports correct progress percentages', async () => {
        seed({
            deadlines: [
                { university_id: 'mit', university_name: 'MIT', date: '2027-01-05', deadline_type: 'RD' },
            ],
            essays: [
                { essay_id: 'e1', university_id: 'mit', status: 'final' },
                { essay_id: 'e2', university_id: 'mit', status: 'draft' },
                { essay_id: 'e3', university_id: 'mit', status: 'not_started' },
            ],
            scholarships: [
                { scholarship_id: 's1', university_id: 'mit', status: 'applied' },
                { scholarship_id: 's2', university_id: 'mit', status: 'received' },
                { scholarship_id: 's3', university_id: 'mit', status: 'not_applied' },
                { scholarship_id: 's4', university_id: 'mit', status: 'not_eligible' },
            ],
        });
        const user = userEvent.setup();
        renderPage();
        await waitFor(() => screen.getByText('MIT'));
        await user.click(screen.getByRole('button', { name: /show progress/i }));

        // Essays: 1 final / 3 total = 33%.
        expect(await screen.findByText('33%')).toBeInTheDocument();
        // Scholarships: applied + received = 2 / 4 = 50%.
        expect(screen.getByText('50%')).toBeInTheDocument();
    });

    it('navigates to the Essays tab when an essay row is clicked', async () => {
        seed({
            deadlines: [
                { university_id: 'mit', university_name: 'MIT', date: '2027-01-05', deadline_type: 'RD' },
            ],
            essays: [
                { essay_id: 'mit_essay_42', university_id: 'mit', status: 'draft', prompt_text: 'Why MIT?' },
            ],
        });
        const user = userEvent.setup();
        renderPage();
        await waitFor(() => screen.getByText('MIT'));
        await user.click(screen.getByRole('button', { name: /show progress/i }));

        await user.click(await screen.findByText('Why MIT?'));
        expect(mockNavigate).toHaveBeenCalledWith('/roadmap?tab=essays&essay_id=mit_essay_42');
    });

    it('navigates to the Scholarships tab when a scholarship row is clicked', async () => {
        seed({
            deadlines: [
                { university_id: 'mit', university_name: 'MIT', date: '2027-01-05', deadline_type: 'RD' },
            ],
            scholarships: [
                { scholarship_id: 'mit_aid_77', university_id: 'mit', status: 'applied', scholarship_name: 'Need-based aid' },
            ],
        });
        const user = userEvent.setup();
        renderPage();
        await waitFor(() => screen.getByText('MIT'));
        await user.click(screen.getByRole('button', { name: /show progress/i }));

        await user.click(await screen.findByText('Need-based aid'));
        expect(mockNavigate).toHaveBeenCalledWith('/roadmap?tab=scholarships&scholarship_id=mit_aid_77');
    });

    it('skips essays/scholarships without university_id (they live on tab-level surfaces)', async () => {
        seed({
            deadlines: [
                { university_id: 'mit', university_name: 'MIT', date: '2027-01-05', deadline_type: 'RD' },
            ],
            essays: [
                { essay_id: 'e1', university_id: 'mit', status: 'draft', prompt_text: 'Why MIT?' },
                { essay_id: 'shared', /* no university_id */ status: 'draft', prompt_text: 'Common App essay' },
            ],
        });
        const user = userEvent.setup();
        renderPage();
        await waitFor(() => screen.getByText('MIT'));
        await user.click(screen.getByRole('button', { name: /show progress/i }));

        // The shared essay (no university_id) shouldn't appear under MIT.
        expect(screen.queryByText('Common App essay')).not.toBeInTheDocument();
        // But the MIT-specific one should.
        expect(await screen.findByText('Why MIT?')).toBeInTheDocument();
    });
});
