import React from 'react';
import { ClipboardDocumentListIcon } from '@heroicons/react/24/outline';
import { researchToTasksPrompt } from '../../utils/research';
import { askLinks } from '../../utils/mcpClients';
import AgentLaunchButtons from '../AgentLaunchButtons';

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
      <AgentLaunchButtons links={links} verb={null} size="xs" />
    </div>
  );
}
