/**
 * KB vintage helpers for fit-staleness UX (design DESIGN-kb-refresh-fit-staleness.md).
 *
 * A fit analysis is stamped with kb_data_year — the admission-cycle year of
 * the university data it was computed against (2026 = the 2026–27 cycle).
 * check-fit-recomputation returns kb_updates[] describing saved fits whose
 * KB inputs are stale.
 */

/** 2026 → "2026–27". Returns null for missing/invalid years. */
export function cycleLabel(year) {
  const y = Number(year);
  if (!Number.isInteger(y) || y < 2000 || y > 2100) return null;
  return `${y}–${String((y + 1) % 100).padStart(2, '0')}`;
}

/**
 * The current admissions-cycle (KB data) year. The new cycle's data lands
 * around August, so we roll forward then. Used to flag saved research/fits
 * that were produced against a now-superseded cycle.
 */
export function currentCycleYear(now = new Date()) {
  const y = now.getFullYear();
  return now.getMonth() >= 7 ? y + 1 : y; // month 7 = August
}

/** The kb_updates entry for one university, or null. */
export function kbUpdateFor(kbUpdates, universityId) {
  if (!Array.isArray(kbUpdates)) return null;
  return kbUpdates.find((u) => u.university_id === universityId) || null;
}

/** Entries that justify an active nudge: material change, not suppressed. */
export function materialUpdates(kbUpdates) {
  if (!Array.isArray(kbUpdates)) return [];
  return kbUpdates.filter(
    (u) =>
      !u.nudge_suppressed &&
      (u.changes || []).some((c) => c.severity === 'material')
  );
}

/**
 * Chip state for a rendered fit:
 *   { tone: 'current'|'stale'|'unknown', label, vintage } or null.
 * `label` carries the "— update available" call-to-action; `vintage` is the
 * bare data-cycle statement for surfaces that carry the CTA elsewhere (e.g.
 * the Launchpad card, whose Fit Analysis button morphs into "Update Fit").
 * Vintage chips render even when nudges are suppressed — passive
 * transparency is the point (design §3e).
 */
export function vintageChip(fit, kbUpdate) {
  const fitYear = fit?.kb_data_year;
  if (kbUpdate) {
    const fromLabel = cycleLabel(kbUpdate.fit_kb_year);
    if (!fromLabel) {
      // Legacy fit with no recorded cycle — don't surface internal "data
      // versioning" wording. Just signal a refresh is available; on the card
      // the chip stays silent (the Update button carries the action).
      return { tone: 'unknown', label: 'Update available', vintage: null };
    }
    const vintage = `${fromLabel} data`;
    return { tone: 'stale', label: `${vintage} — update available`, vintage };
  }
  const label = cycleLabel(fitYear);
  if (!label) return null; // legacy fit, no staleness info — say nothing
  const vintage = `Based on ${label} data`;
  return { tone: 'current', label: vintage, vintage };
}

/**
 * True when a saved fit was computed against superseded KB data and a fresh
 * recompute is available. Drives the "Update Fit" affordance on the card.
 */
export function fitUpdateAvailable(kbUpdate) {
  return Boolean(kbUpdate);
}

/** "New 2026–27 admissions data available" tooltip line, or a generic fallback. */
export function updateTooltip(kbUpdate) {
  const cycle = cycleLabel(kbUpdate?.current_kb_year);
  return cycle
    ? `New ${cycle} admissions data available — refresh your fit analysis`
    : 'New admissions data available — refresh your fit analysis';
}

/** One-line human summary of a kb_updates entry's changes (for cards). */
export function describeChange(change) {
  if (!change) return '';
  switch (change.field) {
    case 'acceptance_rate':
      return `Acceptance rate ${change.old}% → ${change.new}%`;
    case 'application_deadlines':
      return 'Application deadlines changed';
    case 'test_policy':
      return 'Testing policy changed';
    case 'total_coa':
      return `Cost of attendance $${Number(change.old).toLocaleString()} → $${Number(change.new).toLocaleString()}`;
    case 'kb_data_year':
      return 'Newer cycle data available (no major changes detected)';
    case 'provenance':
      return 'Newer data available';
    default:
      return change.detail || `${change.field} changed`;
  }
}
