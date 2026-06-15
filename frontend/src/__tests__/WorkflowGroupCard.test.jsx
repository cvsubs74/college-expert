import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import WorkflowGroupCard from '../components/research/WorkflowGroupCard';

const GROUP = {
  signature: 'get_profile>get_fit_analysis',
  name: 'compare two colleges',
  steps: [
    { tool: 'get_profile', label: 'Pulled my profile' },
    { tool: 'get_fit_analysis', label: 'Got fit for both' },
  ],
  representative: { research_id: 'a2', title: 'UCLA vs Cal', source_prompt: 'compare two colleges' },
  researches: [
    { research_id: 'a2', title: 'UCLA vs Cal', kind: 'comparison', created_at: '2026-06-10', summary: 'cal wins', body_markdown: '## Cal\nStronger CS.' },
    { research_id: 'a1', title: 'Duke vs UCSD', kind: 'comparison', created_at: '2026-06-01', body_markdown: '## Duke\nReach.' },
  ],
};

describe('WorkflowGroupCard', () => {
  it('shows the workflow name and what it produced (count + outputs)', () => {
    render(<WorkflowGroupCard group={GROUP} />);
    expect(screen.getByText('compare two colleges')).toBeInTheDocument();
    expect(screen.getByText(/Produced 2 researches/)).toBeInTheDocument();
    expect(screen.getAllByTestId('workflow-output')).toHaveLength(2);
    expect(screen.getByText('UCLA vs Cal')).toBeInTheDocument();
    expect(screen.getByText('Duke vs UCSD')).toBeInTheDocument();
  });

  it('reveals how it works (steps) on demand', () => {
    render(<WorkflowGroupCard group={GROUP} />);
    fireEvent.click(screen.getByRole('button', { name: /how it works/i }));
    expect(screen.getByText(/Pulled my profile/)).toBeInTheDocument();
    expect(screen.getByText(/Got fit for both/)).toBeInTheDocument();
  });

  it('expands a produced research to show its body', () => {
    render(<WorkflowGroupCard group={GROUP} />);
    const row = screen.getAllByTestId('workflow-output')[0];
    fireEvent.click(within(row).getByRole('button'));
    expect(within(row).getByText(/Stronger CS/)).toBeInTheDocument();
  });

  it('offers run-again links built from the workflow', () => {
    render(<WorkflowGroupCard group={GROUP} />);
    expect(screen.getByRole('link', { name: /run in claude/i }).getAttribute('href')).toContain('claude.ai');
    expect(screen.getByRole('link', { name: /chatgpt/i }).getAttribute('href')).toContain('chatgpt.com');
  });
});
