import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import KbRefreshReviewModal from '../components/KbRefreshReviewModal';

const UPDATES = [
  {
    university_id: 'neu',
    university_name: 'Northeastern University',
    fit_kb_year: 2025,
    current_kb_year: 2026,
    changes: [
      { field: 'acceptance_rate', old: 44, new: 35.2, severity: 'material' },
      { field: 'application_deadlines', severity: 'material' },
    ],
    projected_category_shift: 'SAFETY → TARGET',
  },
  {
    university_id: 'applied_u',
    university_name: 'Applied University',
    nudge_suppressed: true,
    changes: [{ field: 'acceptance_rate', old: 30, new: 20, severity: 'material' }],
  },
];

describe('KbRefreshReviewModal', () => {
  it('renders nothing when closed', () => {
    render(
      <KbRefreshReviewModal isOpen={false} kbUpdates={UPDATES} onClose={() => {}} onUpdateFit={async () => {}} />
    );
    expect(screen.queryByTestId('kb-refresh-review-modal')).toBeNull();
  });

  it('shows concrete old→new facts and the projected shift', () => {
    render(
      <KbRefreshReviewModal isOpen kbUpdates={UPDATES} onClose={() => {}} onUpdateFit={async () => {}} />
    );
    expect(screen.getByText('Northeastern University')).toBeInTheDocument();
    expect(screen.getByText('Acceptance rate 44% → 35.2%')).toBeInTheDocument();
    expect(screen.getByText('Application deadlines changed')).toBeInTheDocument();
    expect(screen.getByText(/Projected fit: SAFETY → TARGET/)).toBeInTheDocument();
  });

  it('excludes nudge-suppressed colleges from review', () => {
    render(
      <KbRefreshReviewModal isOpen kbUpdates={UPDATES} onClose={() => {}} onUpdateFit={async () => {}} />
    );
    expect(screen.queryByText('Applied University')).toBeNull();
  });

  it('per-college update calls onUpdateFit and flips to Updated', async () => {
    const onUpdateFit = vi.fn().mockResolvedValue();
    render(
      <KbRefreshReviewModal isOpen kbUpdates={UPDATES} onClose={() => {}} onUpdateFit={onUpdateFit} />
    );
    fireEvent.click(screen.getByText('Update fit analysis'));
    await waitFor(() => expect(screen.getByText('Updated')).toBeInTheDocument());
    expect(onUpdateFit).toHaveBeenCalledWith('neu');
  });

  it('failed update shows Retry, not Updated', async () => {
    const onUpdateFit = vi.fn().mockRejectedValue(new Error('boom'));
    render(
      <KbRefreshReviewModal isOpen kbUpdates={UPDATES} onClose={() => {}} onUpdateFit={onUpdateFit} />
    );
    fireEvent.click(screen.getByText('Update fit analysis'));
    await waitFor(() => expect(screen.getByText('Retry')).toBeInTheDocument());
    expect(screen.queryByText('Updated')).toBeNull();
  });

  it('shows the all-current empty state when every entry is suppressed', () => {
    render(
      <KbRefreshReviewModal
        isOpen
        kbUpdates={[UPDATES[1]]}
        onClose={() => {}}
        onUpdateFit={async () => {}}
      />
    );
    expect(screen.getByText(/all fit analyses are current/i)).toBeInTheDocument();
  });
});
