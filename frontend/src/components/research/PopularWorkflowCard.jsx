import React from 'react';
import { FireIcon, SparklesIcon } from '@heroicons/react/24/outline';
import { FireIcon as FireSolidIcon } from '@heroicons/react/24/solid';
import { popularWorkflowName, popularWorkflowPrompt, toolLabel, workflowTrend, isNewToUser } from '../../utils/research';
import { askLinks } from '../../utils/mcpClients';
import AgentLaunchButtons from '../AgentLaunchButtons';

/**
 * One cross-user popular workflow (aggregate, PII-free): a reusable algorithm
 * surfaced by how often it's been run. Shows the generic steps + a one-click
 * "Run" that re-runs it for the current user in their AI agent. Flags
 * "Trending" (a week-over-week jump) and "New to you" (the user hasn't run it).
 *
 * @param {{ wf: {signature, tools?, kind, count, weeks?}, ownSignatures?: Set<string>,
 *   profile?: object, collegeList?: object[] }} props
 */
export default function PopularWorkflowCard({ wf, ownSignatures, profile, collegeList }) {
  const tools = (Array.isArray(wf.tools) && wf.tools.length)
    ? wf.tools
    : String(wf.signature || '').split('>').filter(Boolean);
  // Personalize the launch prompt client-side (guarded; the aggregate is untouched).
  const links = askLinks(popularWorkflowPrompt(wf, { profile, collegeList }));
  const count = wf.count || 0;
  const { trending } = workflowTrend(wf);
  const isNew = isNewToUser(wf, ownSignatures);

  return (
    <div data-testid="popular-workflow" data-trending={trending ? 'true' : 'false'} className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="inline-flex items-center gap-1 rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-800">
              <FireIcon className="h-3.5 w-3.5" /> Popular
            </span>
            {trending && (
              <span data-testid="trending-badge" className="inline-flex items-center gap-1 rounded-full border border-orange-300 bg-orange-100 px-2 py-0.5 text-[11px] font-semibold text-orange-700">
                <FireSolidIcon className="h-3.5 w-3.5" /> Trending
              </span>
            )}
            {isNew && (
              <span data-testid="new-to-you-chip" className="inline-flex items-center gap-1 rounded-full border border-indigo-200 bg-indigo-50 px-2 py-0.5 text-[11px] font-medium text-indigo-700">
                <SparklesIcon className="h-3.5 w-3.5" /> New to you
              </span>
            )}
          </div>
          <h3 className="mt-2 text-base font-semibold text-gray-900">{popularWorkflowName(wf)}</h3>
          <p className="mt-0.5 text-xs text-gray-500">Run {count} time{count === 1 ? '' : 's'} · {tools.length} step{tools.length === 1 ? '' : 's'}</p>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-1.5">
          <AgentLaunchButtons links={links} verb="Run" size="sm" />
        </div>
      </div>

      {tools.length > 0 && (
        <ol className="mt-3 flex flex-wrap items-center gap-1.5 text-xs text-gray-600">
          {tools.map((t, i) => (
            <li key={i} className="flex items-center gap-1.5">
              <span className="rounded-md bg-gray-100 px-2 py-0.5 font-medium text-gray-700">{toolLabel(t)}</span>
              {i < tools.length - 1 && <span className="text-gray-300" aria-hidden="true">→</span>}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
