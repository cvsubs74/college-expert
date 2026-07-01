import { describe, it, expect } from 'vitest';
import { MCP_URL, MCP_CLIENTS, askLinks } from '../utils/mcpClients';

const byId = (id) => MCP_CLIENTS.find((c) => c.id === id);

describe('mcpClients connection config (verified against official docs)', () => {
  it('offers only Claude.ai and ChatGPT, both primary, each with steps', () => {
    expect(MCP_CLIENTS.map((c) => c.id)).toEqual(['claude_web', 'chatgpt']);
    for (const c of MCP_CLIENTS) {
      expect(c.primary).toBe(true);
      expect(Array.isArray(c.steps) && c.steps.length).toBeTruthy();
    }
  });

  it('every client with a command/config/deepLink carries the canonical MCP URL', () => {
    for (const c of MCP_CLIENTS) {
      const blob = [c.command, c.config, c.deepLink].filter(Boolean).join('\n');
      if (blob) {
        expect(blob.includes(MCP_URL) || blob.includes(encodeURIComponent(MCP_URL))).toBe(true);
      }
    }
  });

  it('ChatGPT needs Developer mode and the OAuth self-registration note', () => {
    const c = byId('chatgpt');
    expect(c.steps.join(' ')).toMatch(/Developer mode/i);
    expect(c.steps.join(' ')).toMatch(/self-registers/i);
  });
});

describe('askLinks', () => {
  it('returns only Claude and ChatGPT deep links, URL-encoding the prompt', () => {
    const links = askLinks("What's due next?");
    expect(Object.keys(links)).toEqual(['claude', 'chatgpt']);
    expect(links.claude).toContain('claude.ai');
    expect(links.chatgpt).toContain('chatgpt.com');
    expect(links.claude).toContain(encodeURIComponent("What's due next?"));
  });
});
