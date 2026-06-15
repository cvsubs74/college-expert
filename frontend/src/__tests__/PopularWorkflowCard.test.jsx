import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import PopularWorkflowCard from '../components/research/PopularWorkflowCard';
import { isoWeekKey } from '../utils/research';

const WF = {
  signature: 'get_profile>get_fit_analysis>save_research',
  tools: ['get_profile', 'get_fit_analysis', 'save_research'],
  kind: 'comparison', count: 12,
};

// A workflow whose current-week count clearly jumps over last week (so the
// "now"-relative trend math fires regardless of when the test runs).
function trendingWf() {
  const now = new Date();
  const thisW = isoWeekKey(now);
  const lastW = isoWeekKey(new Date(now.getTime() - 7 * 86400000));
  return { ...WF, count: 30, weeks: { [thisW]: 9, [lastW]: 2 } };
}

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

  it('shows a Trending badge on a week-over-week jump, not otherwise', () => {
    const { rerender } = render(<PopularWorkflowCard wf={trendingWf()} />);
    expect(screen.getByTestId('trending-badge')).toBeInTheDocument();
    rerender(<PopularWorkflowCard wf={WF} />); // no weeks → not trending
    expect(screen.queryByTestId('trending-badge')).not.toBeInTheDocument();
  });

  it('flags "New to you" only when the user has not run this workflow', () => {
    const { rerender } = render(<PopularWorkflowCard wf={WF} ownSignatures={new Set(['other'])} />);
    expect(screen.getByTestId('new-to-you-chip')).toBeInTheDocument();
    rerender(<PopularWorkflowCard wf={WF} ownSignatures={new Set([WF.signature])} />);
    expect(screen.queryByTestId('new-to-you-chip')).not.toBeInTheDocument();
  });
});
