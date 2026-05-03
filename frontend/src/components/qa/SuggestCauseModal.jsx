import React, { useEffect, useState } from 'react';
import { XMarkIcon, LightBulbIcon } from '@heroicons/react/24/outline';
import ReactMarkdown from 'react-markdown';
import { suggestCause } from '../../services/qaAgent';

// Modal shown when admin clicks "Suggest cause" on a failing scenario.
// Calls qa-agent /suggest-cause and renders the markdown response.

const SuggestCauseModal = ({ runId, scenarioId, onClose }) => {
    const [loading, setLoading] = useState(true);
    const [suggestion, setSuggestion] = useState(null);
    const [error, setError] = useState(null);
    const [cached, setCached] = useState(false);

    useEffect(() => {
        let cancelled = false;
        setLoading(true);
        suggestCause({ runId, scenarioId })
            .then((data) => {
                if (cancelled) return;
                if (data.success) {
                    setSuggestion(data.suggestion);
                    setCached(!!data.cached);
                } else {
                    setError(data.error || 'No suggestion produced');
                }
            })
            .catch((err) => {
                if (cancelled) return;
                setError(err.message || 'Request failed');
            })
            .finally(() => {
                if (!cancelled) setLoading(false);
            });
        return () => { cancelled = true; };
    }, [runId, scenarioId]);

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
            <div className="bg-white rounded-2xl shadow-xl max-w-2xl w-full max-h-[80vh] flex flex-col overflow-hidden">
                <header className="flex items-start justify-between gap-3 px-5 py-4 border-b border-[#E0DED8]">
                    <div className="flex items-center gap-2">
                        <LightBulbIcon className="h-5 w-5 text-amber-500" />
                        <div>
                            <h2 className="text-lg font-bold text-[#1A2E1F]">Suggested cause</h2>
                            <p className="text-xs text-[#8A8A8A] font-mono">
                                {scenarioId} · {runId}
                            </p>
                        </div>
                    </div>
                    <button
                        type="button"
                        onClick={onClose}
                        className="text-[#8A8A8A] hover:text-[#1A4D2E]"
                        aria-label="Close"
                    >
                        <XMarkIcon className="h-5 w-5" />
                    </button>
                </header>

                <div className="px-5 py-4 overflow-y-auto flex-1">
                    {loading && (
                        <div className="text-sm text-[#6B6B6B]">Analyzing failure…</div>
                    )}
                    {error && (
                        <div className="text-sm text-rose-700 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2">
                            {error}
                        </div>
                    )}
                    {suggestion && (
                        <div className="prose prose-sm prose-emerald max-w-none">
                            <ReactMarkdown>{suggestion}</ReactMarkdown>
                        </div>
                    )}
                </div>

                <footer className="px-5 py-3 border-t border-[#E0DED8] flex items-center justify-between bg-[#FBFAF6]">
                    <span className="text-[11px] text-[#8A8A8A] italic">
                        AI guess — verify against the failing step before acting.
                        {cached && ' (cached from earlier this session)'}
                    </span>
                    <button
                        type="button"
                        onClick={onClose}
                        className="px-4 py-1.5 text-sm font-semibold text-[#1A4D2E] hover:bg-[#F2EFE6] rounded-lg"
                    >
                        Close
                    </button>
                </footer>
            </div>
        </div>
    );
};

export default SuggestCauseModal;
