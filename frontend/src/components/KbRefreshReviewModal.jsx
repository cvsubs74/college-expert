import { useState } from 'react';
import { XMarkIcon, ArrowPathIcon, CheckIcon } from '@heroicons/react/24/outline';
import { describeChange, cycleLabel } from '../utils/kbVintage';

/**
 * Review screen for a KB cycle refresh (design §3b): one card per affected
 * college with the concrete old→new facts and the projected fit impact.
 * The student applies updates — per college or all at once; we never swap
 * their plan silently.
 *
 * Props:
 *   isOpen, onClose
 *   kbUpdates      — entries from check-fit-recomputation (already filtered
 *                    to the colleges worth reviewing by the parent)
 *   onUpdateFit    — async (universityId) => recompute + persist one fit
 *   onAllUpdated   — called after every update completes (refresh fits)
 */
export default function KbRefreshReviewModal({
  isOpen,
  onClose,
  kbUpdates,
  onUpdateFit,
  onAllUpdated,
}) {
  // per-university: 'pending' | 'updating' | 'done' | 'error'
  const [status, setStatus] = useState({});
  const [updatingAll, setUpdatingAll] = useState(false);

  if (!isOpen) return null;

  const updates = (kbUpdates || []).filter((u) => !u.nudge_suppressed);

  const runOne = async (universityId) => {
    setStatus((s) => ({ ...s, [universityId]: 'updating' }));
    try {
      await onUpdateFit(universityId);
      setStatus((s) => ({ ...s, [universityId]: 'done' }));
      return true;
    } catch {
      setStatus((s) => ({ ...s, [universityId]: 'error' }));
      return false;
    }
  };

  const runAll = async () => {
    setUpdatingAll(true);
    for (const u of updates) {
      if (status[u.university_id] !== 'done') {
        // sequential on purpose: each recompute is an LLM call
        // eslint-disable-next-line no-await-in-loop
        await runOne(u.university_id);
      }
    }
    setUpdatingAll(false);
    onAllUpdated?.();
  };

  const yearLabel = cycleLabel(updates[0]?.current_kb_year);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40" data-testid="kb-refresh-review-modal">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-100">
          <div>
            <h2 className="text-xl font-bold text-gray-900">
              What changed{yearLabel ? ` for ${yearLabel}` : ''}
            </h2>
            <p className="text-sm text-gray-500 mt-0.5">
              Your saved fit analyses were computed on last cycle&apos;s data.
              Update them when you&apos;re ready — the previous analysis is kept.
            </p>
          </div>
          <button onClick={onClose} aria-label="Close" className="text-gray-400 hover:text-gray-600">
            <XMarkIcon className="h-6 w-6" />
          </button>
        </div>

        {/* Cards */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {updates.map((u) => {
            const st = status[u.university_id] || 'pending';
            return (
              <div
                key={u.university_id}
                className="border border-gray-200 rounded-xl p-4"
                data-testid={`kb-update-card-${u.university_id}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h3 className="font-semibold text-gray-900">{u.university_name || u.university_id}</h3>
                    <ul className="mt-2 space-y-1">
                      {(u.changes || []).map((c, i) => (
                        <li key={i} className="text-sm text-gray-700 flex items-center gap-2">
                          <span
                            className={`inline-block w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                              c.severity === 'material' ? 'bg-[#C05838]' : 'bg-gray-300'
                            }`}
                          />
                          {describeChange(c)}
                        </li>
                      ))}
                    </ul>
                    {u.projected_category_shift && (
                      <p className="mt-2 text-sm font-medium text-[#C05838]">
                        Projected fit: {u.projected_category_shift.replace('→', '→')}
                      </p>
                    )}
                  </div>
                  <div className="flex-shrink-0">
                    {st === 'done' ? (
                      <span className="inline-flex items-center gap-1 text-sm font-medium text-green-700">
                        <CheckIcon className="h-4 w-4" /> Updated
                      </span>
                    ) : (
                      <button
                        onClick={() => runOne(u.university_id)}
                        disabled={st === 'updating' || updatingAll}
                        className="inline-flex items-center gap-1.5 border border-[#1A4D2E] text-[#1A4D2E] px-3 py-1.5 rounded-full text-sm font-medium hover:bg-[#D6E8D5] disabled:opacity-50 transition-colors"
                      >
                        <ArrowPathIcon className={`h-4 w-4 ${st === 'updating' ? 'animate-spin' : ''}`} />
                        {st === 'updating' ? 'Updating…' : st === 'error' ? 'Retry' : 'Update fit analysis'}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
          {!updates.length && (
            <p className="text-sm text-gray-500 text-center py-8">
              Nothing needs your attention — all fit analyses are current.
            </p>
          )}
        </div>

        {/* Footer */}
        {updates.length > 1 && (
          <div className="p-4 border-t border-gray-100 flex justify-end gap-3">
            <button onClick={onClose} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900">
              Close
            </button>
            <button
              onClick={runAll}
              disabled={updatingAll}
              className="bg-[#1A4D2E] text-white px-5 py-2 rounded-full text-sm font-medium hover:bg-[#2D6B45] disabled:opacity-60"
            >
              {updatingAll ? 'Updating all…' : 'Update all'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
