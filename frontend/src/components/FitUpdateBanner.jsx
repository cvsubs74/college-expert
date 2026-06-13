import { useState } from 'react';
import { ArrowPathIcon } from '@heroicons/react/24/outline';
import { cycleLabel } from '../utils/kbVintage';

/**
 * In-context "newer admissions data is available" banner for the Fit Analysis
 * detail view. Lets a student read the CURRENT analysis and then recompute it
 * in place, with the old→new data cycle spelled out. Renders nothing when the
 * fit is current.
 */
export default function FitUpdateBanner({ kbUpdate, onUpdate }) {
  const [updating, setUpdating] = useState(false);
  const [failed, setFailed] = useState(false);

  if (!kbUpdate) return null;

  const fromLabel = cycleLabel(kbUpdate.fit_kb_year);
  const toLabel = cycleLabel(kbUpdate.current_kb_year);
  const fromText = fromLabel
    ? `This analysis is based on ${fromLabel} data`
    : 'This analysis predates data versioning';

  const handleUpdate = async () => {
    if (updating) return;
    setFailed(false);
    setUpdating(true);
    try {
      await onUpdate?.();
      // On success the parent swaps in the refreshed fit and drops kbUpdate,
      // so this banner unmounts — no need to reset local state.
    } catch (err) {
      console.error('[FitUpdateBanner] update failed:', err);
      setUpdating(false);
      setFailed(true);
    }
  };

  return (
    <div
      data-testid="fit-update-banner"
      className="max-w-6xl mx-auto px-4 pt-4"
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3">
        <div className="flex items-start gap-2.5">
          <span className="text-lg leading-none" aria-hidden="true">🗓️</span>
          <div className="text-sm">
            <p className="font-medium text-amber-900">{fromText}</p>
            <p className="text-amber-700">
              {toLabel
                ? `Newer ${toLabel} admissions data is available — refresh for an up-to-date assessment.`
                : 'Newer admissions data is available — refresh for an up-to-date assessment.'}
            </p>
            {failed && (
              <p className="mt-1 text-red-600" role="alert">
                Update failed — please try again.
              </p>
            )}
          </div>
        </div>
        <button
          onClick={handleUpdate}
          disabled={updating}
          className="shrink-0 inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-amber-500 text-white text-sm font-medium hover:bg-amber-600 transition-all shadow-sm disabled:cursor-wait"
        >
          <ArrowPathIcon className={`h-4 w-4 ${updating ? 'animate-spin' : ''}`} />
          {updating ? 'Updating…' : 'Update analysis'}
        </button>
      </div>
    </div>
  );
}
