import React, { useEffect, useRef, useState } from 'react';
import { PencilSquareIcon } from '@heroicons/react/24/outline';
import { PencilSquareIcon as PencilSquareIconSolid } from '@heroicons/react/24/solid';
import { updateNotes } from '../../services/api';
import { useToast } from '../Toast';

// Save state machine for the textarea below the button.
// - idle    → no in-flight save and no recent save
// - saving  → an updateNotes() call is in flight
// - saved   → save succeeded; brief flash before returning to idle
const SAVE_IDLE = 'idle';
const SAVE_SAVING = 'saving';
const SAVE_SAVED = 'saved';

// Time the "Saved" indicator stays visible after a successful save.
const SAVED_INDICATOR_MS = 1500;

/**
 * Inline notes editor for the consolidated Roadmap UI.
 *
 *   <NotesAffordance
 *     userEmail={...}
 *     collection="essay_tracker"            // see NOTES_COLLECTIONS server-side
 *     itemId="..."
 *     initialValue={essay.notes}            // optional
 *     buttonClassName="..."                 // optional override
 *     emptyLabel="Add notes"                // optional, default below
 *   />
 *
 * UX:
 *   - Default state is a small icon button. Filled icon + indicator dot if
 *     notes already exist.
 *   - Click → expands a textarea inline. Saves on blur (the standard
 *     "click outside to save" model the design doc specifies).
 *   - Save is optimistic; on error we revert to the last-confirmed value,
 *     keep the editor open, and show an error toast.
 */
const NotesAffordance = ({
    userEmail,
    collection,
    itemId,
    initialValue = '',
    buttonClassName = '',
    emptyLabel = 'Add notes',
}) => {
    const toast = useToast();

    // The most recent value we've successfully persisted (or were given). The
    // textarea works against `draft`; on save success this is updated to mirror.
    // On save failure, draft is reverted to this.
    const [persistedValue, setPersistedValue] = useState(initialValue || '');
    const [draft, setDraft] = useState(initialValue || '');
    const [open, setOpen] = useState(false);
    const [saveState, setSaveState] = useState(SAVE_IDLE);
    const blurTimerRef = useRef(null);

    // If the parent passes a new initialValue (e.g., a different essay row got
    // mounted into the same cell), reset our local copies. We don't try to
    // preserve unsaved draft text across item changes — that's a footgun.
    useEffect(() => {
        setPersistedValue(initialValue || '');
        setDraft(initialValue || '');
    }, [collection, itemId, initialValue]);

    // Clear the saved-flash timer on unmount so we don't update state after.
    useEffect(() => {
        return () => {
            if (blurTimerRef.current) clearTimeout(blurTimerRef.current);
        };
    }, []);

    const hasNotes = persistedValue.trim().length > 0;

    const handleToggle = () => {
        setOpen((prev) => !prev);
    };

    const handleChange = (e) => {
        setDraft(e.target.value);
    };

    const persist = async (valueToSave) => {
        if (!userEmail || !collection || !itemId) return;
        if (valueToSave === persistedValue) return;       // no-op
        setSaveState(SAVE_SAVING);
        const result = await updateNotes(userEmail, collection, itemId, valueToSave);
        if (result?.success) {
            setPersistedValue(valueToSave);
            setSaveState(SAVE_SAVED);
            // Flash "Saved" then return to idle.
            if (blurTimerRef.current) clearTimeout(blurTimerRef.current);
            blurTimerRef.current = setTimeout(() => {
                setSaveState(SAVE_IDLE);
            }, SAVED_INDICATOR_MS);
        } else {
            // Revert local draft to last-confirmed value and tell the user.
            setDraft(persistedValue);
            setSaveState(SAVE_IDLE);
            toast.error('Could not save notes', result?.error || 'Please try again.');
        }
    };

    const handleBlur = () => {
        // Debounce so quick focus shuffles (e.g., user clicks back into the
        // same textarea) don't fire a save on each blur.
        if (blurTimerRef.current) clearTimeout(blurTimerRef.current);
        blurTimerRef.current = setTimeout(() => {
            persist(draft);
        }, 500);
    };

    const handleKeyDown = (e) => {
        // Cmd/Ctrl+Enter to save and close. Esc cancels (revert + close).
        if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
            e.preventDefault();
            if (blurTimerRef.current) clearTimeout(blurTimerRef.current);
            persist(draft);
            setOpen(false);
        } else if (e.key === 'Escape') {
            e.preventDefault();
            setDraft(persistedValue);
            setOpen(false);
        }
    };

    const Icon = hasNotes ? PencilSquareIconSolid : PencilSquareIcon;

    return (
        <div className="inline-flex flex-col">
            <button
                type="button"
                onClick={handleToggle}
                aria-expanded={open}
                aria-label={hasNotes ? 'Edit notes' : emptyLabel}
                title={hasNotes ? 'Edit notes' : emptyLabel}
                className={`relative inline-flex items-center justify-center w-8 h-8 rounded-md
                    text-[#1A4D2E] hover:bg-[#F8F6F0] transition-colors ${buttonClassName}`}
            >
                <Icon className="w-4 h-4" />
                {hasNotes && (
                    <span
                        aria-hidden="true"
                        className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-[#1A4D2E]"
                    />
                )}
            </button>

            {open && (
                <div className="mt-2 w-full max-w-md">
                    <textarea
                        autoFocus
                        value={draft}
                        onChange={handleChange}
                        onBlur={handleBlur}
                        onKeyDown={handleKeyDown}
                        placeholder={emptyLabel}
                        rows={3}
                        maxLength={50000}
                        className="w-full text-sm rounded-md border border-[#E0DED8]
                            bg-white px-3 py-2 placeholder-[#9A9A9A]
                            focus:outline-none focus:ring-2 focus:ring-[#1A4D2E] focus:border-transparent"
                    />
                    <div className="flex items-center justify-between mt-1 text-xs">
                        <span className="text-[#9A9A9A]">
                            Saves automatically · ⌘↵ to save · esc to cancel
                        </span>
                        <span
                            aria-live="polite"
                            className={`transition-opacity ${saveState === SAVE_IDLE ? 'opacity-0' : 'opacity-100'}
                                ${saveState === SAVE_SAVED ? 'text-[#1A4D2E]' : 'text-[#6B6B6B]'}`}
                        >
                            {saveState === SAVE_SAVING ? 'Saving…' : saveState === SAVE_SAVED ? 'Saved' : ''}
                        </span>
                    </div>
                </div>
            )}
        </div>
    );
};

export default NotesAffordance;
