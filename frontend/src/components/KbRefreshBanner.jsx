import { useState } from 'react';
import { materialUpdates, cycleLabel } from '../utils/kbVintage';

/**
 * The yearly-refresh moment (design §3a): one dismissible banner when
 * university data for a new admission cycle materially changed something
 * on the student's list. Renders nothing for minor-only changes or when
 * every affected college is nudge-suppressed (already applied).
 *
 * Dismissal is remembered per cycle year in localStorage so the banner
 * doesn't re-nag — the vintage chips carry the state from then on.
 */
export default function KbRefreshBanner({ kbUpdates, onReview }) {
  const material = materialUpdates(kbUpdates);
  const year = material[0]?.current_kb_year;
  const storageKey = `kb_refresh_banner_dismissed_${year}`;

  const [dismissedNow, setDismissedNow] = useState(false);

  // Read the stored flag at render time, not in a lazy useState init —
  // kbUpdates often arrives after mount (parallel fetch), and a
  // mount-time read with year=undefined would forget prior dismissals.
  let storedDismissal = false;
  try {
    storedDismissal = year != null && localStorage.getItem(storageKey) === '1';
  } catch { /* private mode — banner just reappears next session */ }

  if (!material.length || dismissedNow || storedDismissal) return null;

  const label = cycleLabel(year);
  const n = material.length;

  const dismiss = () => {
    try {
      if (year != null) localStorage.setItem(storageKey, '1');
    } catch { /* private mode — banner just reappears next session */ }
    setDismissedNow(true);
  };

  return (
    <div
      data-testid="kb-refresh-banner"
      className="rounded-2xl border border-[#E8A090] bg-gradient-to-r from-[#FEF7F0] to-[#FCEEE8] p-4 mb-4 flex items-start gap-3"
    >
      <span className="text-xl" aria-hidden="true">🗓️</span>
      <div className="flex-1 min-w-0">
        <p className="font-semibold text-[#1A4D2E]">
          {label ? `${label} admissions data is in.` : 'New admissions data is in.'}
        </p>
        <p className="text-sm text-gray-700 mt-0.5">
          {n === 1
            ? '1 college on your list changed in ways that may affect your fit.'
            : `${n} colleges on your list changed in ways that may affect your fit.`}
        </p>
      </div>
      <div className="flex items-center gap-2 flex-shrink-0">
        <button
          onClick={onReview}
          className="bg-[#1A4D2E] text-white px-4 py-2 rounded-full text-sm font-medium hover:bg-[#2D6B45] transition-colors"
        >
          Review what changed
        </button>
        <button
          onClick={dismiss}
          aria-label="Dismiss"
          className="text-gray-400 hover:text-gray-600 px-2 py-1 text-sm"
        >
          Later
        </button>
      </div>
    </div>
  );
}
