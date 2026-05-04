/**
 * RunNowPanel — clicking "Run now" should fetch a preview, show the
 * PreviewModal, and only fire the actual /run after the user confirms.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

const triggerRunFn = vi.fn();
const getRunPreviewFn = vi.fn();

vi.mock('../services/qaAgent', () => ({
    triggerRun: (...a) => triggerRunFn(...a),
    getRunPreview: (...a) => getRunPreviewFn(...a),
}));

// AuthContext supplies currentUser; stub minimally.
vi.mock('../context/AuthContext', () => ({
    useAuth: () => ({ currentUser: { email: 'admin@example.com' } }),
}));

import RunNowPanel from '../components/qa/RunNowPanel';

beforeEach(() => {
    triggerRunFn.mockReset();
    getRunPreviewFn.mockReset();
});

const samplePreview = {
    success: true,
    picked: [
        {
            id: 'junior_spring_5school',
            description: 'Junior in spring with 5-school list',
            business_rationale: 'Validates the most common journey.',
            surfaces_covered: ['profile', 'roadmap'],
            synthesized: false,
        },
    ],
    synth_count: 0,
    static_count: 1,
};

describe('RunNowPanel', () => {
    it('clicking Run now opens the preview modal first (no /run call yet)', async () => {
        getRunPreviewFn.mockResolvedValue(samplePreview);
        const user = userEvent.setup();
        render(<RunNowPanel />);

        await user.click(screen.getByRole('button', { name: /run now/i }));

        // Preview API was called.
        await waitFor(() => expect(getRunPreviewFn).toHaveBeenCalled());
        // Modal shows the picked scenario.
        await waitFor(() =>
            expect(screen.getByText(/junior_spring_5school/i)).toBeInTheDocument()
        );
        // /run was NOT called yet.
        expect(triggerRunFn).not.toHaveBeenCalled();
    });

    it('confirming the preview fires /run with the actor', async () => {
        getRunPreviewFn.mockResolvedValue(samplePreview);
        triggerRunFn.mockResolvedValue({ run_id: 'run_abc', summary: { pass: 1, total: 1 } });
        const user = userEvent.setup();
        render(<RunNowPanel />);

        await user.click(screen.getByRole('button', { name: /run now/i }));
        await waitFor(() => screen.getByRole('button', { name: /^run$/i }));

        await user.click(screen.getByRole('button', { name: /^run$/i }));
        await waitFor(() => expect(triggerRunFn).toHaveBeenCalled());
        expect(triggerRunFn).toHaveBeenCalledWith({
            scenarioId: null,
            actor: 'admin@example.com',
        });
    });

    it('cancelling the preview does NOT fire /run', async () => {
        getRunPreviewFn.mockResolvedValue(samplePreview);
        const user = userEvent.setup();
        render(<RunNowPanel />);

        await user.click(screen.getByRole('button', { name: /run now/i }));
        await waitFor(() => screen.getByRole('button', { name: /cancel/i }));

        await user.click(screen.getByRole('button', { name: /cancel/i }));
        // Modal closes; /run never called.
        await waitFor(() =>
            expect(screen.queryByText(/junior_spring_5school/i)).not.toBeInTheDocument()
        );
        expect(triggerRunFn).not.toHaveBeenCalled();
    });

    it('shows error banner when preview fetch fails', async () => {
        getRunPreviewFn.mockRejectedValue(new Error('preview boom'));
        const user = userEvent.setup();
        render(<RunNowPanel />);

        await user.click(screen.getByRole('button', { name: /run now/i }));
        await waitFor(() =>
            expect(screen.getByText(/preview boom/i)).toBeInTheDocument()
        );
    });
});
