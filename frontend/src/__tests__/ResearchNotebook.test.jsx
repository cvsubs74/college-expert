import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';

// Mock the API layer + auth so the page renders in isolation.
const { listResearch, getCollegeList, deleteResearch } = vi.hoisted(() => ({
  listResearch: vi.fn(),
  getCollegeList: vi.fn().mockResolvedValue({ success: true, colleges: [] }),
  deleteResearch: vi.fn().mockResolvedValue({ success: true }),
}));
vi.mock('../services/api', () => ({ listResearch, getCollegeList, deleteResearch }));
vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({ currentUser: { email: 'stu@example.com' } }),
}));
// Keep the card a sentinel — its own behavior is covered in ResearchCard.test.
vi.mock('../components/research/ResearchCard', () => ({
  default: ({ note }) => <div data-testid="card" data-kind={note.kind}>{note.title}</div>,
}));

import ResearchNotebook from '../pages/ResearchNotebook';

const NOTES = [
  { research_id: 'a', title: 'Duke vs UCSD', kind: 'comparison' },
  { research_id: 'b', title: 'Application timeline', kind: 'timeline' },
  { research_id: 'c', title: 'Random note', kind: 'note' },
];

describe('ResearchNotebook', () => {
  beforeEach(() => {
    listResearch.mockReset();
    getCollegeList.mockResolvedValue({ success: true, colleges: [] });
  });

  it('renders a card per saved note', async () => {
    listResearch.mockResolvedValue({ success: true, research: NOTES });
    render(<ResearchNotebook />);
    await waitFor(() => expect(screen.getAllByTestId('card')).toHaveLength(3));
    expect(screen.getByText('Duke vs UCSD')).toBeInTheDocument();
  });

  it('shows the empty state with a Claude hint when there is no research', async () => {
    listResearch.mockResolvedValue({ success: true, research: [] });
    render(<ResearchNotebook />);
    await waitFor(() => expect(screen.getByTestId('research-empty')).toBeInTheDocument());
    expect(screen.getByTestId('research-empty')).toHaveTextContent(/Claude/);
  });

  it('filters the feed by kind', async () => {
    listResearch.mockResolvedValue({ success: true, research: NOTES });
    render(<ResearchNotebook />);
    await waitFor(() => expect(screen.getAllByTestId('card')).toHaveLength(3));
    fireEvent.click(screen.getByRole('tab', { name: /Timeline/ }));
    const cards = screen.getAllByTestId('card');
    expect(cards).toHaveLength(1);
    expect(cards[0]).toHaveTextContent('Application timeline');
  });
});
