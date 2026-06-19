import { describe, it, expect } from 'vitest';
import { MCP_URL, MCP_CLIENTS, geminiCliCommand } from '../utils/mcpClients';

const byId = (id) => MCP_CLIENTS.find((c) => c.id === id);

describe('mcpClients connection config (verified against official docs)', () => {
  it('every client with a command/config/deepLink carries the canonical MCP URL', () => {
    for (const c of MCP_CLIENTS) {
      const blob = [c.command, c.config, c.deepLink].filter(Boolean).join('\n');
      if (blob) {
        expect(blob.includes(MCP_URL) || blob.includes(encodeURIComponent(MCP_URL))).toBe(true);
      }
    }
  });

  it('Claude Code adds the server over HTTP at user scope', () => {
    expect(byId('claude_code').command).toBe(`claude mcp add --transport http --scope user stratia ${MCP_URL}`);
  });

  it('Gemini CLI adds at user scope AND the steps include the required /mcp auth sign-in', () => {
    const g = byId('gemini_cli');
    expect(g.command).toContain('--transport http');
    expect(g.command).toContain('-s user');
    expect(g.steps.some((s) => s.includes('/mcp auth stratia'))).toBe(true);
  });

  it('per-client config JSON keys are the load-bearing ones (they are NOT interchangeable)', () => {
    expect(byId('cursor').config).toContain('"url"');
    expect(byId('cursor').config).not.toContain('serverUrl');
    expect(byId('windsurf').config).toContain('"serverUrl"');
    expect(byId('vscode').config).toContain('"servers"');
    expect(byId('vscode').config).toContain('"type": "http"');
    expect(byId('cline').config).toContain('"type": "streamableHttp"');
    expect(byId('goose').config).toContain('"type": "streamable_http"');
  });

  it('Windsurf no longer references the non-existent "Manage MCPs" menu', () => {
    expect(byId('windsurf').steps.join(' ')).not.toMatch(/Manage MCPs/);
  });

  it('Cline includes the required Authenticate click and names a min version', () => {
    expect(byId('cline').steps.join(' ')).toMatch(/Authenticate/);
    expect(byId('cline').requires).toMatch(/3\.x/);
  });
});

describe('geminiCliCommand', () => {
  it('builds a hands-free non-interactive Gemini CLI command', () => {
    expect(geminiCliCommand('compare two colleges'))
      .toBe("gemini -p 'compare two colleges' --approval-mode=yolo");
  });

  it('POSIX-escapes embedded single quotes so the prompt is shell-safe', () => {
    expect(geminiCliCommand("What's due?"))
      .toBe("gemini -p 'What'\\''s due?' --approval-mode=yolo");
  });
});
