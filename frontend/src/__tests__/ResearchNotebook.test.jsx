import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

// Mock the API layer + auth so the page renders in isolation.
const { listResearch, getCollegeList, deleteResearch, getPopularWorkflows, pinResearch, fetchUserProfile } = vi.hoisted(() => ({
  listResearch: vi.fn(),
  getCollegeList: vi.fn().mockResolvedValue({ success: true, colleges: [] }),
  deleteResearch: vi.fn().mockResolvedValue({ success: true }),
  getPopularWorkflows: vi.fn().mockResolvedValue({ success: true, workflows: [] }),
  pinResearch: vi.fn().mockResolvedValue({ success: true }),
  fetchUserProfile: vi.fn().mockResolvedValue({ success: true, profile: {} }),
}));
vi.mock('../services/api', () => ({ listResearch, getCollegeList, deleteResearch, getPopularWorkflows, pinResearch, fetchUserProfile }));
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
vi.mock('../components/research/WorkflowGroupCard', () => ({
  default: ({ group }) => <div data-testid="wf-group">{group.name}</div>,
}));
vi.mock('../components/research/PopularWorkflowCard', () => ({
  default: ({ wf }) => <div data-testid="popular-wf">{wf.signature}</div>,
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

describe('ResearchNotebook — workflows view', () => {
  beforeEach(() => {
    listResearch.mockReset();
    getCollegeList.mockResolvedValue({ success: true, colleges: [] });
  });

  it('switches to the Workflows view and shows grouped workflows', async () => {
    listResearch.mockResolvedValue({ success: true, research: [
      { research_id: 'a', title: 'Duke vs UCSD', kind: 'comparison', created_at: '2026-06-01', source_prompt: 'compare colleges', workflow_signature: 'get_profile>get_fit', workflow: [{ tool: 'get_profile', label: 'profile' }] },
      { research_id: 'b', title: 'UCLA vs Cal', kind: 'comparison', created_at: '2026-06-10', source_prompt: 'compare colleges', workflow_signature: 'get_profile>get_fit', workflow: [{ tool: 'get_profile', label: 'profile' }] },
    ] });
    renderPage();
    await waitFor(() => expect(screen.getAllByTestId('card')).toHaveLength(2));
    fireEvent.click(screen.getByRole('tab', { name: /Workflows/ }));
    // the two researches share one workflow → one group
    expect(screen.getAllByTestId('wf-group')).toHaveLength(1);
    expect(screen.getByText('compare colleges')).toBeInTheDocument();
  });
});

describe('ResearchNotebook — popular workflows view', () => {
  beforeEach(() => {
    listResearch.mockResolvedValue({ success: true, research: [{ research_id: 'a', title: 'T', kind: 'note' }] });
    getCollegeList.mockResolvedValue({ success: true, colleges: [] });
    getPopularWorkflows.mockResolvedValue({ success: true, workflows: [
      { signature: 'get_profile>get_fit_analysis', tools: ['get_profile', 'get_fit_analysis'], kind: 'comparison', count: 9 },
      { signature: 'get_roadmap>get_deadlines', tools: ['get_roadmap', 'get_deadlines'], kind: 'timeline', count: 4 },
    ] });
  });

  it('shows popular workflows when the Popular tab is selected', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByRole('tab', { name: /Popular/ })).toBeInTheDocument());
    fireEvent.click(screen.getByRole('tab', { name: /Popular/ }));
    expect(screen.getAllByTestId('popular-wf')).toHaveLength(2);
  });
});
