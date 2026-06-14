/**
 * Helpers for the Research Notebook — artifacts saved from Claude (via the MCP
 * connector) or the app. Keeps kind metadata and provenance/staleness
 * formatting in one testable place; reuses the KB-vintage cycle helpers.
 */
import { cycleLabel, currentCycleYear } from './kbVintage';

/**
 * Per-kind display metadata. `tone` maps to Tailwind classes for the badge.
 * Unknown kinds fall back to `note`.
 */
export const RESEARCH_KINDS = {
  comparison: { label: 'Comparison', emoji: '⚖️', tone: 'bg-indigo-50 text-indigo-700 border-indigo-200' },
  timeline: { label: 'Timeline', emoji: '🗓️', tone: 'bg-sky-50 text-sky-700 border-sky-200' },
  essay_angle: { label: 'Essay angle', emoji: '✍️', tone: 'bg-rose-50 text-rose-700 border-rose-200' },
  scholarship: { label: 'Scholarship', emoji: '💰', tone: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  school_deep_dive: { label: 'Deep dive', emoji: '🔬', tone: 'bg-amber-50 text-amber-800 border-amber-200' },
  strategy: { label: 'Strategy', emoji: '🎯', tone: 'bg-purple-50 text-purple-700 border-purple-200' },
  note: { label: 'Note', emoji: '📝', tone: 'bg-gray-50 text-gray-600 border-gray-200' },
};

/** Metadata for a kind, always defined (defaults to `note`). */
export function kindMeta(kind) {
  return RESEARCH_KINDS[kind] || RESEARCH_KINDS.note;
}

/** Distinct kinds present in a list of notes, in a stable display order. */
export function kindsPresent(notes) {
  const order = Object.keys(RESEARCH_KINDS);
  const present = new Set((notes || []).map((n) => (RESEARCH_KINDS[n.kind] ? n.kind : 'note')));
  return order.filter((k) => present.has(k));
}

/** "Jun 14, 2026" or "" for a missing/invalid ISO date. */
export function formatDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
}

/**
 * Provenance + staleness for a note's footer:
 *   { sourceLabel, when, cycle, stale }
 * `cycle` is the data-cycle label (or null when no kb_year was recorded);
 * `stale` is true when that cycle is older than the current one (so the app can
 * flag "newer data available") — this is the notebook's version of the
 * fit-staleness signal.
 */
export function researchProvenance(note, now = new Date()) {
  const prov = (note && note.provenance) || {};
  const source = note?.source || prov.source;
  const sourceLabel = source === 'claude_mcp' ? 'From Claude' : 'Added in app';
  const when = formatDate(note?.created_at || prov.generated_at);
  const kbYear = prov.kb_year;
  const cycle = cycleLabel(kbYear);
  const stale = Boolean(cycle) && Number(kbYear) < currentCycleYear(now);
  return { sourceLabel, when, cycle, stale };
}
