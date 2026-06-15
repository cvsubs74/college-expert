import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import TurnIntoTasks from '../components/research/TurnIntoTasks';

describe('TurnIntoTasks', () => {
  it('renders Claude + ChatGPT hand-off links seeded with the note title', () => {
    render(<TurnIntoTasks note={{ title: 'Scholarship plan' }} />);
    expect(screen.getByTestId('turn-into-tasks')).toBeInTheDocument();
    const claude = screen.getByRole('link', { name: /claude/i });
    expect(claude.getAttribute('href')).toContain('claude.ai');
    expect(claude.getAttribute('href')).toContain(encodeURIComponent('Scholarship plan'));
    expect(claude.getAttribute('href')).toContain(encodeURIComponent('research_to_tasks'));
    expect(screen.getByRole('link', { name: /chatgpt/i }).getAttribute('href')).toContain('chatgpt.com');
  });

  it('renders nothing without a note', () => {
    const { container } = render(<TurnIntoTasks note={null} />);
    expect(container).toBeEmptyDOMElement();
  });
});
