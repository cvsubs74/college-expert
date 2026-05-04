import React, { useEffect, useRef, useState } from 'react';
import { ChatBubbleLeftRightIcon, PaperAirplaneIcon, ArrowPathIcon } from '@heroicons/react/24/outline';
import { sendChatMessage } from '../../services/qaAgent';

// Admin chat about QA runs / results / system health. Stateless per
// browser tab — the messages array lives in component state and is
// flushed on refresh. Sends the running history with each call so the
// model can resolve follow-ups ("and the one before that?").
//
// Spec: docs/prd/qa-agent-chat.md, docs/design/qa-agent-chat.md.

const STARTER_QUESTIONS = [
    'How is the system trending over the last few runs?',
    'Which scenarios fail most often?',
    "What's the most common failure mode this week?",
];

const ChatPanel = () => {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [busy, setBusy] = useState(false);
    const [open, setOpen] = useState(true);
    const scrollRef = useRef(null);

    // Auto-scroll to the latest message.
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages, busy]);

    const ask = async (question) => {
        const trimmed = question.trim();
        if (!trimmed || busy) return;
        const next = [...messages, { role: 'user', content: trimmed }];
        setMessages(next);
        setInput('');
        setBusy(true);
        try {
            // Send PRIOR history (without the just-added user message —
            // the backend includes the question separately in the prompt).
            const resp = await sendChatMessage({
                question: trimmed,
                history: messages,
            });
            setMessages([
                ...next,
                { role: 'assistant', content: resp.answer },
            ]);
        } catch (err) {
            setMessages([
                ...next,
                {
                    role: 'assistant',
                    content: err.message || 'Chat backend unavailable',
                    isError: true,
                },
            ]);
        } finally {
            setBusy(false);
        }
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        ask(input);
    };

    return (
        <div className="bg-white rounded-xl border border-[#E0DED8] overflow-hidden">
            {/* Header / collapse toggle */}
            <button
                type="button"
                onClick={() => setOpen(!open)}
                className="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-[#FBFAF6]"
            >
                <div className="flex items-center gap-2">
                    <ChatBubbleLeftRightIcon className="h-4 w-4 text-[#1A4D2E]" />
                    <h2 className="text-sm font-bold uppercase tracking-wider text-[#1A4D2E]">
                        Ask the QA agent
                    </h2>
                </div>
                <span className="text-xs text-[#8A8A8A]">
                    {open ? 'collapse' : 'expand'}
                </span>
            </button>

            {open && (
                <div className="border-t border-[#E0DED8]">
                    {/* Message list */}
                    <div
                        ref={scrollRef}
                        className="max-h-96 overflow-y-auto px-5 py-4 space-y-3 bg-[#FBFAF6]"
                    >
                        {messages.length === 0 && !busy && (
                            <div className="text-xs text-[#6B6B6B]">
                                <p className="mb-2">
                                    Ask anything about recent runs, failure patterns, or
                                    system health. The agent grounds answers in the last
                                    30 runs.
                                </p>
                                <div className="flex flex-wrap gap-1.5 mt-2">
                                    {STARTER_QUESTIONS.map((q) => (
                                        <button
                                            key={q}
                                            type="button"
                                            onClick={() => ask(q)}
                                            disabled={busy}
                                            className="text-[11px] px-2.5 py-1 bg-white border border-[#E0DED8] rounded-full hover:border-[#1A4D2E] hover:bg-[#F0EFE9] transition-all disabled:opacity-50"
                                        >
                                            {q}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}
                        {messages.map((m, i) => (
                            <div
                                key={i}
                                className={`text-sm whitespace-pre-wrap ${
                                    m.role === 'user'
                                        ? 'text-[#1A2E1F] font-medium'
                                        : m.isError
                                        ? 'text-rose-700 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2'
                                        : 'text-[#2A2A2A] bg-white border border-[#E0DED8] rounded-lg px-3 py-2'
                                }`}
                            >
                                {m.role === 'user' ? `> ${m.content}` : m.content}
                            </div>
                        ))}
                        {busy && (
                            <div className="text-sm text-[#8A8A8A] flex items-center gap-2">
                                <ArrowPathIcon className="h-4 w-4 animate-spin" />
                                Thinking…
                            </div>
                        )}
                    </div>

                    {/* Input */}
                    <form
                        onSubmit={handleSubmit}
                        className="flex items-center gap-2 px-5 py-3 border-t border-[#E0DED8]"
                    >
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            placeholder="Ask about runs, results, health…"
                            disabled={busy}
                            className="flex-1 border border-[#E0DED8] rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-[#1A4D2E]/30 disabled:opacity-50"
                        />
                        <button
                            type="submit"
                            disabled={busy || !input.trim()}
                            className="inline-flex items-center justify-center gap-1.5 px-4 py-2 bg-[#1A4D2E] text-white text-sm font-semibold rounded-full hover:bg-[#2D6B45] transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            <PaperAirplaneIcon className="h-4 w-4" />
                            Send
                        </button>
                    </form>
                </div>
            )}
        </div>
    );
};

export default ChatPanel;
