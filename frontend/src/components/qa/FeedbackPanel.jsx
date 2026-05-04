import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ChatBubbleBottomCenterTextIcon, XMarkIcon, ArrowPathIcon } from '@heroicons/react/24/outline';
import { getFeedback, addFeedback, dismissFeedback } from '../../services/qaAgent';

// Admin-authored notes that steer the next scheduled run's synthesizer.
//
// Spec: docs/prd/qa-feedback-loop.md, docs/design/qa-feedback-loop.md.
//
// Each item: {id, text, status, applied_count, max_applies,
//             last_applied_run_id, last_applied_at}
//
// Items auto-dismiss after `max_applies` runs reference them. Admin can
// dismiss any item early via the X button.

const MAX_ACTIVE = 10;
const MIN_TEXT = 5;
const MAX_TEXT = 500;
const DEFAULT_MAX_APPLIES = 5;
// Mirrors backend feedback.MAX_APPLIES_BOUND. The "Never" UI option
// maps to this value so the operator can author persistent steers
// that only retire on manual dismiss.
const NEVER_AUTO_RETIRE = 99;
const MAX_APPLIES_OPTIONS = [
    { value: 1, label: '1 run' },
    { value: 3, label: '3 runs' },
    { value: 5, label: '5 runs (default)' },
    { value: 10, label: '10 runs' },
    { value: 20, label: '20 runs' },
    { value: NEVER_AUTO_RETIRE, label: 'Never' },
];

