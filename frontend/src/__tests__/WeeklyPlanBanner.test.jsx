import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import WeeklyPlanBanner from '../components/research/WeeklyPlanBanner';

const links = { claude: 'https://claude.ai/new?q=x', chatgpt: 'https://chatgpt.com/?q=x' };
const renderB = (ui) => render(<MemoryRouter>{ui}</MemoryRouter>);

describe('WeeklyPlanBanner', () => {
  it('cold start: nudges to generate a plan, with run links + a connect link', () => {
    renderB(<WeeklyPlanBanner plan={null} promptLinks={links} />);
    expect(screen.getByTestId('weekly-plan-empty')).toBeInTheDocument();
    expect(screen.queryByTestId('weekly-plan-banner')).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: /get my plan in claude/i }).getAttribute('href')).toBe(links.claude);
    expect(screen.getByRole('link', { name: /connect claude or chatgpt/i }).getAttribute('href')).toBe('/connect');
  });

  it('renders the plan title, ≤3 bullets, and a refresh hand-off', () => {
    const plan = {
      kind: 'weekly_plan',
      title: 'This week',
      body_markdown: '- Submit UCLA supplement (Fri)\n- Email Dr. Lee for your rec\n- Finalize activities list',
      created_at: '2026-06-14T00:00:00Z',
      source: 'claude_mcp',
      provenance: { source: 'claude_mcp' },
    };
    renderB(<WeeklyPlanBanner plan={plan} promptLinks={links} />);
    expect(screen.getByTestId('weekly-plan-banner')).toBeInTheDocument();
    expect(screen.getByText('This week')).toBeInTheDocument();
    expect(screen.getByTestId('weekly-plan-body')).toHaveTextContent('Submit UCLA supplement');
    expect(screen.getByRole('link', { name: /refresh in claude/i }).getAttribute('href')).toBe(links.claude);
    expect(screen.getByText(/From Claude/i)).toBeInTheDocument(); // provenance footer
  });
});
