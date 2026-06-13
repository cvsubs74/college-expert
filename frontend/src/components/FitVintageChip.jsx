import { vintageChip } from '../utils/kbVintage';

/**
 * Vintage chip for a fit analysis — which admission cycle's data produced it.
 * Neutral when current, amber when a KB update is available, and silent for
 * legacy fits with no staleness info (no clutter without signal).
 */
const TONE_CLASSES = {
  current: 'bg-gray-50 text-gray-500 border-gray-200',
  stale: 'bg-amber-50 text-amber-800 border-amber-300',
  unknown: 'bg-amber-50 text-amber-800 border-amber-300',
};

export default function FitVintageChip({ fit, kbUpdate, vintageOnly = false, className = '' }) {
  const chip = vintageChip(fit, kbUpdate);
  if (!chip) return null;
  // `vintageOnly` drops the "— update available" CTA for surfaces that carry
  // the action elsewhere (the Launchpad card's "Update Fit" button). Legacy
  // fits have no vintage to state, so the chip stays silent there.
  const text = vintageOnly ? chip.vintage : chip.label;
  if (!text) return null;
  return (
    <span
      data-testid="fit-vintage-chip"
      data-tone={chip.tone}
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium border whitespace-nowrap ${TONE_CLASSES[chip.tone]} ${className}`}
    >
      {chip.tone !== 'current' && <span aria-hidden="true">🗓️</span>}
      {text}
    </span>
  );
}
