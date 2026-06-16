/**
 * Reach / Target / Safety balance helpers for the college-list ring. Pure and
 * unit-tested. "reach" folds SUPER_REACH into REACH to match the Launchpad's
 * existing bands, so the ring summarizes exactly the categorization already on
 * the page (it can't claim a balance the list doesn't show).
 */

/** The three bands, in display order, with the ring/legend colors. */
export const BALANCE_BANDS = [
  { key: 'reach', label: 'Reach', color: '#C2410C' },   // orange-700
  { key: 'target', label: 'Target', color: '#1A4D2E' }, // brand green
  { key: 'safety', label: 'Safety', color: '#0369A1' }, // sky-700
];

/**
 * The category to bucket a college into for the balance ring: the student's
 * PERSONALIZED fit first (from a computed fit analysis, surfaced either nested
 * as `fit_analysis.fit_category` or top-level `fit_category` by the enriched
 * endpoint), then the population-level `soft_fit_category`. Null when neither.
 */
export function collegeFitCategory(college) {
  return college?.fit_analysis?.fit_category
    || college?.fit_category
    || college?.soft_fit_category
    || null;
}

/**
 * True when a college's band is only an admit-rate ESTIMATE — i.e. it has no
 * personalized fit (so the ring can honestly say how many are estimated).
 */
export function isEstimatedFit(college) {
  return !(college?.fit_analysis?.fit_category || college?.fit_category);
}

/**
 * Donut segments for the ring: each band with its count and fraction of the
 * total. Empty bands keep a zero fraction (so the legend can still list them).
 * @param {{reach?:number,target?:number,safety?:number}} counts
 */
export function balanceSegments({ reach = 0, target = 0, safety = 0 } = {}) {
  const counts = { reach, target, safety };
  const total = reach + target + safety;
  return BALANCE_BANDS.map((b) => ({
    ...b,
    count: counts[b.key],
    fraction: total > 0 ? counts[b.key] / total : 0,
  }));
}

/**
 * A human verdict on list balance — checks the classic applicant mistakes in
 * priority order (no safety, top-heavy, no targets) before declaring it healthy.
 * @returns {{tone: 'good'|'warn'|'info', headline: string, detail: string}}
 */
export function balanceVerdict({ reach = 0, target = 0, safety = 0 } = {}) {
  const total = reach + target + safety;
  if (total === 0) {
    return { tone: 'info', headline: 'No colleges yet', detail: 'Add a few schools to see your reach/target/safety balance.' };
  }
  if (safety === 0) {
    return { tone: 'warn', headline: 'No safety schools', detail: 'Add at least one safety you’d genuinely be happy to attend.' };
  }
  if (reach > target + safety) {
    return { tone: 'warn', headline: 'Top-heavy list', detail: `${reach} reaches vs ${target + safety} target/safety — add a couple of targets or safeties.` };
  }
  if (target === 0) {
    return { tone: 'warn', headline: 'No target schools', detail: 'A strong list leans on targets — add a few where you’re a likely admit.' };
  }
  if (reach > 0 && target > 0 && safety > 0) {
    return { tone: 'good', headline: 'Nicely balanced', detail: 'You’ve got reaches, targets and safeties covered.' };
  }
  return { tone: 'info', headline: 'Building your list', detail: 'Aim for a spread of reaches, targets and safeties.' };
}
