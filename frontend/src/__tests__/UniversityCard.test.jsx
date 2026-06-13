import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import UniversityCard from '../components/stratia/UniversityCard';

const baseUni = {
  university_name: 'Duke University',
  university_id: 'duke',
  location: 'Durham, North Carolina',
  fit_category: 'SUPER_REACH',
  match_score: 34,
};

const STALE = { fit_kb_year: 2025, current_kb_year: 2026 };

describe('UniversityCard — Fit Analysis split control', () => {
  it('current fit: a single view button, no update segment', () => {
    const onViewAnalysis = vi.fn();
    const onUpdateFit = vi.fn();
    render(
      <UniversityCard
        university={{ ...baseUni, kb_data_year: 2026, kb_update: null }}
        onViewAnalysis={onViewAnalysis}
        onUpdateFit={onUpdateFit}
      />
    );
    const view = screen.getByRole('button', { name: /view fit analysis/i });
    expect(view).toHaveTextContent('Fit Analysis');
    expect(screen.queryByRole('button', { name: /update fit analysis with new data/i })).toBeNull();
    fireEvent.click(view);
    expect(onViewAnalysis).toHaveBeenCalledTimes(1);
    expect(onUpdateFit).not.toHaveBeenCalled();
  });

  it('stale fit: keeps a view button AND adds an update segment', () => {
    const onViewAnalysis = vi.fn();
    const onUpdateFit = vi.fn().mockResolvedValue(undefined);
    render(
      <UniversityCard
        university={{ ...baseUni, kb_data_year: 2025, kb_update: STALE }}
        onViewAnalysis={onViewAnalysis}
        onUpdateFit={onUpdateFit}
      />
    );

    // View still works without triggering a recompute (the regression we fixed).
    const view = screen.getByRole('button', { name: /view fit analysis/i });
    fireEvent.click(view);
    expect(onViewAnalysis).toHaveBeenCalledTimes(1);
    expect(onUpdateFit).not.toHaveBeenCalled();

    // The chip states the vintage; the CTA lives on the update segment.
    expect(screen.getByTestId('fit-vintage-chip')).not.toHaveTextContent('update available');

    // Update segment recomputes.
    const update = screen.getByRole('button', { name: /update fit analysis with new data/i });
    fireEvent.click(update);
    expect(onUpdateFit).toHaveBeenCalledTimes(1);
    expect(update).toHaveTextContent('Updating…');
  });

  it('surfaces an error and re-enables the update segment on failure', async () => {
    const onUpdateFit = vi.fn().mockRejectedValue(new Error('boom'));
    render(
      <UniversityCard
        university={{ ...baseUni, kb_data_year: 2025, kb_update: STALE }}
        onViewAnalysis={vi.fn()}
        onUpdateFit={onUpdateFit}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: /update fit analysis with new data/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/update failed/i);
    expect(screen.getByRole('button', { name: /update fit analysis with new data/i })).not.toBeDisabled();
  });
});
