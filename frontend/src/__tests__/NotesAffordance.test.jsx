/**
 * Tests for NotesAffordance — the inline pencil icon + textarea that appears
 * on every notes-bearing surface (essays, scholarships, college cards, focus
 * card rows). The component is small but the save behavior has a real state
 * machine (idle/saving/saved + revert-on-error) worth locking in.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import NotesAffordance from '../components/roadmap/NotesAffordance';
import { toastSpy } from './setup';

// updateNotes is the only API call the component makes. Mock the api.js
// module so we control success/failure without HTTP.
vi.mock('../services/api', () => ({
    updateNotes: vi.fn(),
}));
import { updateNotes } from '../services/api';

beforeEach(() => {
    updateNotes.mockReset();
});

const defaultProps = {
    userEmail: 'test.user@example.com',
    collection: 'essay_tracker',
    itemId: 'essay-1',
};

describe('NotesAffordance', () => {
    describe('collapsed state', () => {
        it('renders an "add notes" button when no initial value', () => {
            render(<NotesAffordance {...defaultProps} initialValue="" />);
            const button = screen.getByRole('button', { name: /add notes/i });
            expect(button).toBeInTheDocument();
            // Indicator dot should NOT be visible when notes are empty.
            expect(button.querySelector('span[aria-hidden="true"]')).toBeNull();
        });

        it('shows the indicator dot when initial value is non-empty', () => {
            render(<NotesAffordance {...defaultProps} initialValue="prior note text" />);
            const button = screen.getByRole('button', { name: /edit notes/i });
            // Indicator dot lives inside the button.
            expect(button.querySelector('span[aria-hidden="true"]')).not.toBeNull();
        });

        it('treats whitespace-only initial value as empty (no dot)', () => {
            render(<NotesAffordance {...defaultProps} initialValue="   " />);
            const button = screen.getByRole('button', { name: /add notes/i });
            expect(button.querySelector('span[aria-hidden="true"]')).toBeNull();
        });
    });

    describe('expanded state', () => {
        it('clicking the icon expands a textarea pre-filled with the initial value', async () => {
            const user = userEvent.setup();
            render(<NotesAffordance {...defaultProps} initialValue="hello world" />);
            await user.click(screen.getByRole('button', { name: /edit notes/i }));

            const textarea = screen.getByRole('textbox');
            expect(textarea).toBeInTheDocument();
            expect(textarea).toHaveValue('hello world');
            // The hint text reminds the user about save shortcuts.
            expect(screen.getByText(/saves automatically/i)).toBeInTheDocument();
        });

        it('clicking the icon a second time collapses the textarea', async () => {
            const user = userEvent.setup();
            render(<NotesAffordance {...defaultProps} />);
            const trigger = screen.getByRole('button', { name: /add notes/i });

            await user.click(trigger);
            expect(screen.getByRole('textbox')).toBeInTheDocument();

            await user.click(trigger);
            expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
        });
    });

    describe('save flow', () => {
        it('calls updateNotes with the expected args on blur', async () => {
            updateNotes.mockResolvedValue({ success: true, updated_at: '2026-05-03T10:00:00Z' });
            const user = userEvent.setup();
            render(<NotesAffordance {...defaultProps} initialValue="" />);

            await user.click(screen.getByRole('button', { name: /add notes/i }));
            await user.type(screen.getByRole('textbox'), 'new note');
            // Blur — the component debounces 500ms then saves.
            await user.tab();

            await waitFor(
                () => expect(updateNotes).toHaveBeenCalledWith(
                    'test.user@example.com',
                    'essay_tracker',
                    'essay-1',
                    'new note',
                ),
                { timeout: 2000 },
            );
        });

        it('does not call updateNotes when the value is unchanged', async () => {
            const user = userEvent.setup();
            render(<NotesAffordance {...defaultProps} initialValue="same text" />);

            await user.click(screen.getByRole('button', { name: /edit notes/i }));
            await user.tab();                                 // blur immediately, no edit

            // Wait past the debounce window then assert no call happened.
            await new Promise((r) => setTimeout(r, 700));
            expect(updateNotes).not.toHaveBeenCalled();
        });

        it('reverts and toasts on save error', async () => {
            updateNotes.mockResolvedValue({ success: false, error: 'item not found' });
            const user = userEvent.setup();
            render(<NotesAffordance {...defaultProps} initialValue="original" />);

            await user.click(screen.getByRole('button', { name: /edit notes/i }));
            const textarea = screen.getByRole('textbox');
            await user.clear(textarea);
            await user.type(textarea, 'failed edit');
            await user.tab();

            await waitFor(() => expect(updateNotes).toHaveBeenCalled(), { timeout: 2000 });
            // Error toast surfaced.
            await waitFor(() => expect(toastSpy.error).toHaveBeenCalled(), { timeout: 2000 });
            // Textarea reverted to last-confirmed value.
            await waitFor(() => expect(textarea).toHaveValue('original'));
        });

        it('saves an empty string to clear notes', async () => {
            updateNotes.mockResolvedValue({ success: true, updated_at: '2026-05-03T10:00:00Z' });
            const user = userEvent.setup();
            render(<NotesAffordance {...defaultProps} initialValue="will clear" />);

            await user.click(screen.getByRole('button', { name: /edit notes/i }));
            const textarea = screen.getByRole('textbox');
            await user.clear(textarea);
            await user.tab();

            await waitFor(
                () => expect(updateNotes).toHaveBeenCalledWith(
                    'test.user@example.com',
                    'essay_tracker',
                    'essay-1',
                    '',
                ),
                { timeout: 2000 },
            );
        });
    });
});
