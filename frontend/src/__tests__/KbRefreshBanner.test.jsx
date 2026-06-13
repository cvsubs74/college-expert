import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import KbRefreshBanner from '../components/KbRefreshBanner';
import FitVintageChip from '../components/FitVintageChip';

const MATERIAL = {
  university_id: 'neu',
  university_name: 'Northeastern University',
  current_kb_year: 2026,
  changes: [{ field: 'acceptance_rate', old: 44, new: 35.2, severity: 'material' }],
};
const MINOR = {
  university_id: 'bu',
  current_kb_year: 2026,
  changes: [{ field: 'total_coa', old: 82000, new: 86000, severity: 'minor' }],
};

beforeEach(() => {
  localStorage.clear();
});

describe('KbRefreshBanner', () => {
  it('renders for material changes with cycle label and count', () => {
    render(<KbRefreshBanner kbUpdates={[MATERIAL]} onReview={() => {}} />);
    expect(screen.getByTestId('kb-refresh-banner')).toBeInTheDocument();
    expect(screen.getByText(/2026–27 admissions data is in/)).toBeInTheDocument();
    expect(screen.getByText(/1 college on your list changed/)).toBeInTheDocument();
  });

  it('does not render for minor-only changes', () => {
    render(<KbRefreshBanner kbUpdates={[MINOR]} onReview={() => {}} />);
    expect(screen.queryByTestId('kb-refresh-banner')).toBeNull();
  });

  it('does not render when all material changes are nudge-suppressed', () => {
    render(
      <KbRefreshBanner
        kbUpdates={[{ ...MATERIAL, nudge_suppressed: true }]}
        onReview={() => {}}
      />
    );
    expect(screen.queryByTestId('kb-refresh-banner')).toBeNull();
  });

  it('review CTA fires onReview', () => {
    const onReview = vi.fn();
    render(<KbRefreshBanner kbUpdates={[MATERIAL]} onReview={onReview} />);
    fireEvent.click(screen.getByText('Review what changed'));
    expect(onReview).toHaveBeenCalledOnce();
  });

  it('remembers dismissal even when kbUpdates arrives after mount', () => {
    // Real pages mount the banner with [] and the fetch fills it in later;
    // the stored flag must be honored when `year` becomes known.
    localStorage.setItem('kb_refresh_banner_dismissed_2026', '1');
    const { rerender } = render(<KbRefreshBanner kbUpdates={[]} onReview={() => {}} />);
    expect(screen.queryByTestId('kb-refresh-banner')).toBeNull();
    rerender(<KbRefreshBanner kbUpdates={[MATERIAL]} onReview={() => {}} />);
    expect(screen.queryByTestId('kb-refresh-banner')).toBeNull();
  });

  it('dismissal hides the banner and is remembered per cycle year', () => {
    const { unmount } = render(<KbRefreshBanner kbUpdates={[MATERIAL]} onReview={() => {}} />);
    fireEvent.click(screen.getByText('Later'));
    expect(screen.queryByTestId('kb-refresh-banner')).toBeNull();
    unmount();

    // Remount: still dismissed for the same year
    render(<KbRefreshBanner kbUpdates={[MATERIAL]} onReview={() => {}} />);
    expect(screen.queryByTestId('kb-refresh-banner')).toBeNull();

    // A NEW cycle year banners again
    expect(localStorage.getItem('kb_refresh_banner_dismissed_2026')).toBe('1');
    expect(localStorage.getItem('kb_refresh_banner_dismissed_2027')).toBeNull();
  });
});

describe('FitVintageChip', () => {
  it('neutral chip for a current fit', () => {
    render(<FitVintageChip fit={{ kb_data_year: 2026 }} kbUpdate={null} />);
    const chip = screen.getByTestId('fit-vintage-chip');
    expect(chip).toHaveAttribute('data-tone', 'current');
    expect(chip).toHaveTextContent('Based on 2026–27 data');
  });

  it('amber chip when an update is available', () => {
    render(
      <FitVintageChip
        fit={{ kb_data_year: 2025 }}
        kbUpdate={{ fit_kb_year: 2025, current_kb_year: 2026 }}
      />
    );
    const chip = screen.getByTestId('fit-vintage-chip');
    expect(chip).toHaveAttribute('data-tone', 'stale');
    expect(chip).toHaveTextContent('2025–26 data — update available');
  });

  it('renders nothing for a legacy fit with no staleness info', () => {
    render(<FitVintageChip fit={{}} kbUpdate={null} />);
    expect(screen.queryByTestId('fit-vintage-chip')).toBeNull();
  });

  it('vintageOnly drops the "update available" CTA (button carries it)', () => {
    render(
      <FitVintageChip
        fit={{ kb_data_year: 2025 }}
        kbUpdate={{ fit_kb_year: 2025, current_kb_year: 2026 }}
        vintageOnly
      />
    );
    const chip = screen.getByTestId('fit-vintage-chip');
    expect(chip).toHaveAttribute('data-tone', 'stale');
    expect(chip).toHaveTextContent('2025–26 data');
    expect(chip).not.toHaveTextContent('update available');
  });
});
