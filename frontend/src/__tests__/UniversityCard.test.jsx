import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import UniversityCard from '../components/stratia/UniversityCard';

const baseUni = {
  university_name: 'Duke University',
  university_id: 'duke',
  location: 'Durham, North Carolina',
  fit_category: 'SUPER_REACH',
  match_score: 34,
};

describe('UniversityCard — Fit Analysis / Update Fit button', () => {
  it('shows "Fit Analysis" and opens analysis when the fit is current', () => {
    const onViewAnalysis = vi.fn();
    const onUpdateFit = vi.fn();
    render(
      <UniversityCard
        university={{ ...baseUni, kb_data_year: 2026, kb_update: null }}
        onViewAnalysis={onViewAnalysis}
        onUpdateFit={onUpdateFit}
      />
    );
    const btn = screen.getByRole('button', { name: /view fit analysis/i });
    expect(btn).toHaveTextContent('Fit Analysis');
    fireEvent.click(btn);
    expect(onViewAnalysis).toHaveBeenCalledTimes(1);
    expect(onUpdateFit).not.toHaveBeenCalled();
  });

  it('morphs to "Update Fit" and recomputes when the fit is stale', async () => {
    const onViewAnalysis = vi.fn();
    const onUpdateFit = vi.fn().mockResolvedValue(undefined);
    render(
      <UniversityCard
        university={{
          ...baseUni,
          kb_data_year: 2025,
          kb_update: { fit_kb_year: 2025, current_kb_year: 2026 },
        }}
        onViewAnalysis={onViewAnalysis}
        onUpdateFit={onUpdateFit}
      />
    );
    const btn = screen.getByRole('button', { name: /update fit analysis with new data/i });
    expect(btn).toHaveTextContent('Update Fit');
    // The card's chip states the vintage, not a duplicate CTA.
    expect(screen.getByTestId('fit-vintage-chip')).not.toHaveTextContent('update available');

    fireEvent.click(btn);
    expect(onUpdateFit).toHaveBeenCalledTimes(1);
    expect(onViewAnalysis).not.toHaveBeenCalled();
    // Spinner state while awaiting recompute.
    expect(btn).toHaveTextContent('Updating…');
    await waitFor(() => expect(onUpdateFit).toHaveBeenCalled());
  });

  it('surfaces an error and re-enables the button when the update fails', async () => {
    const onUpdateFit = vi.fn().mockRejectedValue(new Error('boom'));
    render(
      <UniversityCard
        university={{
          ...baseUni,
          kb_data_year: 2025,
          kb_update: { fit_kb_year: 2025, current_kb_year: 2026 },
        }}
        onViewAnalysis={vi.fn()}
        onUpdateFit={onUpdateFit}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: /update fit analysis with new data/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/update failed/i);
    expect(screen.getByRole('button', { name: /update fit analysis with new data/i })).toHaveTextContent('Update Fit');
  });
});
