import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import ConnectAgents from '../pages/ConnectAgents';
import { MCP_CLIENTS, MCP_URL } from '../utils/mcpClients';

describe('ConnectAgents (Connect your AI agent hub)', () => {
  it('shows the MCP URL and only the Claude.ai + ChatGPT clients', () => {
    render(<ConnectAgents />);
    expect(screen.getByTestId('mcp-url')).toHaveTextContent(MCP_URL);
    expect(screen.getByText('Claude.ai')).toBeInTheDocument();
    expect(screen.getByText('ChatGPT')).toBeInTheDocument();
    // Only Claude and ChatGPT are offered — no dev-tool clients.
    expect(screen.queryByText('Claude Code')).not.toBeInTheDocument();
    expect(screen.getAllByTestId('client-row')).toHaveLength(2);
  });

  it('has no "See all clients" toggle (every client is primary)', () => {
    render(<ConnectAgents />);
    expect(MCP_CLIENTS).toHaveLength(2);
    expect(screen.queryByRole('button', { name: /see all \d+ clients/i })).not.toBeInTheDocument();
    expect(screen.queryByText('Cursor')).not.toBeInTheDocument();
    expect(screen.queryByText('VS Code')).not.toBeInTheDocument();
  });

  it('expands a client to reveal its steps', () => {
    render(<ConnectAgents />);
    // expand ChatGPT specifically
    const row = screen.getAllByTestId('client-row').find((r) => r.dataset.client === 'chatgpt');
    fireEvent.click(within(row).getByRole('button'));
    expect(within(row).getAllByText(/Developer mode/i).length).toBeGreaterThan(0);
  });

  it('renders the ask-something-real prompts with Claude + ChatGPT links only', () => {
    render(<ConnectAgents />);
    const rows = screen.getAllByTestId('ask-row');
    expect(rows.length).toBeGreaterThanOrEqual(6);
    const first = rows[0];
    expect(within(first).getByRole('link', { name: /ask in claude/i })).toHaveAttribute('href', expect.stringContaining('claude.ai'));
    expect(within(first).getByRole('link', { name: /ask in chatgpt/i })).toHaveAttribute('href', expect.stringContaining('chatgpt.com'));
    // Gemini and Grok are no longer offered.
    expect(within(first).queryByRole('link', { name: /grok/i })).not.toBeInTheDocument();
    expect(within(first).queryByRole('button', { name: /gemini/i })).not.toBeInTheDocument();
    expect(within(first).getByRole('button', { name: /copy prompt/i })).toBeInTheDocument();
  });
});
