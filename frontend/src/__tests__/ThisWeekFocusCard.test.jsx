/**
 * Tests for ThisWeekFocusCard — the Plan-tab focus list that aggregates
 * urgent items from /work-feed.
 *
 * The component owns three meaningful states (loading, empty, populated)
 * plus the source-icon / urgency-badge / deep-link-navigation behavior.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

import ThisWeekFocusCard from '../components/roadmap/ThisWeekFocusCard';

vi.mock('../services/api', () => ({
    fetchWorkFeed: vi.fn(),
}));
import { fetchWorkFeed } from '../services/api';

// Stub useNavigate so we can assert on the navigate target. We can't use
// the real navigate without a live route, and even with MemoryRouter the
// navigate side effect is best asserted directly.
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async (importOriginal) => {
    const actual = await importOriginal();
    return {
        ...actual,
        useNavigate: () => mockNavigate,
    };
});

beforeEach(() => {
    fetchWorkFeed.mockReset();
    mockNavigate.mockReset();
});

const renderCard = (props = {}) => render(
    <MemoryRouter>
        <ThisWeekFocusCard userEmail="test.user@example.com" {...props} />
    </MemoryRouter>,
);

describe('ThisWeekFocusCard', () => {
    it('shows the loading skeleton while the fetch is in flight', () => {
        // Never resolve — leaves the component in loading state.
        fetchWorkFeed.mockReturnValue(new Promise(() => {}));
        const { container } = renderCard();
        // Skeleton uses animate-pulse on placeholder rows.
        expect(container.querySelector('.animate-pulse')).not.toBeNull();
    });

    it('renders the empty-state copy when total is 0', async () => {
        fetchWorkFeed.mockResolvedValue({ success: true, items: [], total: 0 });
        renderCard();
        await waitFor(() =>
            expect(screen.getByText(/nothing urgent right now/i)).toBeInTheDocument(),
        );
    });

    it('renders one row per item with the source label', async () => {
        fetchWorkFeed.mockResolvedValue({
            success: true,
            total: 3,
            items: [
                {
                    id: 't1', source: 'roadmap_task', title: 'Submit MIT app',
                    days_until: 5, urgency: 'urgent', deep_link: '/roadmap?tab=plan&task_id=t1',
                },
                {
                    id: 'e1', source: 'essay', title: 'Common App essay',
                    deep_link: '/roadmap?tab=essays&essay_id=e1',
                },
                {
                    id: 's1', source: 'scholarship', title: 'Need-based aid',
                    days_until: 30, urgency: 'soon',
                    deep_link: '/roadmap?tab=scholarships&scholarship_id=s1',
                },
            ],
        });
        renderCard();

        await waitFor(() =>
            expect(screen.getByText('Submit MIT app')).toBeInTheDocument(),
        );
        // Each source's label should appear once per matching row.
        expect(screen.getByText('Plan')).toBeInTheDocument();
        expect(screen.getByText('Essay')).toBeInTheDocument();
        expect(screen.getByText('Scholarship')).toBeInTheDocument();
    });

    it('shows "Showing X of Y" when total exceeds the visible item count', async () => {
        fetchWorkFeed.mockResolvedValue({
            success: true,
            total: 24,
            items: Array.from({ length: 8 }, (_, i) => ({
                id: `t${i}`, source: 'roadmap_task', title: `T${i}`,
                deep_link: `/roadmap?tab=plan&task_id=t${i}`,
            })),
        });
        renderCard();
        await waitFor(() =>
            expect(screen.getByText(/showing 8 of 24/i)).toBeInTheDocument(),
        );
    });

    it('navigates via deep_link when an item row is clicked', async () => {
        fetchWorkFeed.mockResolvedValue({
            success: true,
            total: 1,
            items: [{
                id: 'e1', source: 'essay', title: 'Common App essay',
                deep_link: '/roadmap?tab=essays&essay_id=e1',
            }],
        });
        const user = userEvent.setup();
        renderCard();
        await waitFor(() => screen.getByText('Common App essay'));

        await user.click(screen.getByText('Common App essay'));

        expect(mockNavigate).toHaveBeenCalledWith('/roadmap?tab=essays&essay_id=e1');
    });

    it('formats the due-date label using days_until', async () => {
        fetchWorkFeed.mockResolvedValue({
            success: true,
            total: 3,
            items: [
                { id: 'a', source: 'roadmap_task', title: 'A', days_until: -2, urgency: 'overdue', deep_link: '#' },
                { id: 'b', source: 'roadmap_task', title: 'B', days_until: 0, urgency: 'urgent', deep_link: '#' },
                { id: 'c', source: 'roadmap_task', title: 'C', days_until: 5, urgency: 'urgent', deep_link: '#' },
            ],
        });
        renderCard();
        await waitFor(() => {
            expect(screen.getByText(/overdue · 2d/i)).toBeInTheDocument();
            expect(screen.getByText(/due today/i)).toBeInTheDocument();
            expect(screen.getByText(/due in 5d/i)).toBeInTheDocument();
        });
    });

    it('refetches when refreshKey changes', async () => {
        fetchWorkFeed.mockResolvedValue({ success: true, items: [], total: 0 });
        const { rerender } = renderCard({ refreshKey: 0 });
        await waitFor(() => expect(fetchWorkFeed).toHaveBeenCalledTimes(1));

        rerender(
            <MemoryRouter>
                <ThisWeekFocusCard userEmail="test.user@example.com" refreshKey={1} />
            </MemoryRouter>,
        );
        await waitFor(() => expect(fetchWorkFeed).toHaveBeenCalledTimes(2));
    });
});
