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
});
