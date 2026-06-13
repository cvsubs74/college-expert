import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import FitUpdateBanner from '../components/FitUpdateBanner';

describe('FitUpdateBanner', () => {
  it('renders nothing when the fit is current', () => {
    const { container } = render(<FitUpdateBanner kbUpdate={null} onUpdate={vi.fn()} />);
    expect(container.firstChild).toBeNull();
  });

  it('shows old→new cycle context and recomputes on click', () => {
    const onUpdate = vi.fn().mockResolvedValue(undefined);
    render(<FitUpdateBanner kbUpdate={{ fit_kb_year: 2025, current_kb_year: 2026 }} onUpdate={onUpdate} />);
    const banner = screen.getByTestId('fit-update-banner');
    expect(banner).toHaveTextContent('based on 2025–26 data');
    expect(banner).toHaveTextContent('2026–27 admissions data is available');

    const btn = screen.getByRole('button', { name: /update analysis/i });
    fireEvent.click(btn);
    expect(onUpdate).toHaveBeenCalledTimes(1);
    expect(btn).toHaveTextContent('Updating…');
  });

  it('handles a legacy (pre-versioning) fit with no fit year', () => {
    render(<FitUpdateBanner kbUpdate={{ fit_kb_year: null, current_kb_year: 2026 }} onUpdate={vi.fn()} />);
    expect(screen.getByTestId('fit-update-banner')).toHaveTextContent('predates data versioning');
  });

  it('surfaces an error and re-enables the button on failure', async () => {
    const onUpdate = vi.fn().mockRejectedValue(new Error('boom'));
    render(<FitUpdateBanner kbUpdate={{ fit_kb_year: 2025, current_kb_year: 2026 }} onUpdate={onUpdate} />);
    fireEvent.click(screen.getByRole('button', { name: /update analysis/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/update failed/i);
    expect(screen.getByRole('button', { name: /update analysis/i })).not.toBeDisabled();
  });
});
