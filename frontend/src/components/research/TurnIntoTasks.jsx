import React from 'react';
import { ClipboardDocumentListIcon, PlayIcon } from '@heroicons/react/24/outline';
import { researchToTasksPrompt } from '../../utils/research';
import { askLinks } from '../../utils/mcpClients';

/**
 * "Turn into tasks" hand-off — re-runs the note in the student's connected agent
 * so the AGENT derives roadmap tasks (via research_to_tasks). The app never
 * extracts tasks itself. Purely presentational: builds the deep links from the
 * note's title.
 *
 * @param {{ note: object, className?: string }} props
 */
export default function TurnIntoTasks({ note, className = '' }) {
  if (!note) return null;
  const links = askLinks(researchToTasksPrompt(note));
  return (
    <div data-testid="turn-into-tasks" className={`flex flex-wrap items-center gap-1.5 ${className}`}>
      <span className="inline-flex items-center gap-1 text-[11px] font-medium uppercase tracking-wide text-gray-400">
        <ClipboardDocumentListIcon className="h-3.5 w-3.5" /> Turn into tasks
      </span>
      <a
        href={links.claude}
        target="_blank"
        rel="noreferrer"
        className="inline-flex items-center gap-1 rounded-md bg-[#1A4D2E] px-2 py-1 text-[11px] font-medium text-white hover:bg-[#2D6B45]"
      >
        <PlayIcon className="h-3 w-3" /> Claude
      </a>
      <a
        href={links.chatgpt}
        target="_blank"
        rel="noreferrer"
        className="inline-flex items-center gap-1 rounded-md border border-gray-300 bg-white px-2 py-1 text-[11px] font-medium text-gray-700 hover:bg-gray-50"
      >
        <PlayIcon className="h-3 w-3" /> ChatGPT
      </a>
    </div>
  );
}
