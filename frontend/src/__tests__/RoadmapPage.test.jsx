/**
 * Tests for the RoadmapPage tab strip — URL-synced active-tab state, default
 * tab fallback, and that the right tab content mounts.
 *
 * Heavy children (PlanTab's roadmap fetch, EssayDashboard, etc.) are mocked
 * so the test stays focused on the tab switcher rather than the whole tree.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route, useLocation } from 'react-router-dom';

// Mock all the heavy children with simple sentinels we can assert on.
vi.mock('../components/counselor/RoadmapView', () => ({
    default: () => <div data-testid="roadmap-view" />,
}));
vi.mock('../components/roadmap/ThisWeekFocusCard', () => ({
    default: () => <div data-testid="focus-card" />,
}));
vi.mock('../components/roadmap/FloatingCounselorChat', () => ({
    default: () => <div data-testid="floating-chat" />,
}));
vi.mock('../components/roadmap/AddTaskModal', () => ({
    default: ({ isOpen }) => (isOpen ? <div data-testid="add-task-modal" /> : null),
}));
vi.mock('../pages/EssayDashboard', () => ({
    default: () => <div data-testid="essays-tab" />,
}));
vi.mock('../pages/ScholarshipTracker', () => ({
    default: () => <div data-testid="scholarships-tab" />,
}));
vi.mock('../pages/ApplicationsPage', () => ({
    default: () => <div data-testid="colleges-tab" />,
}));
vi.mock('../services/api', () => ({
    fetchStudentRoadmap: vi.fn().mockResolvedValue({ success: true, roadmap: { phases: [] } }),
    fetchUserProfile: vi.fn().mockResolvedValue({ profile: { grade: '11th Grade' } }),
}));

import RoadmapPage from '../pages/RoadmapPage';

// Renders RoadmapPage and exposes the current router location via a sentinel
// element, so tests can assert on URL changes without depending on
// `window.location` (which MemoryRouter doesn't update — its history is
// in-memory only).
const LocationProbe = () => {
    const loc = useLocation();
    return <span data-testid="probe-location">{loc.pathname + loc.search}</span>;
};

const renderAt = (path) => render(
    <MemoryRouter initialEntries={[path]}>
        <LocationProbe />
        <Routes>
            <Route path="/roadmap" element={<RoadmapPage />} />
        </Routes>
    </MemoryRouter>,
);

describe('RoadmapPage', () => {
    beforeEach(() => {
        // Each test starts on a clean URL.
    });

    it('defaults to the Plan tab when no ?tab= is set', async () => {
        renderAt('/roadmap');
        await waitFor(() => expect(screen.getByTestId('focus-card')).toBeInTheDocument());
        // Plan is the only tab whose content includes the focus card.
        expect(screen.queryByTestId('essays-tab')).not.toBeInTheDocument();
    });

    it('honors ?tab=essays', async () => {
        renderAt('/roadmap?tab=essays');
        expect(await screen.findByTestId('essays-tab')).toBeInTheDocument();
        expect(screen.queryByTestId('focus-card')).not.toBeInTheDocument();
    });

    it('honors ?tab=scholarships', async () => {
        renderAt('/roadmap?tab=scholarships');
        expect(await screen.findByTestId('scholarships-tab')).toBeInTheDocument();
    });

    it('honors ?tab=colleges', async () => {
        renderAt('/roadmap?tab=colleges');
        expect(await screen.findByTestId('colleges-tab')).toBeInTheDocument();
    });

    it('falls back to Plan tab when ?tab= is unknown', async () => {
        renderAt('/roadmap?tab=garbage');
        await waitFor(() => expect(screen.getByTestId('focus-card')).toBeInTheDocument());
    });

    it('switches tabs and updates the URL when a tab is clicked', async () => {
        const user = userEvent.setup();
        renderAt('/roadmap');
        await waitFor(() => expect(screen.getByTestId('focus-card')).toBeInTheDocument());

        await user.click(screen.getByRole('button', { name: /^essays/i }));

        expect(await screen.findByTestId('essays-tab')).toBeInTheDocument();
        expect(screen.getByTestId('probe-location').textContent).toContain('tab=essays');
    });

    it('renders the floating chat across all tabs', async () => {
        renderAt('/roadmap?tab=colleges');
        expect(await screen.findByTestId('floating-chat')).toBeInTheDocument();
    });

    it('Plan tab shows an "Add task" button that opens the modal', async () => {
        const user = userEvent.setup();
        renderAt('/roadmap');
        await waitFor(() => expect(screen.getByTestId('focus-card')).toBeInTheDocument());

        const addButton = screen.getByRole('button', { name: /add task/i });
        await user.click(addButton);

        expect(await screen.findByTestId('add-task-modal')).toBeInTheDocument();
    });
});
