/**
 * FeedbackPanel — admin types notes that steer the next scheduled
 * run's synthesizer. Renders existing items (with applied counts),
 * supports adding new items, and dismissing.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render as rtlRender, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

// FeedbackPanel renders <Link> elements that need a Router context.
const render = (ui, opts) => rtlRender(<MemoryRouter>{ui}</MemoryRouter>, opts);

const getFeedbackFn = vi.fn();
const addFeedbackFn = vi.fn();
const dismissFeedbackFn = vi.fn();

vi.mock('../services/qaAgent', () => ({
    getFeedback: (...a) => getFeedbackFn(...a),
    addFeedback: (...a) => addFeedbackFn(...a),
    dismissFeedback: (...a) => dismissFeedbackFn(...a),
}));

import FeedbackPanel from '../components/qa/FeedbackPanel';

beforeEach(() => {
    getFeedbackFn.mockReset();
    addFeedbackFn.mockReset();
    dismissFeedbackFn.mockReset();
    // Default: empty list.
    getFeedbackFn.mockResolvedValue({ success: true, items: [] });
    addFeedbackFn.mockResolvedValue({ success: true, item: {} });
    dismissFeedbackFn.mockResolvedValue({ success: true });
});

describe('FeedbackPanel', () => {
    it('renders empty state when no items', async () => {
        render(<FeedbackPanel />);
        await waitFor(() => {
            expect(screen.getByText(/No active feedback/i)).toBeInTheDocument();
        });
    });

    it('renders existing items with text + applied count + id', async () => {
        getFeedbackFn.mockResolvedValue({
            success: true,
            items: [
                {
                    id: 'fb_abc',
                    text: 'Focus on essay tracker',
                    status: 'active',
                    applied_count: 2,
                    max_applies: 5,
                    last_applied_run_id: 'run_xyz',
                },
            ],
        });
        render(<FeedbackPanel />);
        await waitFor(() => {
            expect(screen.getByText(/Focus on essay tracker/i)).toBeInTheDocument();
        });
        expect(screen.getByText(/applied 2\/5/i)).toBeInTheDocument();
        expect(screen.getByText(/fb_abc/)).toBeInTheDocument();
    });

    it('submits new feedback and refreshes the list', async () => {
        const user = userEvent.setup();
        addFeedbackFn.mockResolvedValue({
            success: true,
            item: { id: 'fb_new', text: 'test essay tracker', status: 'active' },
        });
        // After submit, the next getFeedback returns the new item.
        getFeedbackFn
            .mockResolvedValueOnce({ success: true, items: [] })
            .mockResolvedValueOnce({
                success: true,
                items: [{
                    id: 'fb_new', text: 'test essay tracker', status: 'active',
                    applied_count: 0, max_applies: 5,
                }],
            });

        render(<FeedbackPanel />);
        await waitFor(() => expect(screen.getByText(/No active feedback/i)).toBeInTheDocument());

        await user.type(
            screen.getByPlaceholderText(/Focus on essay tracker/i),
            'test essay tracker',
        );
        await user.click(screen.getByRole('button', { name: /submit/i }));

        await waitFor(() => {
            expect(addFeedbackFn).toHaveBeenCalledWith({
                text: 'test essay tracker',
            });
        });
        // After refresh, new item shows.
        await waitFor(() => {
            expect(screen.getByText('test essay tracker')).toBeInTheDocument();
        });
    });

    it('dismisses an item via the X button', async () => {
        const user = userEvent.setup();
        getFeedbackFn
            .mockResolvedValueOnce({
                success: true,
                items: [{
                    id: 'fb_doomed', text: 'dismiss me please', status: 'active',
                    applied_count: 0, max_applies: 5,
                }],
            })
            .mockResolvedValueOnce({ success: true, items: [] });

        render(<FeedbackPanel />);
        await waitFor(() => expect(screen.getByText(/dismiss me please/i)).toBeInTheDocument());

        await user.click(screen.getByLabelText(/Dismiss fb_doomed/i));

        await waitFor(() => {
            expect(dismissFeedbackFn).toHaveBeenCalledWith('fb_doomed');
        });
        await waitFor(() => {
            expect(screen.queryByText(/dismiss me please/i)).not.toBeInTheDocument();
        });
    });

    it('disables submit when the draft is too short', async () => {
        const user = userEvent.setup();
        render(<FeedbackPanel />);
        await waitFor(() => screen.getByPlaceholderText(/Focus on essay tracker/i));

        await user.type(screen.getByPlaceholderText(/Focus on essay tracker/i), 'abc');
        const submit = screen.getByRole('button', { name: /submit/i });
        expect(submit).toBeDisabled();
    });

    it('shows the active count + cap', async () => {
        getFeedbackFn.mockResolvedValue({
            success: true,
            items: Array.from({ length: 3 }, (_, i) => ({
                id: `fb_${i}`, text: `item ${i}`, status: 'active',
                applied_count: 0, max_applies: 5,
            })),
        });
        render(<FeedbackPanel />);
        await waitFor(() => expect(screen.getByText(/3 of 10 active/i)).toBeInTheDocument());
    });

    it('renders an error banner when add fails', async () => {
        addFeedbackFn.mockResolvedValue({
            success: false,
            error: 'already have 10 active items',
        });
        const user = userEvent.setup();
        render(<FeedbackPanel />);
        await waitFor(() => screen.getByPlaceholderText(/Focus on essay tracker/i));
        await user.type(
            screen.getByPlaceholderText(/Focus on essay tracker/i),
            'this should fail',
        );
        await user.click(screen.getByRole('button', { name: /submit/i }));
        await waitFor(() => {
            expect(screen.getByText(/already have 10 active items/i)).toBeInTheDocument();
        });
    });

    // ---- Applied-status visibility -------------------------------------
    // Bug repro: "Make sure the feedback provided in 'Steer' is being
    // used to generate scenarios." The loop was correct but invisible —
    // operators couldn't see whether their feedback had been picked up
    // by a run. Fix: surface an "✓ applied" pill and a clickable run-id
    // link when applied_count > 0.

    describe('Applied indicator', () => {
        it('shows an "applied" pill when applied_count > 0', async () => {
            getFeedbackFn.mockResolvedValue({
                success: true,
                items: [{
                    id: 'fb_used',
                    text: 'used at least once',
                    status: 'active',
                    applied_count: 1,
                    max_applies: 5,
                    last_applied_run_id: 'run_xyz',
                }],
            });
            render(<FeedbackPanel />);
            await waitFor(() => {
                expect(screen.getByText(/used at least once/i)).toBeInTheDocument();
            });
            // The pill text is short — match on the word "applied" + a
            // checkmark or similar affirmative.
            expect(screen.getByLabelText(/applied to a run/i)).toBeInTheDocument();
        });

        it('does NOT show an "applied" pill when applied_count is 0', async () => {
            getFeedbackFn.mockResolvedValue({
                success: true,
                items: [{
                    id: 'fb_fresh',
                    text: 'never applied',
                    status: 'active',
                    applied_count: 0,
                    max_applies: 5,
                }],
            });
            render(<FeedbackPanel />);
            await waitFor(() => {
                expect(screen.getByText(/never applied/i)).toBeInTheDocument();
            });
            expect(screen.queryByLabelText(/applied to a run/i)).toBeNull();
        });

        it('renders last_applied_run_id as a clickable link to /qa-runs', async () => {
            getFeedbackFn.mockResolvedValue({
                success: true,
                items: [{
                    id: 'fb_linked',
                    text: 'linked to run',
                    status: 'active',
                    applied_count: 2,
                    max_applies: 5,
                    last_applied_run_id: 'run_clickable_xyz',
                }],
            });
            render(<FeedbackPanel />);
            await waitFor(() => {
                expect(screen.getByText(/linked to run/i)).toBeInTheDocument();
            });
            const link = screen.getByRole('link', { name: /run_clickable_xyz/i });
            expect(link).toBeInTheDocument();
            // Link points at the run-detail page.
            expect(link.getAttribute('href')).toContain('run_clickable_xyz');
        });
    });
});