const FeedbackPanel = () => {
    const [items, setItems] = useState([]);
    // Most-recent-N retired items so the operator can see "the
    // feedback I left actually drove runs and auto-retired" — without
    // this, an item that hits max_applies just disappears from the
    // panel and the loop looks broken from the outside.
    const [dismissed, setDismissed] = useState([]);
    const [draft, setDraft] = useState('');
    // Per-item auto-retire threshold the operator picks before
    // submitting. Default mirrors the backend's DEFAULT_MAX_APPLIES.
    const [maxApplies, setMaxApplies] = useState(DEFAULT_MAX_APPLIES);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState(null);
    const [submitting, setSubmitting] = useState(false);

    const refresh = async () => {
        setBusy(true);
        setError(null);
        try {
            const resp = await getFeedback();
            if (resp?.success) {
                setItems(resp.items || []);
                setDismissed(resp.recently_dismissed || []);
            } else {
                setError(resp?.error || "couldn't load feedback");
            }
        } catch (err) {
            setError(err.message || "couldn't load feedback");
        } finally {
            setBusy(false);
        }
    };

    useEffect(() => { refresh(); }, []);

    const submitFeedback = async (e) => {
        e?.preventDefault?.();
        const trimmed = draft.trim();
        if (trimmed.length < MIN_TEXT) {
            setError(`feedback must be at least ${MIN_TEXT} characters`);
            return;
        }
        setSubmitting(true);
        setError(null);
        try {
            const resp = await addFeedback({
                text: trimmed,
                max_applies: maxApplies,
            });
            if (resp?.success) {
                setDraft('');
                setMaxApplies(DEFAULT_MAX_APPLIES);
                await refresh();
            } else {
                setError(resp?.error || "couldn't save feedback");
            }
        } catch (err) {
            setError(err.message || "couldn't save feedback");
        } finally {
            setSubmitting(false);
        }
    };

    const handleDismiss = async (id) => {
        try {
            await dismissFeedback(id);
            await refresh();
        } catch (err) {
            setError(err.message || "couldn't dismiss");
        }
    };

    const activeCount = items.length;
    const atCap = activeCount >= MAX_ACTIVE;

    return (
        <div className="bg-white border border-[#E0DED8] rounded-xl p-5">
            <div className="flex items-baseline justify-between mb-3 gap-2 flex-wrap">
                <h2 className="text-sm font-bold uppercase tracking-wider text-[#1A4D2E] flex items-center gap-2">
                    <ChatBubbleBottomCenterTextIcon className="h-4 w-4" />
                    Feedback to the QA agent
                </h2>
                <span className="text-xs text-[#8A8A8A]">
                    {activeCount} of {MAX_ACTIVE} active
                </span>
            </div>

            <p className="text-xs text-[#6B6B6B] mb-3">
                Anything you type here gets included in the next scheduled run's
                scenario design. Each item carries its own auto-retire limit
                (default 5 runs) — pick "Never" for persistent steers and
                retire manually via the X button when you're done.
            </p>

            <form onSubmit={submitFeedback} className="mb-4">
                <textarea
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    placeholder='e.g. "Focus on essay tracker after the recent ship."'
                    disabled={submitting || atCap}
                    rows={2}
                    maxLength={MAX_TEXT}
                    className="w-full border border-[#E0DED8] rounded-lg px-3 py-2 text-sm bg-[#FBFAF6] focus:outline-none focus:ring-2 focus:ring-[#1A4D2E]/30 resize-none disabled:opacity-50"
                />
                <div className="flex items-center justify-between mt-2 gap-3 flex-wrap">
                    <span className="text-[10px] text-[#8A8A8A]">
                        {draft.length}/{MAX_TEXT}
                        {atCap && ' · cap reached, dismiss an item to add more'}
                    </span>
                    <div className="flex items-center gap-3">
                        <label className="flex items-center gap-1.5 text-[11px] text-[#6B6B6B]">
                            <span>Expires after:</span>
                            <select
                                aria-label="Expires after"
                                value={String(maxApplies)}
                                onChange={(e) => setMaxApplies(Number(e.target.value))}
                                disabled={submitting || atCap}
                                className="border border-[#E0DED8] rounded-md bg-[#FBFAF6] px-2 py-1 text-[11px] focus:outline-none focus:ring-2 focus:ring-[#1A4D2E]/30 disabled:opacity-50"
                            >
                                {MAX_APPLIES_OPTIONS.map((opt) => (
                                    <option key={opt.value} value={String(opt.value)}>
                                        {opt.label}
                                    </option>
                                ))}
                            </select>
                        </label>
                        <button
                            type="submit"
                            disabled={submitting || atCap || draft.trim().length < MIN_TEXT}
                            className="px-4 py-1.5 bg-[#1A4D2E] text-white text-xs font-semibold rounded-full hover:bg-[#2D6B45] transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {submitting ? 'Saving…' : 'Submit'}
                        </button>
                    </div>
                </div>
            </form>

            {error && (
                <div className="mb-3 text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2">
                    {error}
                </div>
            )}

            {busy && items.length === 0 ? (
                <div className="text-xs text-[#8A8A8A] flex items-center gap-2">
                    <ArrowPathIcon className="h-3.5 w-3.5 animate-spin" />
                    Loading…
                </div>
            ) : items.length === 0 ? (
                <p className="text-xs text-[#8A8A8A] italic">
                    No active feedback. Add a note above to steer the next run.
                </p>
            ) : (
                <ul className="space-y-2">
                    {items.map((it) => (
                        <li
                            key={it.id}
                            className="flex items-start justify-between gap-3 bg-[#FBFAF6] border border-[#E0DED8] rounded-lg p-3"
                        >
                            <div className="flex-1 min-w-0">
                                <div className="flex items-start gap-2">
                                    <p className="text-sm text-[#1A2E1F] flex-1 min-w-0">
                                        {it.text}
                                    </p>
                                    {(it.applied_count ?? 0) > 0 && (
                                        <span
                                            aria-label="applied to a run"
                                            className="flex-shrink-0 text-[10px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-1.5 py-0.5 rounded"
                                        >
                                            ✓ applied
                                        </span>
                                    )}
                                </div>
                                <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 mt-1 text-[10px] text-[#6B6B6B]">
                                    <span className="font-mono">{it.id}</span>
                                    <span>·</span>
                                    <span>
                                        applied {it.applied_count ?? 0}/{it.max_applies ?? 5}
                                    </span>
                                    {it.last_applied_run_id && (
                                        <>
                                            <span>·</span>
                                            <Link
                                                to={`/qa-runs/${it.last_applied_run_id}`}
                                                className="font-mono truncate text-[#1A4D2E] hover:underline"
                                            >
                                                last: {it.last_applied_run_id}
                                            </Link>
                                        </>
                                    )}
                                </div>
                            </div>
                            <button
                                type="button"
                                onClick={() => handleDismiss(it.id)}
                                aria-label={`Dismiss ${it.id}`}
                                className="flex-shrink-0 p-1 rounded-full text-[#8A8A8A] hover:text-rose-700 hover:bg-rose-50"
                            >
                                <XMarkIcon className="h-4 w-4" />
                            </button>
                        </li>
                    ))}
                </ul>
            )}

            {dismissed.length > 0 && (
                <div className="mt-5 pt-4 border-t border-[#E0DED8]">
                    <div className="flex items-baseline justify-between mb-2">
                        <h3 className="text-[10px] uppercase tracking-wider text-[#6B6B6B] font-semibold">
                            Retired
                        </h3>
                        <span className="text-[10px] text-[#8A8A8A]">
                            {dismissed.length} most recent
                        </span>
                    </div>
                    <p className="text-[11px] text-[#6B6B6B] mb-2">
                        Notes that already drove runs and auto-retired.
                    </p>
                    <ul className="space-y-2">
                        {dismissed.map((it) => (
                            <li
                                key={it.id}
                                className="flex items-start justify-between gap-3 bg-[#FBFAF6] border border-[#E0DED8] rounded-lg p-3 opacity-90"
                            >
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-start gap-2">
                                        <p className="text-sm text-[#4A4A4A] flex-1 min-w-0">
                                            {it.text}
                                        </p>
                                        <span
                                            aria-label="retired"
                                            className="flex-shrink-0 text-[10px] font-semibold text-[#6B6B6B] bg-[#F1EFE8] border border-[#E0DED8] px-1.5 py-0.5 rounded whitespace-nowrap"
                                        >
                                            ✓ retired after {it.applied_count ?? 0} runs
                                        </span>
                                    </div>
                                    <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 mt-1 text-[10px] text-[#8A8A8A]">
                                        <span className="font-mono">{it.id}</span>
                                        {it.last_applied_run_id && (
                                            <>
                                                <span>·</span>
                                                <Link
                                                    to={`/qa-runs/${it.last_applied_run_id}`}
                                                    className="font-mono truncate text-[#1A4D2E] hover:underline"
                                                >
                                                    last: {it.last_applied_run_id}
                                                </Link>
                                            </>
                                        )}
                                    </div>
                                </div>
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
};

export default FeedbackPanel;
