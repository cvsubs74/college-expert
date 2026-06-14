import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

const { saveResearch, updateResearch } = vi.hoisted(() => ({
  saveResearch: vi.fn().mockResolvedValue({ success: true, research_id: 'rsh_new' }),
  updateResearch: vi.fn().mockResolvedValue({ success: true }),
}));
vi.mock('../services/api', () => ({ saveResearch, updateResearch }));
vi.mock('../components/Toast', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn() }),
}));

import ResearchEditorModal from '../components/research/ResearchEditorModal';

const COLLEGES = [
  { university_id: 'duke_university', university_name: 'Duke University' },
  { university_id: 'uc_san_diego', university_name: 'UC San Diego' },
];

describe('ResearchEditorModal', () => {
  beforeEach(() => {
    saveResearch.mockClear();
    updateResearch.mockClear();
  });

  it('renders nothing when closed', () => {
    const { container } = render(<ResearchEditorModal isOpen={false} userEmail="a@b.com" onClose={vi.fn()} onSaved={vi.fn()} />);
    expect(container.firstChild).toBeNull();
  });

  it('creates a note via saveResearch with the entered fields', async () => {
    const onSaved = vi.fn();
    const onClose = vi.fn();
    render(<ResearchEditorModal isOpen userEmail="a@b.com" onClose={onClose} onSaved={onSaved} colleges={COLLEGES} />);

    expect(screen.getByText('New research')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'My comparison' } });
    fireEvent.change(screen.getByLabelText('Details (Markdown)'), { target: { value: '## body' } });
    fireEvent.change(screen.getByLabelText(/Tags/), { target: { value: 'cs, reach' } });
    fireEvent.click(screen.getByLabelText('Duke University')); // link a college

    fireEvent.click(screen.getByRole('button', { name: /save research/i }));
    await waitFor(() => expect(saveResearch).toHaveBeenCalledTimes(1));
    const [email, payload] = saveResearch.mock.calls[0];
    expect(email).toBe('a@b.com');
    expect(payload.title).toBe('My comparison');
    expect(payload.bodyMarkdown).toBe('## body');
    expect(payload.tags).toEqual(['cs', 'reach']);
    expect(payload.universityIds).toEqual(['duke_university']);
    expect(onSaved).toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });

  it('edits an existing note via updateResearch (prefilled, partial update)', async () => {
    const existing = {
      research_id: 'rsh_1', title: 'Old', summary: 's', body_markdown: 'b',
      kind: 'strategy', university_ids: ['uc_san_diego'], tags: ['x'],
    };
    render(<ResearchEditorModal isOpen userEmail="a@b.com" onClose={vi.fn()} onSaved={vi.fn()} colleges={COLLEGES} existing={existing} />);

    expect(screen.getByText('Edit research')).toBeInTheDocument();
    expect(screen.getByLabelText('Title')).toHaveValue('Old');           // prefilled
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'New title' } });
    fireEvent.click(screen.getByRole('button', { name: /save changes/i }));

    await waitFor(() => expect(updateResearch).toHaveBeenCalledTimes(1));
    const [email, id, patch] = updateResearch.mock.calls[0];
    expect(email).toBe('a@b.com');
    expect(id).toBe('rsh_1');
    expect(patch.title).toBe('New title');
    expect(saveResearch).not.toHaveBeenCalled();
  });

  it('disables save until title and body are filled', () => {
    render(<ResearchEditorModal isOpen userEmail="a@b.com" onClose={vi.fn()} onSaved={vi.fn()} />);
    const btn = screen.getByRole('button', { name: /save research/i });
    expect(btn).toBeDisabled();
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'T' } });
    expect(btn).toBeDisabled(); // body still empty
    fireEvent.change(screen.getByLabelText('Details (Markdown)'), { target: { value: 'B' } });
    expect(btn).toBeEnabled();
  });
});
