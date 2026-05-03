/**
 * ScheduleEditor lets the admin edit when scheduled runs fire.
 * Loads current config from qa-agent's GET /schedule, lets the user
 * change frequency / times / days / timezone, posts the new config
 * back to POST /schedule.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

const getScheduleFn = vi.fn();
const saveScheduleFn = vi.fn();
vi.mock('../services/qaAgent', () => ({
    getSchedule: (...a) => getScheduleFn(...a),
    saveSchedule: (...a) => saveScheduleFn(...a),
}));

import ScheduleEditor from '../components/qa/ScheduleEditor';

beforeEach(() => {
    getScheduleFn.mockReset();
    saveScheduleFn.mockReset();
});

describe('ScheduleEditor', () => {
    it('loads current schedule and renders the form', async () => {
        getScheduleFn.mockResolvedValue({
            success: true,
            schedule: {
                frequency: 'daily',
                times: ['06:00'],
                days: ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'],
                timezone: 'America/Los_Angeles',
            },
        });
        render(<ScheduleEditor />);
        await waitFor(() => {
            expect(screen.getByDisplayValue('06:00')).toBeInTheDocument();
        });
        expect(screen.getByDisplayValue(/America\/Los_Angeles/)).toBeInTheDocument();
    });

    it('submits the updated schedule on Save', async () => {
        getScheduleFn.mockResolvedValue({
            success: true,
            schedule: {
                frequency: 'daily',
                times: ['06:00'],
                days: ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'],
                timezone: 'America/Los_Angeles',
            },
        });
        saveScheduleFn.mockResolvedValue({ success: true });

        const user = userEvent.setup();
        render(<ScheduleEditor />);
        await waitFor(() => {
            expect(screen.getByDisplayValue('06:00')).toBeInTheDocument();
        });

        // Change first time from 06:00 to 07:30
        const timeInput = screen.getByDisplayValue('06:00');
        await user.clear(timeInput);
        await user.type(timeInput, '07:30');
        await user.click(screen.getByRole('button', { name: /save/i }));

        await waitFor(() => {
            expect(saveScheduleFn).toHaveBeenCalled();
        });
        const submitted = saveScheduleFn.mock.calls[0][0];
        expect(submitted.times).toContain('07:30');
    });

    it('renders an error if save fails', async () => {
        getScheduleFn.mockResolvedValue({
            success: true,
            schedule: {
                frequency: 'daily',
                times: ['06:00'],
                days: ['mon'],
                timezone: 'America/Los_Angeles',
            },
        });
        saveScheduleFn.mockRejectedValue(new Error('nope'));

        const user = userEvent.setup();
        render(<ScheduleEditor />);
        await waitFor(() => {
            expect(screen.getByDisplayValue('06:00')).toBeInTheDocument();
        });
        await user.click(screen.getByRole('button', { name: /save/i }));
        await waitFor(() => {
            expect(screen.getByText(/nope|couldn't save/i)).toBeInTheDocument();
        });
    });
});
