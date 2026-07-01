import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import AgentChatHandoff from '../components/AgentChatHandoff';

describe('AgentChatHandoff', () => {
  it('renders Claude + ChatGPT hand-off links seeded with the prompt', () => {
    render(<AgentChatHandoff prompt="Tell me about Princeton" />);
    const claude = screen.getByRole('link', { name: /ask in claude/i });
    expect(claude.getAttribute('href')).toContain('claude.ai');
    expect(claude.getAttribute('href')).toContain(encodeURIComponent('Tell me about Princeton'));
    expect(screen.getByRole('link', { name: /^chatgpt$/i }).getAttribute('href')).toContain('chatgpt.com');
    expect(screen.getByText(/prefer your own ai/i)).toBeInTheDocument();
  });

  it('renders a custom label', () => {
    render(<AgentChatHandoff prompt="x" label="Model overloaded?" />);
    expect(screen.getByText('Model overloaded?')).toBeInTheDocument();
  });

  it('renders nothing without a prompt', () => {
    const { container } = render(<AgentChatHandoff prompt="" />);
    expect(container).toBeEmptyDOMElement();
  });
});
