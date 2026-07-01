import React, { useState } from 'react';
import {
  ClipboardDocumentIcon,
  CheckIcon,
  PlusIcon,
  MinusIcon,
  ArrowTopRightOnSquareIcon,
} from '@heroicons/react/24/outline';
import { MCP_URL, MCP_CLIENTS, ASK_PROMPTS, askLinks } from '../utils/mcpClients';

/** Small copy-to-clipboard button with transient "Copied" feedback. */
function CopyButton({ text, label = 'Copy', className = '' }) {
  const [copied, setCopied] = useState(false);
  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard blocked — no-op */
    }
  };
  return (
    <button
      type="button"
      onClick={onCopy}
      className={`inline-flex items-center gap-1.5 rounded-md border border-gray-300 bg-white px-2.5 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 ${className}`}
    >
      {copied ? <CheckIcon className="h-3.5 w-3.5 text-green-600" /> : <ClipboardDocumentIcon className="h-3.5 w-3.5" />}
      {copied ? 'Copied' : label}
    </button>
  );
}

function ClientRow({ client }) {
  const [open, setOpen] = useState(false);
  return (
    <div data-testid="client-row" data-client={client.id} className="border-b border-gray-100 last:border-b-0">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-gray-50"
      >
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gray-100 text-lg" aria-hidden="true">
          {client.emoji}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block font-medium text-gray-900">{client.name}</span>
          {client.sub && <span className="block text-xs text-gray-500">{client.sub}</span>}
        </span>
        {open ? <MinusIcon className="h-5 w-5 text-gray-400" /> : <PlusIcon className="h-5 w-5 text-gray-400" />}
      </button>

      {open && (
        <div className="space-y-3 px-4 pb-4 pl-16">
          {client.requires && (
            <p className="text-xs text-gray-500">
              <span className="font-medium text-gray-600">Requires:</span> {client.requires}
            </p>
          )}
          <ol className="list-decimal space-y-1.5 pl-4 text-sm text-gray-700 marker:text-gray-400">
            {client.steps.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ol>

          {client.command && (
            <div className="flex items-start gap-2">
              <pre className="flex-1 overflow-x-auto rounded-lg bg-gray-900 px-3 py-2 text-xs text-gray-100">{client.command}</pre>
              <CopyButton text={client.command} />
            </div>
          )}
          {client.config && (
            <div className="flex items-start gap-2">
              <pre className="flex-1 overflow-x-auto rounded-lg bg-gray-900 px-3 py-2 text-xs text-gray-100">{client.config}</pre>
              <CopyButton text={client.config} />
            </div>
          )}
          {client.deepLink && (
            <a
              href={client.deepLink}
              className="inline-flex items-center gap-1.5 rounded-md bg-[#1A4D2E] px-3 py-1.5 text-xs font-medium text-white hover:bg-[#2D6B45]"
            >
              <ArrowTopRightOnSquareIcon className="h-3.5 w-3.5" />
              One-click add
            </a>
          )}
        </div>
      )}
    </div>
  );
}

function AskRow({ item }) {
  const links = askLinks(item.prompt);
  return (
    <div data-testid="ask-row" className="flex items-center justify-between gap-3 border-b border-gray-100 px-4 py-3 last:border-b-0">
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-gray-800" title={item.title}>{item.title}</p>
        <p className="truncate text-xs text-gray-500" title={item.prompt}>{item.prompt}</p>
      </div>
      <div className="flex shrink-0 flex-wrap items-center justify-end gap-1.5">
        <a href={links.claude} target="_blank" rel="noreferrer"
          className="rounded-md border border-gray-300 bg-white px-2.5 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50">
          Ask in Claude
        </a>
        <a href={links.chatgpt} target="_blank" rel="noreferrer"
          className="rounded-md border border-gray-300 bg-white px-2.5 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50">
          Ask in ChatGPT
        </a>
        <CopyButton text={item.prompt} label="Copy prompt" />
      </div>
    </div>
  );
}

/**
 * "Connect your AI agent" hub — add the Stratia MCP connector to any AI client
 * (Claude.ai, ChatGPT, Claude Code, and more), then ask real questions that run
 * the Stratia tools. Modeled on Era's Context connect flow.
 */
export default function ConnectAgents() {
  const [showAll, setShowAll] = useState(false);
  const primary = MCP_CLIENTS.filter((c) => c.primary);
  const rest = MCP_CLIENTS.filter((c) => !c.primary);
  const visible = showAll ? MCP_CLIENTS : primary;

  return (
    <div className="mx-auto max-w-3xl px-4 py-6 sm:px-6">
      <h1 className="text-2xl font-bold text-gray-900">Connect your AI agent</h1>
      <p className="mt-1 max-w-2xl text-sm text-gray-600">
        Give any AI assistant secure access to your Stratia data — your profile, college list, fit
        analyses, deadlines, scholarships and roadmap — then ask it anything. It can also save
        research straight to your notebook. Takes about 30 seconds.
      </p>

      {/* The one URL every client needs */}
      <div className="mt-5 rounded-xl border border-gray-200 bg-white p-4">
        <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Your MCP server URL</p>
        <div className="mt-2 flex items-center gap-2">
          <code data-testid="mcp-url" className="flex-1 overflow-x-auto rounded-lg bg-gray-50 px-3 py-2 text-sm text-gray-800">{MCP_URL}</code>
          <CopyButton text={MCP_URL} label="Copy URL" />
        </div>
        <p className="mt-2 text-xs text-gray-500">
          Sign-in is Google OAuth — no API keys to manage. Paste this URL into your client below.
        </p>
      </div>

      {/* Clients */}
      <section className="mt-6">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">Add Stratia to your client</h2>
        <div className="mt-2 overflow-hidden rounded-xl border border-gray-200 bg-white">
          {visible.map((c) => (
            <ClientRow key={c.id} client={c} />
          ))}
        </div>
        {rest.length > 0 && (
          <button
            type="button"
            onClick={() => setShowAll((v) => !v)}
            className="mt-2 text-sm font-medium text-indigo-600 hover:text-indigo-800"
          >
            {showAll ? 'Show fewer clients' : `See all ${MCP_CLIENTS.length} clients →`}
          </button>
        )}
      </section>

      {/* Ask something real */}
      <section className="mt-8">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">Ask something real</h2>
        <p className="mt-1 text-sm text-gray-600">
          These aren’t questions a dashboard can answer. Copy one, or open it straight in Claude or ChatGPT.
        </p>
        <div className="mt-2 overflow-hidden rounded-xl border border-gray-200 bg-white">
          {ASK_PROMPTS.map((p, i) => (
            <AskRow key={i} item={p} />
          ))}
        </div>
      </section>
    </div>
  );
}
