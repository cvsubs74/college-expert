import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import ConnectAgents from '../pages/ConnectAgents';
import { MCP_CLIENTS, MCP_URL } from '../utils/mcpClients';

describe('ConnectAgents (Connect your AI agent hub)', () => {
  it('shows the MCP URL and the primary clients (Claude.ai, ChatGPT, Claude Code)', () => {
    render(<ConnectAgents />);
    expect(screen.getByTestId('mcp-url')).toHaveTextContent(MCP_URL);
    expect(screen.getByText('Claude.ai')).toBeInTheDocument();
    expect(screen.getByText('ChatGPT')).toBeInTheDocument();
    expect(screen.getByText('Claude Code')).toBeInTheDocument();
    // collapsed by default: only the 3 primary clients
    expect(screen.getAllByTestId('client-row')).toHaveLength(3);
  });

  it('reveals all clients via "See all N clients"', () => {
    render(<ConnectAgents />);
    fireEvent.click(screen.getByRole('button', { name: /see all \d+ clients/i }));
    expect(screen.getAllByTestId('client-row')).toHaveLength(MCP_CLIENTS.length);
    expect(screen.getByText('Cursor')).toBeInTheDocument();
    expect(screen.getByText('VS Code')).toBeInTheDocument();
  });

  it('expands a client to reveal its steps', () => {
    render(<ConnectAgents />);
    // expand ChatGPT specifically
    const row = screen.getAllByTestId('client-row').find((r) => r.dataset.client === 'chatgpt');
    fireEvent.click(within(row).getByRole('button'));
    expect(within(row).getAllByText(/Developer mode/i).length).toBeGreaterThan(0);
  });

  it('renders the ask-something-real prompts with Ask-in-agent links', () => {
    render(<ConnectAgents />);
    const rows = screen.getAllByTestId('ask-row');
    expect(rows.length).toBeGreaterThanOrEqual(6);
    const first = rows[0];
    expect(within(first).getByRole('link', { name: /ask in claude/i })).toHaveAttribute('href', expect.stringContaining('claude.ai'));
    expect(within(first).getByRole('link', { name: /ask in chatgpt/i })).toHaveAttribute('href', expect.stringContaining('chatgpt.com'));
  });
});
