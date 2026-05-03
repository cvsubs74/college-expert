import React, { useState, useEffect } from 'react';
import { ChatBubbleLeftRightIcon } from '@heroicons/react/24/outline';
import CounselorChat from '../counselor/CounselorChat';

// Local-storage key for whether the chat panel is open. Persisting across
// reloads keeps the user's preference; we only restore for the current
// device, so it's a UX hint not a profile setting.
const OPEN_STATE_KEY = 'roadmap_counselor_chat_open';

/**
 * Floating launcher for the CounselorChat component. Replaces the
 * sidebar-mounted chat that used to live on /counselor (which now redirects
 * to /roadmap).
 *
 * Layout:
 *   - Collapsed: a pill-shaped button bottom-right ("Ask Counselor").
 *   - Expanded: a 380×600 panel hosting <CounselorChat onClose={...}/>.
 *     Panel size is capped at calc(100vw-3rem)/calc(100vh-6rem) so it
 *     doesn't overflow on small viewports.
 *
 * Mount at the RoadmapPage level (not inside tab content) so the chat
 * persists across tab switches — its in-component state (messages,
 * conversation_id) is preserved as long as the user stays on /roadmap.
 */
const FloatingCounselorChat = () => {
    const [isOpen, setIsOpen] = useState(() => {
        try {
            return localStorage.getItem(OPEN_STATE_KEY) === '1';
        } catch {
            return false;
        }
    });

    useEffect(() => {
        try {
            localStorage.setItem(OPEN_STATE_KEY, isOpen ? '1' : '0');
        } catch {
            // Ignore quota / privacy-mode storage errors.
        }
    }, [isOpen]);

    const handleClose = () => setIsOpen(false);
    const handleOpen = () => setIsOpen(true);

    return (
        <>
            {!isOpen && (
                <button
                    type="button"
                    onClick={handleOpen}
                    aria-label="Open counselor chat"
                    className="fixed bottom-6 right-6 z-40 inline-flex items-center gap-2 px-4 py-3
                        rounded-full bg-[#1A4D2E] text-white shadow-lg shadow-[#1A4D2E]/25
                        hover:bg-[#2D6B45] hover:shadow-xl transition-all"
                >
                    <ChatBubbleLeftRightIcon className="h-5 w-5" />
                    <span className="hidden sm:inline text-sm font-medium">
                        Ask Counselor
                    </span>
                </button>
            )}

            {isOpen && (
                <div
                    role="dialog"
                    aria-label="Counselor chat"
                    className="fixed bottom-6 right-6 z-40
                        w-[380px] h-[600px]
                        max-w-[calc(100vw-3rem)] max-h-[calc(100vh-6rem)]"
                >
                    <CounselorChat onClose={handleClose} />
                </div>
            )}
        </>
    );
};

export default FloatingCounselorChat;
