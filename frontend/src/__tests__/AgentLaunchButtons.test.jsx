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
    expect(screen.getByRole('link', { name: /^gemini$/i }).getAttribute('href')).toContain('gemini.google.com');
    expect(screen.getByRole('link', { name: /^grok$/i }).getAttribute('href')).toContain('grok.com');
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

  it('renders nothing with no usable links', () => {
    const { container } = render(<AgentLaunchButtons links={{}} />);
    expect(container).toBeEmptyDOMElement();
  });
});
