import React from 'react';
import { Link } from 'react-router-dom';
import { ChevronRightIcon } from '@heroicons/react/24/outline';
import PassFailBadge from './PassFailBadge';

// Most-recent-first table of QA runs. Click a row → drill into detail.

const fmtDate = (iso) => {
    if (!iso) return '—';
    try {
        const d = new Date(iso);
        return d.toLocaleString(undefined, {
            month: 'short', day: 'numeric',
            hour: '2-digit', minute: '2-digit',
        });
    } catch {
        return iso;
    }
};

const fmtDuration = (ms) => {
    if (!ms) return '—';
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
};

const RunsTable = ({ runs }) => {
    if (!runs || !runs.length) {
        return (
            <div className="bg-white rounded-xl border border-[#E0DED8] p-8 text-center text-sm text-[#8A8A8A]">
                No runs yet. Click "Run now" above to kick off a batch.
            </div>
        );
    }

    return (
        <div className="bg-white rounded-xl border border-[#E0DED8] overflow-hidden">
            <table className="w-full text-sm">
                <thead className="bg-[#F8F6F0] border-b border-[#E0DED8]">
                    <tr className="text-left text-xs uppercase tracking-wider text-[#6B6B6B]">
                        <th className="px-4 py-3 font-semibold">Started</th>
                        <th className="px-4 py-3 font-semibold">Status</th>
                        <th className="px-4 py-3 font-semibold">Trigger</th>
                        <th className="px-4 py-3 font-semibold">Actor</th>
                        <th className="px-4 py-3 font-semibold">Duration</th>
                        <th className="px-4 py-3" />
                    </tr>
                </thead>
                <tbody className="divide-y divide-[#E0DED8]">
                    {runs.map((run) => (
                        <tr
                            key={run.run_id}
                            className="hover:bg-[#FBFAF6] transition-colors"
                        >
                            <td className="px-4 py-3 text-[#2A2A2A]">
                                {fmtDate(run.started_at)}
                            </td>
                            <td className="px-4 py-3">
                                <PassFailBadge summary={run.summary} />
                            </td>
                            <td className="px-4 py-3 text-[#4A4A4A]">{run.trigger || '—'}</td>
                            <td className="px-4 py-3 text-[#6B6B6B] text-xs truncate max-w-[200px]">
                                {run.actor || '—'}
                            </td>
                            <td className="px-4 py-3 text-[#4A4A4A]">{fmtDuration(run.duration_ms)}</td>
                            <td className="px-4 py-3 text-right">
                                <Link
                                    to={`/qa-runs/${run.run_id}`}
                                    className="inline-flex items-center gap-1 text-sm font-semibold text-[#1A4D2E] hover:text-[#2D6B45]"
                                >
                                    View
                                    <ChevronRightIcon className="h-4 w-4" />
                                </Link>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

export default RunsTable;
