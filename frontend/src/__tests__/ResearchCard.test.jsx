import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ResearchCard from '../components/research/ResearchCard';

const baseNote = {
  research_id: 'rsh_1',
  title: 'Duke vs UCSD for CS',
  summary: 'Reach vs target tradeoffs',
  kind: 'comparison',
  body_markdown: '## Verdict\n\nDuke is a **reach**; UCSD is a target.',
  university_ids: ['duke_university', 'uc_san_diego'],
  tags: ['cs'],
  source: 'claude_mcp',
  created_at: '2026-06-14T00:00:00Z',
  provenance: { source: 'claude_mcp', kb_year: 2026 },
};

describe('ResearchCard', () => {
  it('renders the kind badge, title and summary', () => {
    render(<ResearchCard note={baseNote} />);
    expect(screen.getByTestId('research-kind-badge')).toHaveTextContent('Comparison');
    expect(screen.getByText('Duke vs UCSD for CS')).toBeInTheDocument();
    expect(screen.getByText('Reach vs target tradeoffs')).toBeInTheDocument();
  });

  it('shows linked colleges using the name map, prettifying unknown ids', () => {
    render(<ResearchCard note={baseNote} collegeNames={{ duke_university: 'Duke University' }} />);
    const chips = screen.getAllByTestId('research-college-chip').map((c) => c.textContent);
    expect(chips).toContain('Duke University'); // from map
    expect(chips).toContain('Uc San Diego'); // prettified fallback
  });

  it('expands and collapses the Markdown body', () => {
    render(<ResearchCard note={baseNote} />);
    expect(screen.queryByTestId('research-body')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /show details/i }));
    expect(screen.getByTestId('research-body')).toHaveTextContent('Duke is a reach');
    fireEvent.click(screen.getByRole('button', { name: /hide details/i }));
    expect(screen.queryByTestId('research-body')).not.toBeInTheDocument();
  });

  it('flags staleness when the note was based on an older KB cycle', () => {
    const stale = { ...baseNote, provenance: { source: 'claude_mcp', kb_year: 2020 } };
    render(<ResearchCard note={stale} />);
    expect(screen.getByTestId('research-stale-chip')).toHaveTextContent('newer cycle available');
  });

  it('does not flag staleness when no KB cycle was recorded', () => {
    const note = { ...baseNote, provenance: { source: 'claude_mcp' } };
    render(<ResearchCard note={note} />);
    expect(screen.queryByTestId('research-stale-chip')).not.toBeInTheDocument();
  });

  it('calls onDelete with the research id', () => {
    const onDelete = vi.fn();
    render(<ResearchCard note={baseNote} onDelete={onDelete} />);
    fireEvent.click(screen.getByRole('button', { name: /delete research/i }));
    expect(onDelete).toHaveBeenCalledWith('rsh_1');
  });

  it('shows no pin control unless onTogglePin is provided', () => {
    render(<ResearchCard note={baseNote} />);
    expect(screen.queryByRole('button', { name: /pin research/i })).not.toBeInTheDocument();
  });

  it('toggles pin: unpinned note pins on click', () => {
    const onTogglePin = vi.fn();
    render(<ResearchCard note={baseNote} onTogglePin={onTogglePin} />);
    const btn = screen.getByRole('button', { name: /pin research/i });
    expect(btn).toHaveAttribute('aria-pressed', 'false');
    fireEvent.click(btn);
    expect(onTogglePin).toHaveBeenCalledWith(baseNote, true);
  });

  it('renders a pinned note as pressed/highlighted and unpins on click', () => {
    const onTogglePin = vi.fn();
    const pinned = { ...baseNote, pinned: true };
    render(<ResearchCard note={pinned} onTogglePin={onTogglePin} />);
    expect(screen.getByTestId('research-card')).toHaveAttribute('data-pinned', 'true');
    const btn = screen.getByRole('button', { name: /unpin research/i });
    expect(btn).toHaveAttribute('aria-pressed', 'true');
    fireEvent.click(btn);
    expect(onTogglePin).toHaveBeenCalledWith(pinned, false);
  });
});

describe('ResearchCard — repeat workflow widget', () => {
  const wfNote = {
    research_id: 'rsh_w', title: 'Duke vs UCSD', kind: 'comparison', body_markdown: 'x', source: 'claude',
    source_prompt: 'Compare Duke and UCSD for CS',
    workflow: [
      { tool: 'get_profile', label: 'Pulled profile' },
      { tool: 'get_fit_analysis', label: 'Got Duke & UCSD fit' },
    ],
  };

  it('renders Run-in-agent links built from the repeat prompt', () => {
    render(<ResearchCard note={wfNote} />);
    expect(screen.getByTestId('research-workflow')).toBeInTheDocument();
    const claude = screen.getByRole('link', { name: /run in claude/i });
    expect(claude.getAttribute('href')).toContain('claude.ai');
    expect(claude.getAttribute('href')).toContain(encodeURIComponent('Compare Duke and UCSD for CS'));
    expect(screen.getByRole('link', { name: /chatgpt/i }).getAttribute('href')).toContain('chatgpt.com');
  });

  it('expands to show the original ask and ordered steps', () => {
    render(<ResearchCard note={wfNote} />);
    fireEvent.click(screen.getByRole('button', { name: /^workflow/i }));
    expect(screen.getByText(/Compare Duke and UCSD for CS/)).toBeInTheDocument();
    expect(screen.getByText(/Pulled profile/)).toBeInTheDocument();
    expect(screen.getByText(/Got Duke & UCSD fit/)).toBeInTheDocument();
  });

  it('hides the widget when the note has no workflow', () => {
    render(<ResearchCard note={{ research_id: 'x', title: 't', kind: 'note', body_markdown: 'b' }} />);
    expect(screen.queryByTestId('research-workflow')).not.toBeInTheDocument();
  });
});
