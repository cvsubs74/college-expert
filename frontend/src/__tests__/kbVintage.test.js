import { describe, it, expect } from 'vitest';
import {
  cycleLabel,
  kbUpdateFor,
  materialUpdates,
  vintageChip,
  describeChange,
  fitUpdateAvailable,
  updateTooltip,
} from '../utils/kbVintage';

describe('cycleLabel', () => {
  it('formats an admission cycle year', () => {
    expect(cycleLabel(2026)).toBe('2026–27');
    expect(cycleLabel(2029)).toBe('2029–30');
  });
  it('pads the century rollover', () => {
    expect(cycleLabel(2099)).toBe('2099–00');
  });
  it('rejects garbage', () => {
    expect(cycleLabel(null)).toBeNull();
    expect(cycleLabel(undefined)).toBeNull();
    expect(cycleLabel('soon')).toBeNull();
    expect(cycleLabel(1850)).toBeNull();
  });
});

describe('materialUpdates (banner gating)', () => {
  const material = {
    university_id: 'neu',
    changes: [{ field: 'acceptance_rate', severity: 'material' }],
  };
  const minor = {
    university_id: 'bu',
    changes: [{ field: 'total_coa', severity: 'minor' }],
  };

  it('keeps only material, unsuppressed entries', () => {
    expect(materialUpdates([material, minor])).toEqual([material]);
  });

  it('drops suppressed entries even when material', () => {
    const suppressed = { ...material, nudge_suppressed: true };
    expect(materialUpdates([suppressed, minor])).toEqual([]);
  });

  it('empty/missing input → no banner', () => {
    expect(materialUpdates([])).toEqual([]);
    expect(materialUpdates(null)).toEqual([]);
  });
});

describe('vintageChip', () => {
  it('current fit → neutral chip with cycle label', () => {
    const chip = vintageChip({ kb_data_year: 2026 }, null);
    expect(chip).toEqual({ tone: 'current', label: 'Based on 2026–27 data', vintage: 'Based on 2026–27 data' });
  });

  it('stale fit → amber update-available chip', () => {
    const chip = vintageChip(
      { kb_data_year: 2025 },
      { fit_kb_year: 2025, current_kb_year: 2026 }
    );
    expect(chip.tone).toBe('stale');
    expect(chip.label).toBe('2025–26 data — update available');
    expect(chip.vintage).toBe('2025–26 data');
  });

  it('suppressed entries still get a chip (passive transparency)', () => {
    const chip = vintageChip(
      { kb_data_year: 2025 },
      { fit_kb_year: 2025, current_kb_year: 2026, nudge_suppressed: true }
    );
    expect(chip.tone).toBe('stale');
  });

  it('legacy fit with a kb_update → unknown tone, neutral "Update available", silent vintage', () => {
    const chip = vintageChip({}, { fit_kb_year: null, current_kb_year: 2026 });
    expect(chip.tone).toBe('unknown');
    expect(chip.label).toBe('Update available');
    expect(chip.label).not.toMatch(/data versioning/i);
    expect(chip.vintage).toBeNull();  // card chip stays silent; button carries the CTA
  });

  it('legacy fit with no staleness info → silent (no clutter)', () => {
    expect(vintageChip({}, null)).toBeNull();
    expect(vintageChip(null, null)).toBeNull();
  });
});

describe('fitUpdateAvailable / updateTooltip', () => {
  it('is true exactly when a kb_update is present', () => {
    expect(fitUpdateAvailable({ fit_kb_year: 2025, current_kb_year: 2026 })).toBe(true);
    expect(fitUpdateAvailable(null)).toBe(false);
    expect(fitUpdateAvailable(undefined)).toBe(false);
  });

  it('builds a cycle-aware tooltip, with a generic fallback', () => {
    expect(updateTooltip({ current_kb_year: 2026 })).toBe(
      'New 2026–27 admissions data available — refresh your fit analysis'
    );
    expect(updateTooltip({})).toBe(
      'New admissions data available — refresh your fit analysis'
    );
  });
});

describe('kbUpdateFor / describeChange', () => {
  it('finds the entry for a university', () => {
    const updates = [{ university_id: 'neu' }, { university_id: 'bu' }];
    expect(kbUpdateFor(updates, 'bu')).toEqual({ university_id: 'bu' });
    expect(kbUpdateFor(updates, 'mit')).toBeNull();
    expect(kbUpdateFor(undefined, 'mit')).toBeNull();
  });

  it('renders human change lines', () => {
    expect(describeChange({ field: 'acceptance_rate', old: 44, new: 35.2 }))
      .toBe('Acceptance rate 44% → 35.2%');
    expect(describeChange({ field: 'application_deadlines' }))
      .toBe('Application deadlines changed');
    expect(describeChange({ field: 'total_coa', old: 82000, new: 86000 }))
      .toBe('Cost of attendance $82,000 → $86,000');
  });
});
