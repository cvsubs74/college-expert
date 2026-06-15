import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { TrashIcon, ChevronDownIcon, ChevronUpIcon, PencilSquareIcon, PlayIcon, ClipboardDocumentIcon, CheckIcon } from '@heroicons/react/24/outline';
import { kindMeta, researchProvenance, workflowSteps, hasWorkflow, repeatPrompt } from '../../utils/research';
import { askLinks } from '../../utils/mcpClients';

/** `duke_university` → "Duke University" (fallback when no display name known). */
function prettyId(id) {
  return String(id || '')
    .split('_')
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

/**
 * One Research Notebook entry: kind badge, title + summary, linked-college
 * chips, an expandable Markdown body, and a provenance/staleness footer.
 *
 * @param {{ note: object, collegeNames?: Record<string,string>,
 *   onDelete?: (researchId: string) => void, onEdit?: (note: object) => void }} props
 */
// "Repeat this workflow" — shows how the research was produced (the original ask
// + ordered steps the agent ran) and lets the student re-run it in their agent.
function WorkflowWidget({ note }) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  if (!hasWorkflow(note)) return null;
  const steps = workflowSteps(note);
  const prompt = repeatPrompt(note);
  const links = askLinks(prompt);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(prompt);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard blocked — no-op */
    }
  };
  return (
    <div data-testid="research-workflow" className="mt-3 rounded-lg border border-gray-100 bg-gray-50/60 p-3">
      <div className="flex items-center justify-between gap-2">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          className="inline-flex items-center gap-1 text-xs font-semibold uppercase tracking-wide text-gray-500 hover:text-gray-700"
        >
          {open ? <ChevronUpIcon className="h-3.5 w-3.5" /> : <ChevronDownIcon className="h-3.5 w-3.5" />}
          Workflow{steps.length ? ` · ${steps.length} step${steps.length > 1 ? 's' : ''}` : ''}
        </button>
        <div className="flex shrink-0 items-center gap-1.5">
          <a href={links.claude} target="_blank" rel="noreferrer"
            className="inline-flex items-center gap-1 rounded-md bg-[#1A4D2E] px-2 py-1 text-[11px] font-medium text-white hover:bg-[#2D6B45]">
            <PlayIcon className="h-3 w-3" /> Run in Claude
          </a>
          <a href={links.chatgpt} target="_blank" rel="noreferrer"
            className="inline-flex items-center gap-1 rounded-md border border-gray-300 bg-white px-2 py-1 text-[11px] font-medium text-gray-700 hover:bg-gray-50">
            <PlayIcon className="h-3 w-3" /> ChatGPT
          </a>
          <button type="button" onClick={copy} aria-label="Copy workflow prompt"
            className="rounded-md border border-gray-300 bg-white p-1 text-gray-500 hover:bg-gray-50">
            {copied ? <CheckIcon className="h-3.5 w-3.5 text-green-600" /> : <ClipboardDocumentIcon className="h-3.5 w-3.5" />}
          </button>
        </div>
      </div>
      {open && (
        <div className="mt-2 space-y-2">
          {note.source_prompt && (
            <p className="text-xs text-gray-600">
              <span className="font-medium text-gray-700">Asked:</span> “{note.source_prompt}”
            </p>
          )}
          {steps.length > 0 && (
            <ol className="list-decimal space-y-1 pl-5 text-xs text-gray-600 marker:text-gray-400">
              {steps.map((s, i) => (
                <li key={i}>
                  {s.label}
                  {s.tool ? <span className="ml-1 text-gray-400">({s.tool})</span> : null}
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
    </div>
  );
}

export default function ResearchCard({ note, collegeNames = {}, onDelete, onEdit }) {
  const [open, setOpen] = useState(false);
  const meta = kindMeta(note.kind);
  const prov = researchProvenance(note);
  const colleges = note.university_ids || [];
  const tags = note.tags || [];

  return (
    <div
      data-testid="research-card"
      data-kind={note.kind || 'note'}
      className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm transition hover:shadow-md"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <span
            data-testid="research-kind-badge"
            className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium ${meta.tone}`}
          >
            <span aria-hidden="true">{meta.emoji}</span>
            {meta.label}
          </span>
          <h3 className="mt-2 truncate text-base font-semibold text-gray-900" title={note.title}>
            {note.title || 'Untitled research'}
          </h3>
          {note.summary && <p className="mt-1 text-sm text-gray-600">{note.summary}</p>}
        </div>
        <div className="flex shrink-0 items-center gap-1">
          {onEdit && (
            <button
              type="button"
              aria-label="Edit research"
              onClick={() => onEdit(note)}
              className="rounded-md p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700"
            >
              <PencilSquareIcon className="h-4 w-4" />
            </button>
          )}
          {onDelete && (
            <button
              type="button"
              aria-label="Delete research"
              onClick={() => onDelete(note.research_id)}
              className="rounded-md p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-600"
            >
              <TrashIcon className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      {colleges.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {colleges.map((id) => (
            <span
              key={id}
              data-testid="research-college-chip"
              className="rounded-full bg-gray-100 px-2 py-0.5 text-[11px] font-medium text-gray-700"
            >
              {collegeNames[id] || prettyId(id)}
            </span>
          ))}
        </div>
      )}

      {note.body_markdown && (
        <>
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-indigo-600 hover:text-indigo-800"
          >
            {open ? <ChevronUpIcon className="h-4 w-4" /> : <ChevronDownIcon className="h-4 w-4" />}
            {open ? 'Hide details' : 'Show details'}
          </button>
          {open && (
            <div
              data-testid="research-body"
              className="prose prose-sm mt-2 max-w-none rounded-lg bg-gray-50 p-3 prose-p:my-1.5 prose-ul:my-1.5 prose-li:my-0 prose-headings:mt-3 prose-headings:mb-1"
            >
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{note.body_markdown}</ReactMarkdown>
            </div>
          )}
        </>
      )}

      <WorkflowWidget note={note} />

      <div className="mt-3 flex flex-wrap items-center gap-x-2 gap-y-1 border-t border-gray-100 pt-2 text-[11px] text-gray-500">
        <span className="font-medium text-gray-600">{prov.sourceLabel}</span>
        {prov.when && <span>· {prov.when}</span>}
        {prov.cycle && !prov.stale && <span>· Based on {prov.cycle} data</span>}
        {prov.stale && (
          <span
            data-testid="research-stale-chip"
            className="inline-flex items-center gap-1 rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 font-medium text-amber-800"
          >
            <span aria-hidden="true">🗓️</span>
            Based on {prov.cycle} data — newer cycle available
          </span>
        )}
        {tags.length > 0 && <span className="text-gray-400">· {tags.map((t) => `#${t}`).join(' ')}</span>}
      </div>
    </div>
  );
}
