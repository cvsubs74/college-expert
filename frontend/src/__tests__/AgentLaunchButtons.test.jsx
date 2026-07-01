import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import AgentLaunchButtons from '../components/AgentLaunchButtons';

describe('AgentLaunchButtons', () => {
  it('renders Claude and ChatGPT from a prompt, verb on the first only', () => {
    render(<AgentLaunchButtons prompt="do the thing" verb="Run" />);
    const claude = screen.getByRole('link', { name: /run in claude/i });
    expect(claude.getAttribute('href')).toContain('claude.ai');
    expect(claude.getAttribute('href')).toContain(encodeURIComponent('do the thing'));
    expect(screen.getByRole('link', { name: /^chatgpt$/i }).getAttribute('href')).toContain('chatgpt.com');
    // Gemini and Grok are no longer offered.
    expect(screen.queryByRole('link', { name: /gemini/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /grok/i })).not.toBeInTheDocument();
    expect(screen.queryByTestId('gemini-cli-copy')).not.toBeInTheDocument();
  });

  it('verb=null renders bare product names (no "Run in")', () => {
    render(<AgentLaunchButtons prompt="x" verb={null} />);
    expect(screen.getByRole('link', { name: /^claude$/i })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /run in claude/i })).not.toBeInTheDocument();
  });

  it('renders only the providers present in a partial links object', () => {
    render(<AgentLaunchButtons links={{ claude: 'https://claude.ai/new?q=x' }} verb={null} />);
    expect(screen.getByRole('link', { name: /^claude$/i })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /^chatgpt$/i })).not.toBeInTheDocument();
  });

  it('renders nothing with no usable links', () => {
    const { container } = render(<AgentLaunchButtons links={{}} />);
    expect(container).toBeEmptyDOMElement();
  });
});
