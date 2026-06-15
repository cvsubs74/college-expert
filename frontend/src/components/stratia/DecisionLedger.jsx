import React from 'react';
import { CheckCircleIcon, XCircleIcon, TrophyIcon } from '@heroicons/react/24/outline';
import {
  DECISION_OPTIONS, decisionMeta, predictedBand, calibrationOutcome, calibrationSummary,
} from '../../utils/outcomes';

const BAND_TONE = {
  Reach: 'bg-orange-50 text-orange-700 border-orange-200',
  Target: 'bg-[#E8F0E9] text-[#1A4D2E] border-[#CFE0D2]',
  Safety: 'bg-sky-50 text-sky-700 border-sky-200',
};

// Predicted-vs-actual marker per recorded decision.
const MARK = {
  match: { Icon: CheckCircleIcon, cls: 'text-emerald-600', label: 'Stratia called it' },
  beat: { Icon: TrophyIcon, cls: 'text-amber-600', label: 'You beat the odds' },
  miss: { Icon: XCircleIcon, cls: 'text-rose-500', label: 'Off the prediction' },
};

/**
 * Decision Ledger — record real admission outcomes per college and see how
 * Stratia's fit predictions held up (predicted vs actual). The calibration
 * headline is suppressed until >= 3 decisions are logged.
 *
 * @param {{ outcomes?: Array<{university_id, name, predicted, decision}>,
 *   onSetDecision?: (universityId: string, decision: string) => void }} props
 */
export default function DecisionLedger({ outcomes = [], onSetDecision }) {
  if (!outcomes.length) return null;
  const summary = calibrationSummary(outcomes);
  const remaining = Math.max(0, 3 - summary.decided);

  return (
    <div data-testid="decision-ledger" className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      <h3 className="text-base font-semibold text-gray-900">Decision Ledger</h3>
      <p className="mt-0.5 text-sm text-gray-600">
        Record where you got in — and see how Stratia&rsquo;s fit calls held up.
      </p>

      {summary.ready ? (
        <div
          data-testid="calibration-headline"
          className="mt-3 rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-2 text-sm font-medium text-indigo-800"
        >
          {summary.headline}
        </div>
      ) : (
        <p className="mt-3 text-xs text-gray-500">
          {summary.decided > 0
            ? `Record ${remaining} more decision${remaining === 1 ? '' : 's'} to see how Stratia’s calls held up.`
            : 'Add your first admission decision below — once you log 3, Stratia grades its own predictions.'}
        </p>
      )}

      <ul className="mt-3 divide-y divide-gray-100">
        {outcomes.map((o) => {
          const band = predictedBand(o.predicted);
          const dm = decisionMeta(o.decision);
          const mark = dm ? MARK[calibrationOutcome(o.predicted, o.decision)] : null;
          const MarkIcon = mark?.Icon;
          return (
            <li key={o.university_id} data-testid="ledger-row" className="flex items-center gap-2.5 py-2">
              <span className="min-w-0 flex-1 truncate text-sm font-medium text-gray-800" title={o.name}>{o.name}</span>
              {band && (
                <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[11px] font-medium ${BAND_TONE[band] || ''}`}>
                  {band}
                </span>
              )}
              {MarkIcon && <MarkIcon className={`h-4 w-4 shrink-0 ${mark.cls}`} aria-label={mark.label} title={mark.label} />}
              {onSetDecision ? (
                <select
                  aria-label={`Decision for ${o.name}`}
                  value={dm?.key || ''}
                  onChange={(e) => onSetDecision(o.university_id, e.target.value)}
                  className="shrink-0 rounded-md border border-gray-300 bg-white px-2 py-1 text-xs text-gray-700"
                >
                  {DECISION_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              ) : dm ? (
                <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[11px] font-medium ${dm.tone}`}>{dm.label}</span>
              ) : null}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
