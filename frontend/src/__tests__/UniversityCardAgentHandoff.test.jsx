/**
 * #310: the card surfaces a FREE "Update via ChatGPT/Claude" agent-handoff
 * affordance alongside the 1-credit in-app regenerate — the credit-saving route.
 * The launch prompt tells the agent to recompute + save via MCP for this school;
 * the save-schema is NEVER shown in the UI.
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import UniversityCard from '../components/stratia/UniversityCard';
import { agentUpdateAnalysisPrompt } from '../utils/mcpClients';

const uni = {
  university_name: 'Duke University',
  university_id: 'duke',
  location: 'Durham, NC',
  fit_category: 'REACH',
  match_score: 45,
};

describe('UniversityCard — free agent-update affordance (#310)', () => {
  it('renders the "Update via ChatGPT/Claude — free" hand-off with a school-specific prompt', () => {
    render(<UniversityCard university={uni} onViewAnalysis={() => {}} />);

    expect(screen.getByTestId('agent-update-affordance')).toBeInTheDocument();
    expect(screen.getByText(/update via chatgpt\/claude — free/i)).toBeInTheDocument();

    // The Claude launch link carries the recompute+save prompt for THIS school.
    const claude = screen.getByRole('link', { name: /ask in claude/i });
    expect(claude.getAttribute('href')).toContain('claude.ai');
    expect(claude.getAttribute('href')).toContain(encodeURIComponent('Duke University'));
    expect(screen.getByRole('link', { name: /^chatgpt$/i }).getAttribute('href')).toContain('chatgpt.com');
  });

  it('the launch prompt asks the agent to recompute AND save both artifacts, free', () => {
    const p = agentUpdateAnalysisPrompt('Duke University');
    expect(p).toMatch(/Duke University/);
    expect(p.toLowerCase()).toMatch(/fit/);
    expect(p.toLowerCase()).toMatch(/major chances/);
    expect(p).toMatch(/save_fit_analysis/);
    expect(p).toMatch(/save_major_chances/);
    expect(p).toMatch(/get_analysis_schema/);
    // Never leaks the raw schema into the UI — it names the tool, not the shape.
    expect(p).not.toMatch(/trust_rules/);
  });
});
