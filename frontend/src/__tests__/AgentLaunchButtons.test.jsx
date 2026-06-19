import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import AgentLaunchButtons from '../components/AgentLaunchButtons';

describe('AgentLaunchButtons', () => {
  it('renders all four providers from a prompt, verb on the first only', () => {
    render(<AgentLaunchButtons prompt="do the thing" verb="Run" />);
    const claude = screen.getByRole('link', { name: /run in claude/i });
    expect(claude.getAttribute('href')).toContain('claude.ai');
    expect(claude.getAttribute('href')).toContain(encodeURIComponent('do the thing'));
    expect(screen.getByRole('link', { name: /^chatgpt$/i }).getAttribute('href')).toContain('chatgpt.com');
    expect(screen.getByRole('link', { name: /^grok$/i }).getAttribute('href')).toContain('grok.com');
    // Gemini renders a copy-the-CLI-command button (its web app can't use MCP), not a web link.
    expect(screen.queryByRole('link', { name: /^gemini$/i })).not.toBeInTheDocument();
    expect(screen.getByTestId('gemini-cli-copy').getAttribute('title')).toMatch(/gemini -p .*--approval-mode=yolo/);
  });

  it('verb=null renders bare product names (no "Run in")', () => {
    render(<AgentLaunchButtons prompt="x" verb={null} />);
    expect(screen.getByRole('link', { name: /^claude$/i })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /run in claude/i })).not.toBeInTheDocument();
  });

  it('renders only the providers present in a partial links object', () => {
    render(<AgentLaunchButtons links={{ claude: 'https://claude.ai/new?q=x', chatgpt: 'https://chatgpt.com/?q=x' }} verb={null} />);
    expect(screen.getByRole('link', { name: /^claude$/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /^chatgpt$/i })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /^gemini$/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /^grok$/i })).not.toBeInTheDocument();
  });

  it('recovers the prompt from a links object (the path real callers use) for the Gemini command', () => {
    // Callers pass `links` (askLinks output), not the raw prompt — Gemini must
    // still produce a runnable command by decoding the link's q param.
    render(<AgentLaunchButtons links={{
      claude: 'https://claude.ai/new?q=x',
      gemini: `https://gemini.google.com/app?q=${encodeURIComponent("What's due next?")}`,
    }} />);
    const title = screen.getByTestId('gemini-cli-copy').getAttribute('title');
    expect(title).toContain("gemini -p 'What'\\''s due next?' --approval-mode=yolo");
  });

  it('renders nothing with no usable links', () => {
    const { container } = render(<AgentLaunchButtons links={{}} />);
    expect(container).toBeEmptyDOMElement();
  });
});
