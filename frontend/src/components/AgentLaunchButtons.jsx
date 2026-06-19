import React, { useState } from 'react';
import { PlayIcon, CommandLineIcon, CheckIcon } from '@heroicons/react/24/outline';
import { askLinks, geminiCliCommand } from '../utils/mcpClients';

// The agent launch order — the SINGLE source of truth for which providers we
// hand a prompt off to. Claude / ChatGPT / Grok open a web chat (their web apps
// run the Stratia connector). Gemini is the exception: its web app can't use MCP
// connectors — only the CLI can — so its button copies a runnable CLI command
// instead of opening a (useless) web link.
const PROVIDERS = [
  { key: 'claude', name: 'Claude' },
  { key: 'chatgpt', name: 'ChatGPT' },
  { key: 'gemini', name: 'Gemini' },
  { key: 'grok', name: 'Grok' },
];

// Recover the raw prompt: prefer the explicit prop, else decode it from the
// gemini deep link's `q` param (so callers passing only a `links` object still
// yield a runnable Gemini command without re-plumbing).
function recoverPrompt(prompt, links) {
  if (prompt) return prompt;
  try {
    return new URL(links?.gemini || '').searchParams.get('q') || '';
  } catch {
    return '';
  }
}

/**
 * The standard "open this prompt in your AI agent" button row: Claude, ChatGPT,
 * Gemini, Grok. The first present web provider is primary (green) and may carry
 * a verb ("Run in Claude"); the rest are compact outlines. Gemini renders a
 * "Gemini CLI" copy button (a web page can't open a terminal) that copies a
 * runnable `gemini -p '<prompt>' --approval-mode=yolo`. Renders only providers
 * that have a link; the parent supplies the flex container.
 *
 * @param {{ prompt?: string, links?: object, verb?: string|null,
 *   Icon?: React.ComponentType<{className?: string}>, size?: 'xs'|'sm' }} props
 */
export default function AgentLaunchButtons({ prompt, links, verb = 'Run', Icon = PlayIcon, size = 'sm' }) {
  const l = links || (prompt ? askLinks(prompt) : {});
  const present = PROVIDERS.filter((p) => l[p.key]);
  const pad = size === 'xs' ? 'px-2 py-1 text-[11px]' : 'px-2.5 py-1.5 text-xs';
  const ic = size === 'xs' ? 'h-3 w-3' : 'h-3.5 w-3.5';
  return (
    <>
      {present.map((p, i) => {
        if (p.key === 'gemini') {
          return (
            <GeminiCliButton key="gemini" command={geminiCliCommand(recoverPrompt(prompt, l))} pad={pad} ic={ic} />
          );
        }
        return (
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
        );
      })}
    </>
  );
}

/** Gemini's affordance: copy a runnable CLI command (paste in a terminal to run). */
function GeminiCliButton({ command, pad, ic }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(command);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard blocked — no-op */
    }
  };
  return (
    <button
      type="button"
      onClick={copy}
      data-testid="gemini-cli-copy"
      title={`Copy & run in your terminal: ${command}`}
      className={`inline-flex items-center gap-1 rounded-md border border-gray-300 bg-white font-medium text-gray-700 hover:bg-gray-50 ${pad}`}
    >
      {copied ? <CheckIcon className={`${ic} text-green-600`} /> : <CommandLineIcon className={ic} />}
      {copied ? 'Copied' : 'Gemini CLI'}
    </button>
  );
}
