import React from 'react';
import { PlayIcon } from '@heroicons/react/24/outline';
import { balanceSegments, balanceVerdict } from '../../utils/listBalance';

const TONE = {
  good: { wrap: 'border-emerald-200 bg-emerald-50', head: 'text-emerald-800', dot: 'bg-emerald-500' },
  warn: { wrap: 'border-amber-200 bg-amber-50', head: 'text-amber-800', dot: 'bg-amber-500' },
  info: { wrap: 'border-gray-200 bg-white', head: 'text-gray-800', dot: 'bg-gray-400' },
};

const R = 42;
const CIRC = 2 * Math.PI * R;

/**
 * A compact reach/target/safety donut + verdict for the college list. Purely
 * presentational — it renders whatever counts it's given (the Launchpad gates
 * on having enough categorized colleges) and offers a "Fix my balance" hand-off
 * to the connected agent.
 *
 * @param {{reach?:number, target?:number, safety?:number, estimated?:number,
 *   fixLinks?: {claude?: string, chatgpt?: string}}} props
 */
export default function BalanceRing({ reach = 0, target = 0, safety = 0, estimated = 0, fixLinks }) {
  const total = reach + target + safety;
  if (total === 0) return null;

  const segments = balanceSegments({ reach, target, safety });
  const verdict = balanceVerdict({ reach, target, safety });
  const tone = TONE[verdict.tone] || TONE.info;

  // Lay the non-empty segments around the ring, starting at 12 o'clock.
  let acc = 0;
  const arcs = segments
    .filter((s) => s.count > 0)
    .map((s) => {
      const len = s.fraction * CIRC;
      const arc = { color: s.color, len, offset: -acc };
      acc += len;
      return arc;
    });

  return (
    <div
      data-testid="balance-ring"
      className={`flex flex-col items-center gap-4 rounded-xl border p-4 shadow-sm sm:flex-row sm:items-center sm:gap-5 ${tone.wrap}`}
    >
      <div className="relative h-28 w-28 shrink-0">
        <svg viewBox="0 0 100 100" className="h-full w-full -rotate-90">
          <circle cx="50" cy="50" r={R} fill="none" stroke="#E5E7EB" strokeWidth="14" />
          {arcs.map((a, i) => (
            <circle
              key={i}
              cx="50"
              cy="50"
              r={R}
              fill="none"
              stroke={a.color}
              strokeWidth="14"
              strokeDasharray={`${a.len} ${CIRC - a.len}`}
              strokeDashoffset={a.offset}
            />
          ))}
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-bold text-gray-900">{total}</span>
          <span className="text-[11px] font-medium text-gray-500">school{total === 1 ? '' : 's'}</span>
        </div>
      </div>

      <div className="min-w-0 flex-1 text-center sm:text-left">
        <h3 data-testid="balance-verdict" className={`text-base font-semibold ${tone.head}`}>{verdict.headline}</h3>
        <p className="mt-0.5 text-sm text-gray-600">{verdict.detail}</p>

        <div className="mt-2 flex flex-wrap items-center justify-center gap-x-3 gap-y-1 text-xs text-gray-600 sm:justify-start">
          {segments.map((s) => (
            <span key={s.key} className="inline-flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: s.color }} aria-hidden="true" />
              <span className="font-medium text-gray-700">{s.count}</span> {s.label}
            </span>
          ))}
        </div>

        <p className="mt-1 text-[11px] text-gray-400">
          Based on your current fits{estimated > 0 ? ` · ${estimated} estimated from admit rates` : ''}
        </p>

        {fixLinks && (verdict.tone === 'warn') && (
          <div className="mt-3 flex flex-wrap items-center justify-center gap-1.5 sm:justify-start">
            <span className="text-xs font-medium text-gray-600">Fix my balance:</span>
            {fixLinks.claude && (
              <a
                href={fixLinks.claude}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 rounded-md bg-[#1A4D2E] px-2.5 py-1 text-xs font-medium text-white hover:bg-[#2D6B45]"
              >
                <PlayIcon className="h-3.5 w-3.5" /> Claude
              </a>
            )}
            {fixLinks.chatgpt && (
              <a
                href={fixLinks.chatgpt}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 rounded-md border border-gray-300 bg-white px-2.5 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50"
              >
                <PlayIcon className="h-3.5 w-3.5" /> ChatGPT
              </a>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
