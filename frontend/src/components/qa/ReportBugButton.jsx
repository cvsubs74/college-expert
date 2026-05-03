import React, { useState } from 'react';
import { BugAntIcon } from '@heroicons/react/24/outline';
import { buildIssueUrl } from '../../services/qaAgent';

// Builds a pre-filled GitHub issue from a failing scenario and opens it
// in a new tab. The user reviews and submits manually.

const ReportBugButton = ({ runId, scenarioId, className = '' }) => {
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState(null);

    const handleClick = async () => {
        setBusy(true);
        setError(null);
        try {
            const result = await buildIssueUrl({ runId, scenarioId });
            if (result.success && result.issue_url) {
                window.open(result.issue_url, '_blank', 'noopener,noreferrer');
            } else {
                setError(result.error || 'Could not build issue URL');
            }
        } catch (err) {
            setError(err.message || 'Request failed');
        } finally {
            setBusy(false);
        }
    };

    return (
        <div className="inline-flex flex-col items-end gap-1">
            <button
                type="button"
                onClick={handleClick}
                disabled={busy}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-full border border-rose-200 text-rose-700 bg-rose-50 hover:bg-rose-100 transition-colors disabled:opacity-50 ${className}`}
            >
                <BugAntIcon className="h-3.5 w-3.5" />
                {busy ? 'Opening…' : 'Report bug'}
            </button>
            {error && (
                <span className="text-[10px] text-rose-700">{error}</span>
            )}
        </div>
    );
};

export default ReportBugButton;
