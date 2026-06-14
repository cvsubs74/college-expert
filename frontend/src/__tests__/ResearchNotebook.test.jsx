import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

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
// Keep heavy children as sentinels — covered by their own tests.
vi.mock('../components/research/ResearchCard', () => ({
  default: ({ note }) => <div data-testid="card" data-kind={note.kind}>{note.title}</div>,
}));
vi.mock('../components/research/ResearchEditorModal', () => ({
  default: ({ isOpen }) => (isOpen ? <div data-testid="editor-modal" /> : null),
}));

import ResearchNotebook from '../pages/ResearchNotebook';

const NOTES = [
  { research_id: 'a', title: 'Duke vs UCSD', kind: 'comparison' },
  { research_id: 'b', title: 'Application timeline', kind: 'timeline' },
  { research_id: 'c', title: 'Random note', kind: 'note' },
];

const renderPage = () => render(<MemoryRouter><ResearchNotebook /></MemoryRouter>);

describe('ResearchNotebook', () => {
  beforeEach(() => {
    listResearch.mockReset();
    getCollegeList.mockResolvedValue({ success: true, colleges: [] });
  });

  it('renders a card per saved note', async () => {
    listResearch.mockResolvedValue({ success: true, research: NOTES });
    renderPage();
    await waitFor(() => expect(screen.getAllByTestId('card')).toHaveLength(3));
    expect(screen.getByText('Duke vs UCSD')).toBeInTheDocument();
  });

  it('shows the empty state with a manual + connect path when there is no research', async () => {
    listResearch.mockResolvedValue({ success: true, research: [] });
    renderPage();
    await waitFor(() => expect(screen.getByTestId('research-empty')).toBeInTheDocument());
    // source-agnostic: links to connect an agent AND offers manual creation
    expect(screen.getByRole('link', { name: /connect an ai agent/i })).toHaveAttribute('href', '/connect');
    expect(screen.getAllByRole('button', { name: /new research/i }).length).toBeGreaterThan(0);
  });

  it('opens the editor modal from the New research button', async () => {
    listResearch.mockResolvedValue({ success: true, research: [] });
    renderPage();
    await waitFor(() => expect(screen.getByTestId('research-empty')).toBeInTheDocument());
    expect(screen.queryByTestId('editor-modal')).not.toBeInTheDocument();
    fireEvent.click(screen.getAllByRole('button', { name: /new research/i })[0]);
    expect(screen.getByTestId('editor-modal')).toBeInTheDocument();
  });

  it('filters the feed by kind', async () => {
    listResearch.mockResolvedValue({ success: true, research: NOTES });
    renderPage();
    await waitFor(() => expect(screen.getAllByTestId('card')).toHaveLength(3));
    fireEvent.click(screen.getByRole('tab', { name: /Timeline/ }));
    const cards = screen.getAllByTestId('card');
    expect(cards).toHaveLength(1);
    expect(cards[0]).toHaveTextContent('Application timeline');
  });
});
