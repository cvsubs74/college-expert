/**
 * Tests for AddTaskModal — the "+ Add task" form on the Plan tab.
 *
 * The modal has a small interaction surface (title required, optional
 * fields, two ways to close, save flow) but enough conditional rendering
 * + state machine to be worth pinning down.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import AddTaskModal from '../components/roadmap/AddTaskModal';
import { toastSpy } from './setup';

vi.mock('../services/api', () => ({
    createUserTask: vi.fn(),
    getCollegeList: vi.fn(),
}));
import { createUserTask, getCollegeList } from '../services/api';

beforeEach(() => {
    createUserTask.mockReset();
    getCollegeList.mockReset();
    // Default: empty college list so the school dropdown shows the no-school
    // option only. Individual tests override.
    getCollegeList.mockResolvedValue({ college_list: [] });
});

const renderModal = (overrides = {}) => {
    const onClose = vi.fn();
    const onSaved = vi.fn();
    const props = {
        userEmail: 'test.user@example.com',
        isOpen: true,
        onClose,
        onSaved,
        ...overrides,
    };
    const utils = render(<AddTaskModal {...props} />);
    return { ...utils, onClose, onSaved };
};

describe('AddTaskModal', () => {
    describe('visibility', () => {
        it('renders nothing when isOpen is false', () => {
            const { container } = render(<AddTaskModal userEmail="x" isOpen={false} onClose={() => {}} />);
            expect(container.firstChild).toBeNull();
        });

        it('renders the form when isOpen is true', () => {
            renderModal();
            expect(screen.getByRole('dialog')).toBeInTheDocument();
            expect(screen.getByLabelText(/title/i)).toBeInTheDocument();
        });
    });

    describe('form gating', () => {
        it('disables submit when title is empty', () => {
            renderModal();
            const submit = screen.getByRole('button', { name: /add task/i });
            expect(submit).toBeDisabled();
        });

        it('enables submit once title has non-whitespace content', async () => {
            const user = userEvent.setup();
            renderModal();
            await user.type(screen.getByLabelText(/title/i), 'My new task');
            const submit = screen.getByRole('button', { name: /add task/i });
            expect(submit).toBeEnabled();
        });
    });

    describe('save flow', () => {
        it('calls createUserTask with the typed values and fires onSaved', async () => {
            createUserTask.mockResolvedValue({ success: true, task_id: 'user_task_123' });
            const user = userEvent.setup();
            const { onClose, onSaved } = renderModal();

            await user.type(screen.getByLabelText(/title/i), 'Reach out for letter of rec');
            await user.click(screen.getByRole('button', { name: /add task/i }));

            await waitFor(() => expect(createUserTask).toHaveBeenCalledWith(
                'test.user@example.com',
                expect.objectContaining({ title: 'Reach out for letter of rec' }),
            ));
            await waitFor(() => expect(onSaved).toHaveBeenCalledWith('user_task_123'));
            await waitFor(() => expect(onClose).toHaveBeenCalled());
            expect(toastSpy.success).toHaveBeenCalled();
        });

        it('passes optional fields when filled', async () => {
            createUserTask.mockResolvedValue({ success: true, task_id: 'tid' });
            getCollegeList.mockResolvedValue({
                college_list: [{ university_id: 'mit', university_name: 'MIT' }],
            });
            const user = userEvent.setup();
            renderModal();

            await user.type(screen.getByLabelText(/title/i), 'Submit MIT app');
            await waitFor(() => {
                // Wait for the college list to load into the select.
                expect(screen.getByRole('option', { name: 'MIT' })).toBeInTheDocument();
            });
            await user.selectOptions(screen.getByLabelText(/for school/i), 'mit');
            await user.click(screen.getByRole('button', { name: /add task/i }));

            await waitFor(() => expect(createUserTask).toHaveBeenCalledWith(
                'test.user@example.com',
                expect.objectContaining({
                    title: 'Submit MIT app',
                    universityId: 'mit',
                }),
            ));
        });

        it('shows error toast and keeps modal open when save fails', async () => {
            createUserTask.mockResolvedValue({ success: false, error: 'server down' });
            const user = userEvent.setup();
            const { onClose } = renderModal();

            await user.type(screen.getByLabelText(/title/i), 'Will fail');
            await user.click(screen.getByRole('button', { name: /add task/i }));

            await waitFor(() => expect(toastSpy.error).toHaveBeenCalled());
            // onClose should NOT have been called — user can retry without retyping.
            expect(onClose).not.toHaveBeenCalled();
        });
    });

    describe('dismissal', () => {
        it('closes when escape is pressed', async () => {
            const user = userEvent.setup();
            const { onClose } = renderModal();
            await user.keyboard('{Escape}');
            expect(onClose).toHaveBeenCalled();
        });

        it('closes when the cancel button is clicked', async () => {
            const user = userEvent.setup();
            const { onClose } = renderModal();
            await user.click(screen.getByRole('button', { name: /cancel/i }));
            expect(onClose).toHaveBeenCalled();
        });

        it('does NOT close when clicking inside the dialog', async () => {
            const user = userEvent.setup();
            const { onClose } = renderModal();
            // Click on the title input — definitely "inside" the dialog content.
            await user.click(screen.getByLabelText(/title/i));
            expect(onClose).not.toHaveBeenCalled();
        });
    });
});
