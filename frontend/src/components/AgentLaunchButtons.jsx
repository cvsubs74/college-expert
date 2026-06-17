import React from 'react';
import { PlayIcon } from '@heroicons/react/24/outline';
import { askLinks } from '../utils/mcpClients';

// The agent launch order — the SINGLE source of truth for which providers we
// hand a prompt off to. Add one here and it appears on every "open in your
// agent" affordance app-wide.
const PROVIDERS = [
  { key: 'claude', name: 'Claude' },
  { key: 'chatgpt', name: 'ChatGPT' },
  { key: 'gemini', name: 'Gemini' },
  { key: 'grok', name: 'Grok' },
];

/**
 * The standard "open this prompt in your AI agent" button row: Claude, ChatGPT,
 * Gemini, Grok. The first present provider is primary (green) and may carry a
 * verb ("Run in Claude"); the rest are compact outlines showing the bare
 * product name. Renders only providers that have a link, so a partial `links`
 * object yields just those buttons (and an empty/missing one renders nothing).
 * The parent supplies the flex container (so it can wrap as it likes).
 *
 * @param {{ prompt?: string, links?: object, verb?: string|null,
 *   Icon?: React.ComponentType<{className?: string}>, size?: 'xs'|'sm' }} props
 *   Pass `prompt` (links built via askLinks) OR a prebuilt `links` object.
 *   `verb` labels the first button ("Run in Claude"); null → bare "Claude".
 */
export default function AgentLaunchButtons({ prompt, links, verb = 'Run', Icon = PlayIcon, size = 'sm' }) {
  const l = links || (prompt ? askLinks(prompt) : {});
  const present = PROVIDERS.filter((p) => l[p.key]);
  const pad = size === 'xs' ? 'px-2 py-1 text-[11px]' : 'px-2.5 py-1.5 text-xs';
  const ic = size === 'xs' ? 'h-3 w-3' : 'h-3.5 w-3.5';
  return (
    <>
      {present.map((p, i) => (
        <a
          key={p.key}
          href={l[p.key]}
          target="_blank"
          rel="noreferrer"
          className={`inline-flex items-center gap-1 rounded-md font-medium ${pad} ${
            i === 0
              ? 'bg-[#1A4D2E] text-white hover:bg-[#2D6B45]'
              : 'border border-gray-300 bg-white text-gray-700 hover:bg-gray-50'
          }`}
        >
          <Icon className={ic} /> {i === 0 && verb ? `${verb} in ${p.name}` : p.name}
        </a>
      ))}
    </>
  );
}
