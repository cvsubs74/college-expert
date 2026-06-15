/**
 * Decision Ledger helpers — turn recorded admission decisions + the fit category
 * Stratia predicted into an honest "predicted vs actual" read. Pure + tested.
 *
 * The admission OUTCOME (`decision`: accepted/waitlisted/denied/...) is kept
 * deliberately separate from the application PROCESS status
 * (planning/submitted/...) so the ledger grades real results, not progress.
 */

/** Canonical admission outcomes + display metadata. */
export const DECISION_META = {
  accepted: { label: 'Accepted', tone: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  enrolled: { label: 'Enrolled', tone: 'bg-emerald-100 text-emerald-800 border-emerald-300' },
  waitlisted: { label: 'Waitlisted', tone: 'bg-amber-50 text-amber-700 border-amber-200' },
  deferred: { label: 'Deferred', tone: 'bg-sky-50 text-sky-700 border-sky-200' },
  denied: { label: 'Denied', tone: 'bg-rose-50 text-rose-700 border-rose-200' },
};

/** Options for an in-app decision selector (value + label), incl. a clear/none. */
export const DECISION_OPTIONS = [
  { value: '', label: '— No decision —' },
  { value: 'accepted', label: 'Accepted' },
  { value: 'waitlisted', label: 'Waitlisted' },
  { value: 'deferred', label: 'Deferred' },
  { value: 'denied', label: 'Denied' },
  { value: 'enrolled', label: 'Enrolled' },
];

const DECISION_SYNONYMS = {
  admit: 'accepted', admitted: 'accepted', accept: 'accepted', in: 'accepted',
  waitlist: 'waitlisted', 'wait-listed': 'waitlisted', wl: 'waitlisted',
  deny: 'denied', reject: 'denied', rejected: 'denied',
  defer: 'deferred',
  committed: 'enrolled', attending: 'enrolled',
};

/** Map a raw decision string to a canonical key, or null if empty/unknown. */
export function normalizeDecision(value) {
  if (!value) return null;
  const k = String(value).trim().toLowerCase();
  if (DECISION_META[k]) return k;
  return DECISION_SYNONYMS[k] || null;
}

/** Display metadata for a decision (`{key, label, tone}`), or null. */
export function decisionMeta(value) {
  const k = normalizeDecision(value);
  return k ? { key: k, ...DECISION_META[k] } : null;
}

// Reach / Target / Safety family for a fit category (SUPER_REACH folds in).
const BAND_LABEL = { SUPER_REACH: 'Reach', REACH: 'Reach', TARGET: 'Target', SAFETY: 'Safety' };

/** The predicted band label ('Reach'|'Target'|'Safety') from a fit category, or null. */
export function predictedBand(predicted) {
  if (!predicted) return null;
  return BAND_LABEL[String(predicted).toUpperCase()] || null;
}

/**
 * Was a recorded decision "on-model" vs what Stratia predicted?
 *   - Safety/Target + accepted/enrolled → 'match' (called it)
 *   - Safety/Target + denied            → 'miss'  (the model was off)
 *   - Reach + denied                    → 'match' (a reach behaved like a reach)
 *   - Reach + accepted/enrolled         → 'beat'  (you beat the odds — happy, not scored as right/wrong)
 *   - waitlisted/deferred, or unknown band → 'neutral' (not graded)
 */
export function calibrationOutcome(predicted, decision) {
  const band = predictedBand(predicted);
  const d = normalizeDecision(decision);
  if (!band || !d || d === 'waitlisted' || d === 'deferred') return 'neutral';
  const gotIn = d === 'accepted' || d === 'enrolled';
  if (band === 'Reach') return gotIn ? 'beat' : 'match';
  return gotIn ? 'match' : 'miss';   // Target / Safety
}

/**
 * Summarize the ledger into counts + a friendly, non-overclaiming headline.
 * Returns `{ ready: false }` until at least `minDecided` decisions are recorded,
 * so a sample of one or two doesn't read as the model being random.
 */
export function calibrationSummary(outcomes, minDecided = 3) {
  const decided = (outcomes || []).filter((o) => normalizeDecision(o.decision));
  if (decided.length < minDecided) {
    return { decided: decided.length, ready: false, headline: null };
  }
  let match = 0, miss = 0, beat = 0, neutral = 0;
  for (const o of decided) {
    const r = calibrationOutcome(o.predicted, o.decision);
    if (r === 'match') match += 1;
    else if (r === 'miss') miss += 1;
    else if (r === 'beat') beat += 1;
    else neutral += 1;
  }
  const scored = match + miss;
  let headline;
  if (scored === 0) {
    headline = beat
      ? `${decided.length} decisions in — you beat the odds on ${beat}! More grades as targets & safeties resolve.`
      : `${decided.length} decisions in — too early to grade (waitlists & deferrals don’t count).`;
  } else {
    headline = `Stratia called ${match} of ${scored} right${beat ? ` · you beat the odds on ${beat}` : ''}.`;
  }
  return { decided: decided.length, ready: true, match, miss, beat, neutral, scored, headline };
}
