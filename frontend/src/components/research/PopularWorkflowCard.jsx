import React from 'react';
import { PlayIcon, FireIcon } from '@heroicons/react/24/outline';
import { popularWorkflowName, popularWorkflowPrompt, toolLabel } from '../../utils/research';
import { askLinks } from '../../utils/mcpClients';

/**
 * One cross-user popular workflow (aggregate, PII-free): a reusable algorithm
 * surfaced by how often it's been run. Shows the generic steps + a one-click
 * "Run" that re-runs it for the current user in their AI agent.
 *
 * @param {{ wf: {signature, tools?, kind, count} }} props
 */
export default function PopularWorkflowCard({ wf }) {
  const tools = (Array.isArray(wf.tools) && wf.tools.length)
    ? wf.tools
    : String(wf.signature || '').split('>').filter(Boolean);
  const links = askLinks(popularWorkflowPrompt(wf));
  const count = wf.count || 0;

  return (
    <div data-testid="popular-workflow" className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <span className="inline-flex items-center gap-1 rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-800">
            <FireIcon className="h-3.5 w-3.5" /> Popular
          </span>
          <h3 className="mt-2 text-base font-semibold text-gray-900">{popularWorkflowName(wf)}</h3>
          <p className="mt-0.5 text-xs text-gray-500">Run {count} time{count === 1 ? '' : 's'} · {tools.length} step{tools.length === 1 ? '' : 's'}</p>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          <a href={links.claude} target="_blank" rel="noreferrer"
            className="inline-flex items-center gap-1 rounded-md bg-[#1A4D2E] px-2.5 py-1.5 text-xs font-medium text-white hover:bg-[#2D6B45]">
            <PlayIcon className="h-3.5 w-3.5" /> Run in Claude
          </a>
          <a href={links.chatgpt} target="_blank" rel="noreferrer"
            className="inline-flex items-center gap-1 rounded-md border border-gray-300 bg-white px-2.5 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50">
            <PlayIcon className="h-3.5 w-3.5" /> ChatGPT
          </a>
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
