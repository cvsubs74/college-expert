import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import PopularWorkflowCard from '../components/research/PopularWorkflowCard';

const WF = {
  signature: 'get_profile>get_fit_analysis>save_research',
  tools: ['get_profile', 'get_fit_analysis', 'save_research'],
  kind: 'comparison', count: 12,
};

describe('PopularWorkflowCard', () => {
  it('shows the name, run count, friendly steps and run links', () => {
    render(<PopularWorkflowCard wf={WF} />);
    expect(screen.getByText(/Comparison: Get profile/)).toBeInTheDocument();
    expect(screen.getByText(/Run 12 times/)).toBeInTheDocument();
    expect(screen.getAllByText('Get profile').length).toBeGreaterThanOrEqual(1); // step pill
    expect(screen.getByRole('link', { name: /run in claude/i }).getAttribute('href')).toContain('claude.ai');
    expect(screen.getByRole('link', { name: /chatgpt/i }).getAttribute('href')).toContain('chatgpt.com');
  });

  it('handles singular grammar and signature-only records', () => {
    render(<PopularWorkflowCard wf={{ signature: 'a>b', kind: 'note', count: 1 }} />);
    expect(screen.getByText(/Run 1 time ·/)).toBeInTheDocument();
  });
});
