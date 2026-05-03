import React, { useEffect, useState } from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import { createUserTask, getCollegeList } from '../../services/api';
import { useToast } from '../Toast';

/**
 * Modal form for adding a custom task to the user's roadmap.
 *
 * Renders inside a fixed full-screen overlay so the user can't accidentally
 * dismiss it by clicking page elements. Press Escape or click the backdrop
 * to close. Tasks are created via createUserTask() (POST
 * /save-roadmap-task with created_by:'user'); on success we call
 * onSaved() — the parent uses this to bump a refreshKey on the focus card.
 *
 * Form fields:
 *   - title       (required)
 *   - due_date    (optional, native date input)
 *   - university  (optional, dropdown populated from the user's college_list)
 *   - notes       (optional)
 */
const AddTaskModal = ({ userEmail, isOpen, onClose, onSaved }) => {
    const toast = useToast();
    const [title, setTitle] = useState('');
    const [dueDate, setDueDate] = useState('');
    const [universityId, setUniversityId] = useState('');
    const [notes, setNotes] = useState('');
    const [colleges, setColleges] = useState([]);
    const [saving, setSaving] = useState(false);

    // Reset the form whenever the modal opens. We don't try to preserve
    // partially-typed text across opens — keeps the mental model simple.
    useEffect(() => {
        if (!isOpen) return;
        setTitle('');
        setDueDate('');
        setUniversityId('');
        setNotes('');
    }, [isOpen]);

    // Fetch the user's college list once when the modal opens. Empty list
    // is fine — the dropdown just shows the "(no school)" option.
    useEffect(() => {
        if (!isOpen || !userEmail) return;
        let cancelled = false;
        getCollegeList(userEmail)
            .then((res) => {
                if (cancelled) return;
                const list = Array.isArray(res?.college_list) ? res.college_list : [];
                setColleges(list);
            })
            .catch(() => {
                // Silent — the dropdown is optional, no need to interrupt.
            });
        return () => { cancelled = true; };
    }, [isOpen, userEmail]);

    // Esc closes; lock body scroll while open so the page underneath doesn't
    // scroll behind the modal.
    useEffect(() => {
        if (!isOpen) return;
        const onKeyDown = (e) => {
            if (e.key === 'Escape') onClose();
        };
        document.addEventListener('keydown', onKeyDown);
        const prevOverflow = document.body.style.overflow;
        document.body.style.overflow = 'hidden';
        return () => {
            document.removeEventListener('keydown', onKeyDown);
            document.body.style.overflow = prevOverflow;
        };
    }, [isOpen, onClose]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!title.trim() || saving) return;
        setSaving(true);
        const result = await createUserTask(userEmail, {
            title,
            dueDate: dueDate || undefined,
            universityId: universityId || undefined,
            notes: notes || undefined,
        });
        setSaving(false);
        if (result?.success) {
            toast.success('Task added', `"${title.trim()}" is on your roadmap.`);
            if (onSaved) onSaved(result.task_id);
            onClose();
        } else {
            toast.error('Could not add task', result?.error || 'Please try again.');
        }
    };

    if (!isOpen) return null;

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
            onClick={onClose}
            role="presentation"
        >
            <div
                className="bg-white rounded-2xl shadow-xl w-full max-w-md max-h-[90vh] overflow-y-auto"
                onClick={(e) => e.stopPropagation()}
                role="dialog"
                aria-modal="true"
                aria-labelledby="add-task-title"
            >
                <header className="flex items-center justify-between px-5 py-4 border-b border-[#E0DED8]">
                    <h2 id="add-task-title" className="text-lg font-medium text-[#1A4D2E]">
                        Add a task
                    </h2>
                    <button
                        type="button"
                        onClick={onClose}
                        aria-label="Close"
                        className="p-1 text-stone-500 hover:text-[#1A4D2E] hover:bg-stone-100 rounded-md transition-colors"
                    >
                        <XMarkIcon className="w-5 h-5" />
                    </button>
                </header>

                <form onSubmit={handleSubmit} className="px-5 py-4 space-y-4">
                    <div>
                        <label htmlFor="add-task-title-input" className="block text-xs font-medium text-[#4A4A4A] uppercase tracking-wide mb-1">
                            Title
                        </label>
                        <input
                            id="add-task-title-input"
                            type="text"
                            value={title}
                            onChange={(e) => setTitle(e.target.value)}
                            placeholder="e.g., Reach out to Dr. Smith for letter of rec"
                            maxLength={200}
                            autoFocus
                            required
                            className="w-full text-sm rounded-md border border-[#E0DED8] bg-white px-3 py-2
                                placeholder-[#9A9A9A]
                                focus:outline-none focus:ring-2 focus:ring-[#1A4D2E] focus:border-transparent"
                        />
                    </div>

                    <div>
                        <label htmlFor="add-task-due-date" className="block text-xs font-medium text-[#4A4A4A] uppercase tracking-wide mb-1">
                            Due date <span className="font-normal text-[#9A9A9A] normal-case">(optional)</span>
                        </label>
                        <input
                            id="add-task-due-date"
                            type="date"
                            value={dueDate}
                            onChange={(e) => setDueDate(e.target.value)}
                            className="w-full text-sm rounded-md border border-[#E0DED8] bg-white px-3 py-2
                                focus:outline-none focus:ring-2 focus:ring-[#1A4D2E] focus:border-transparent"
                        />
                    </div>

                    <div>
                        <label htmlFor="add-task-school" className="block text-xs font-medium text-[#4A4A4A] uppercase tracking-wide mb-1">
                            For school <span className="font-normal text-[#9A9A9A] normal-case">(optional)</span>
                        </label>
                        <select
                            id="add-task-school"
                            value={universityId}
                            onChange={(e) => setUniversityId(e.target.value)}
                            className="w-full text-sm rounded-md border border-[#E0DED8] bg-white px-3 py-2
                                focus:outline-none focus:ring-2 focus:ring-[#1A4D2E] focus:border-transparent"
                        >
                            <option value="">— No specific school —</option>
                            {colleges.map((c) => (
                                <option key={c.university_id} value={c.university_id}>
                                    {c.university_name || c.university_id}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div>
                        <label htmlFor="add-task-notes" className="block text-xs font-medium text-[#4A4A4A] uppercase tracking-wide mb-1">
                            Notes <span className="font-normal text-[#9A9A9A] normal-case">(optional)</span>
                        </label>
                        <textarea
                            id="add-task-notes"
                            value={notes}
                            onChange={(e) => setNotes(e.target.value)}
                            placeholder="Anything you want to remember about this task"
                            rows={3}
                            maxLength={50000}
                            className="w-full text-sm rounded-md border border-[#E0DED8] bg-white px-3 py-2
                                placeholder-[#9A9A9A]
                                focus:outline-none focus:ring-2 focus:ring-[#1A4D2E] focus:border-transparent"
                        />
                    </div>

                    <div className="flex items-center justify-end gap-2 pt-2">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-4 py-2 text-sm font-medium text-[#4A4A4A] rounded-full
                                hover:bg-stone-100 transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={!title.trim() || saving}
                            className="px-4 py-2 text-sm font-medium text-white rounded-full
                                bg-[#1A4D2E] hover:bg-[#2D6B45] disabled:bg-stone-300 disabled:cursor-not-allowed
                                transition-colors"
                        >
                            {saving ? 'Saving…' : 'Add task'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default AddTaskModal;
