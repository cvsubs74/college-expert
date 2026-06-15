import React from 'react';
import { Link } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { PlayIcon, ArrowPathIcon, SparklesIcon } from '@heroicons/react/24/outline';
import { researchProvenance } from '../../utils/research';

/**
 * "This week" banner — the agent-authored weekly action card pinned to the top
 * of the Research Notebook. Shows the latest `weekly_plan` note (≤3 next
 * actions) with a one-tap refresh, or a cold-start prompt to generate the first
 * one. Purely presentational: the parent selects the plan and passes the
 * re-run links (the app never runs the agent itself).
 *
 * @param {{ plan?: object|null, promptLinks?: {claude?: string, chatgpt?: string} }} props
 */
export default function WeeklyPlanBanner({ plan, promptLinks = {} }) {
  // Cold start — no weekly plan yet. Nudge the student to ask their agent.
  if (!plan) {
    return (
      <div
        data-testid="weekly-plan-empty"
        className="mt-4 rounded-xl border border-dashed border-teal-300 bg-teal-50/60 p-4"
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <h2 className="flex items-center gap-1.5 text-sm font-semibold text-teal-900">
              <SparklesIcon className="h-4 w-4" /> This week’s 3 things
            </h2>
            <p className="mt-0.5 text-sm text-teal-800/80">
              Ask your connected agent for the 3 most important things to do this week — it’ll pin them here.
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-1.5">
            <RunLinks promptLinks={promptLinks} verb="Get my plan" />
          </div>
        </div>
        <p className="mt-2 text-[11px] text-teal-700/70">
          No agent yet?{' '}
          <Link to="/connect" className="font-medium underline hover:text-teal-900">Connect Claude or ChatGPT</Link>.
        </p>
      </div>
    );
  }

  const prov = researchProvenance(plan);
  return (
    <div
      data-testid="weekly-plan-banner"
      className="mt-4 rounded-xl border border-teal-200 bg-gradient-to-br from-teal-50 to-white p-4 shadow-sm"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <span className="inline-flex items-center gap-1 rounded-full border border-teal-200 bg-teal-100 px-2 py-0.5 text-[11px] font-semibold text-teal-800">
            📌 This week
          </span>
          <h2 className="mt-1.5 text-base font-semibold text-gray-900">{plan.title || 'This week’s plan'}</h2>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          <RunLinks promptLinks={promptLinks} verb="Refresh" icon={ArrowPathIcon} />
        </div>
      </div>

      {plan.body_markdown && (
        <div
          data-testid="weekly-plan-body"
          className="prose prose-sm mt-2 max-w-none prose-p:my-1 prose-ul:my-1 prose-li:my-0.5 prose-ol:my-1"
        >
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{plan.body_markdown}</ReactMarkdown>
        </div>
      )}

      <div className="mt-2 text-[11px] text-gray-500">
        <span className="font-medium text-gray-600">{prov.sourceLabel}</span>
        {prov.when && <span> · {prov.when}</span>}
      </div>
    </div>
  );
}

/** Open-in-agent links shared by the plan + cold-start states. */
function RunLinks({ promptLinks = {}, verb = 'Run', icon: Icon = PlayIcon }) {
  return (
    <>
      {promptLinks.claude && (
        <a
          href={promptLinks.claude}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 rounded-md bg-[#1A4D2E] px-2.5 py-1.5 text-xs font-medium text-white hover:bg-[#2D6B45]"
        >
          <Icon className="h-3.5 w-3.5" /> {verb} in Claude
        </a>
      )}
      {promptLinks.chatgpt && (
        <a
          href={promptLinks.chatgpt}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 rounded-md border border-gray-300 bg-white px-2.5 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
        >
          <Icon className="h-3.5 w-3.5" /> ChatGPT
        </a>
      )}
    </>
  );
}
