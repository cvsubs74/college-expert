import React from 'react';
import AgentLaunchButtons from './AgentLaunchButtons';

/**
 * A persistent "prefer your own AI?" row for any in-app chat. Hands the chat's
 * current context off to Claude or ChatGPT (via the Stratia MCP connector) so a
 * student can continue on their preferred surface — and a resilient path when
 * the in-app model is overloaded. `prompt` is the seeded question + context
 * (built by the helpers in utils/agentHandoff.js).
 */
export default function AgentChatHandoff({ prompt, label = 'Prefer your own AI?', className = '' }) {
  if (!prompt) return null;
  return (
    <div className={`flex flex-wrap items-center gap-1.5 ${className}`} data-testid="agent-chat-handoff">
      <span className="text-[11px] text-gray-500">{label}</span>
      <AgentLaunchButtons prompt={prompt} verb="Ask" size="xs" />
    </div>
  );
}
