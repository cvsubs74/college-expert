import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { PlayIcon, ChevronDownIcon, ChevronRightIcon, Squares2X2Icon } from '@heroicons/react/24/outline';
import { repeatPrompt, formatDate, kindMeta } from '../../utils/research';
import { askLinks } from '../../utils/mcpClients';

/**
 * One reusable workflow ("custom algorithm") and everything it produced.
 * Shows HOW it works (the ordered steps) and WHAT it produced (the researches),
 * plus a one-click "Run again" in the user's AI agent.
 *
 * @param {{ group: {name,steps,representative,researches}, collegeNames?: object }} props
 */
export default function WorkflowGroupCard({ group }) {
  const [showSteps, setShowSteps] = useState(false);
  const [openId, setOpenId] = useState(null);
  const links = askLinks(repeatPrompt(group.representative));
  const runs = group.researches.length;

  return (
    <div data-testid="workflow-group" className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <span className="inline-flex items-center gap-1 rounded-full border border-indigo-200 bg-indigo-50 px-2 py-0.5 text-[11px] font-medium text-indigo-700">
            <Squares2X2Icon className="h-3.5 w-3.5" /> Workflow
          </span>
          <h3 className="mt-2 text-base font-semibold text-gray-900">{group.name}</h3>
          <p className="mt-0.5 text-xs text-gray-500">
            Produced {runs} research{runs === 1 ? '' : 'es'} · {group.steps.length} step{group.steps.length === 1 ? '' : 's'}
          </p>
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

      {/* HOW: the steps */}
      {group.steps.length > 0 && (
        <div className="mt-3">
          <button type="button" onClick={() => setShowSteps((v) => !v)} aria-expanded={showSteps}
            className="inline-flex items-center gap-1 text-xs font-semibold uppercase tracking-wide text-gray-500 hover:text-gray-700">
            {showSteps ? <ChevronDownIcon className="h-3.5 w-3.5" /> : <ChevronRightIcon className="h-3.5 w-3.5" />}
            How it works
          </button>
          {showSteps && (
            <ol className="mt-2 list-decimal space-y-1 pl-5 text-xs text-gray-600 marker:text-gray-400">
              {group.steps.map((s, i) => (
                <li key={i}>{s.label}{s.tool ? <span className="ml-1 text-gray-400">({s.tool})</span> : null}</li>
              ))}
            </ol>
          )}
        </div>
      )}

      {/* WHAT: the produced researches */}
      <div className="mt-3 border-t border-gray-100 pt-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Produced</p>
        <ul className="mt-1.5 divide-y divide-gray-100">
          {group.researches.map((r) => {
            const meta = kindMeta(r.kind);
            const open = openId === r.research_id;
            return (
              <li key={r.research_id} data-testid="workflow-output">
                <button type="button" onClick={() => setOpenId(open ? null : r.research_id)} aria-expanded={open}
                  className="flex w-full items-center gap-2 py-2 text-left hover:bg-gray-50">
                  {open ? <ChevronDownIcon className="h-4 w-4 shrink-0 text-gray-400" /> : <ChevronRightIcon className="h-4 w-4 shrink-0 text-gray-400" />}
                  <span className="text-xs" aria-hidden="true">{meta.emoji}</span>
                  <span className="min-w-0 flex-1 truncate text-sm text-gray-800" title={r.title}>{r.title || 'Untitled'}</span>
                  <span className="shrink-0 text-[11px] text-gray-400">{formatDate(r.created_at)}</span>
                </button>
                {open && (
                  <div className="prose prose-sm mb-2 ml-6 max-w-none rounded-lg bg-gray-50 p-3 prose-p:my-1.5">
                    {r.summary && <p className="not-prose mb-2 text-xs italic text-gray-500">{r.summary}</p>}
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{r.body_markdown || '_No details._'}</ReactMarkdown>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
