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
// Maps a note's `source` to a "From X" footer label. The MCP connector stamps
// the real calling client (#233); `claude_mcp`/`claude` are legacy values for
// notes saved before per-client attribution existed. Unknown clients fall back
// to the display name the connector stored in `provenance.model`, then to a
// neutral agent label — never to a specific vendor.
const SOURCE_LABELS = {
  app: 'Added in app',
  manual: 'Added in app',
  claude_mcp: 'From Claude',
  claude: 'From Claude',
  claude_code: 'From Claude Code',
  chatgpt: 'From ChatGPT',
  cursor: 'From Cursor',
  windsurf: 'From Windsurf',
  cline: 'From Cline',
  goose: 'From Goose',
  gemini: 'From Gemini',
  vscode: 'From VS Code',
};

export function researchSourceLabel(source, prov = {}) {
  if (!source || source === 'app' || source === 'manual') return 'Added in app';
  if (SOURCE_LABELS[source]) return SOURCE_LABELS[source];
  const display = (prov.model && String(prov.model).trim()) || 'an AI agent';
  return `From ${display}`;
}

export function researchProvenance(note, now = new Date()) {
  const prov = (note && note.provenance) || {};
  const source = note?.source || prov.source;
  const sourceLabel = researchSourceLabel(source, prov);
  const when = formatDate(note?.created_at || prov.generated_at);
  const kbYear = prov.kb_year;
  const cycle = cycleLabel(kbYear);
  const stale = Boolean(cycle) && Number(kbYear) < currentCycleYear(now);
  return { sourceLabel, when, cycle, stale };
}

// --- workflow (how the research was produced; powers "Repeat this workflow") ---

/** Ordered workflow steps for a note (each {tool, label}), or []. */
export function workflowSteps(note) {
  return (Array.isArray(note?.workflow) ? note.workflow : [])
    .map((s) => (typeof s === 'string' ? { tool: '', label: s } : s))
    .filter((s) => s && s.label);
}

/** True when a note carries enough to repeat it (an original ask or steps). */
export function hasWorkflow(note) {
  return Boolean((note?.source_prompt || '').trim()) || workflowSteps(note).length > 0;
}

/**
 * A ready-to-send prompt that reproduces the note's workflow in an AI agent.
 * Prefers the user's original ask; otherwise synthesizes one from the steps.
 */
export function repeatPrompt(note) {
  const original = (note?.source_prompt || '').trim();
  if (original) return original;
  const steps = workflowSteps(note).map((s) => s.label);
  const base = note?.title ? `Re-run my "${note.title}" Stratia workflow` : 'Re-run this Stratia workflow';
  return steps.length
    ? `${base}: ${steps.join('; ')}. Then save the updated result to my Stratia research notebook.`
    : `${base} and save the updated result to my Stratia research notebook.`;
}

/**
 * Stable identity for a note's workflow — the ordered tool sequence (prefers the
 * server-stored signature). Falls back to the ask/title so label-only workflows
 * still group. Two researches with the same signature came from the same
 * reusable "algorithm".
 */
export function workflowSignature(note) {
  if (note?.workflow_signature) return note.workflow_signature;
  const raw = Array.isArray(note?.workflow) ? note.workflow : [];
  const tools = raw.map((s) => (s && typeof s === 'object' ? s.tool : '')).filter(Boolean);
  if (tools.length) return tools.join('>');
  const ask = (note?.source_prompt || '').trim().toLowerCase();
  if (ask) return `p:${ask}`;
  const title = (note?.title || '').trim().toLowerCase();
  return title ? `t:${title}` : '';
}

/** A short human name for a workflow given its representative note. */
export function workflowName(note) {
  const ask = (note?.source_prompt || '').trim();
  if (ask) return ask.length > 80 ? `${ask.slice(0, 77)}…` : ask;
  const steps = workflowSteps(note).map((s) => s.label);
  if (steps.length) return steps.slice(0, 3).join(' → ') + (steps.length > 3 ? ' → …' : '');
  return note?.title || 'Workflow';
}

/**
 * Group researches by workflow into reusable "algorithms". Each group lists the
 * researches it produced (what) and the steps (how), newest-first, then by how
 * many times the workflow was run.
 * @returns {Array<{signature, name, steps, representative, researches}>}
 */
export function groupByWorkflow(notes) {
  const byId = (n) => n.created_at || '';
  const groups = new Map();
  for (const n of (notes || [])) {
    if (!hasWorkflow(n)) continue;
    const sig = workflowSignature(n);
    if (!sig) continue;
    if (!groups.has(sig)) groups.set(sig, []);
    groups.get(sig).push(n);
  }
  const out = [];
  for (const [signature, items] of groups) {
    items.sort((a, b) => (byId(b)).localeCompare(byId(a))); // newest first
    const representative = items[0];
    out.push({
      signature,
      name: workflowName(representative),
      steps: workflowSteps(representative),
      representative,
      researches: items,
    });
  }
  // Most-run first, then most-recent
  out.sort((a, b) => b.researches.length - a.researches.length
    || byId(b.representative).localeCompare(byId(a.representative)));
  return out;
}

// --- popular (cross-user) workflows: aggregate tool-sequence signatures --------

/** Friendly names for connector tool ids (Popular Workflows shows generic, PII-free steps). */
export const TOOL_LABELS = {
  search_universities: 'Search universities',
  get_university: 'Get university details',
  get_college_list: 'Get college list',
  get_fit_analysis: 'Get fit analysis',
  get_fit_history: 'Get fit history',
  get_deadlines: 'Get deadlines',
  get_profile: 'Get profile',
  get_roadmap: 'Get roadmap',
  get_essays: 'Get essays',
  get_aid_packages: 'Get aid packages',
  get_scholarships: 'Get scholarships',
  get_credits: 'Get credits',
  check_fit_recomputation: 'Check stale fits',
  add_college: 'Add a college',
  remove_college: 'Remove a college',
  recompute_fit: 'Recompute fit',
  update_profile_field: 'Update a profile field',
  update_student_profile: 'Build/update profile',
  save_research: 'Save research',
  research_to_tasks: 'Turn research into tasks',
};

/** A friendly label for a tool id (falls back to title-casing the id). */
export function toolLabel(tool) {
  if (TOOL_LABELS[tool]) return TOOL_LABELS[tool];
  return String(tool || '').split('_').filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}

/** Tool ids for a popular-workflow record (from `tools` or the signature). */
function popularTools(wf) {
  if (Array.isArray(wf?.tools) && wf.tools.length) return wf.tools;
  return String(wf?.signature || '').split('>').filter(Boolean);
}

/** Display name for a popular workflow: "<Kind>: step → step → …". */
export function popularWorkflowName(wf) {
  const kindLabel = kindMeta(wf?.kind).label;
  const steps = popularTools(wf).map(toolLabel);
  if (!steps.length) return kindLabel;
  return `${kindLabel}: ${steps.slice(0, 3).join(' → ')}${steps.length > 3 ? ' → …' : ''}`;
}

/** A generic, PII-free prompt that re-runs a popular workflow for the current user. */
export function popularWorkflowPrompt(wf) {
  const steps = popularTools(wf).map(toolLabel);
  const kindLabel = kindMeta(wf?.kind).label.toLowerCase();
  return steps.length
    ? `Run a Stratia ${kindLabel} workflow that does the following with my data: ${steps.join(', then ')}. Then save the result to my research notebook.`
    : `Run a Stratia ${kindLabel} workflow and save the result to my research notebook.`;
}

// --- trending + "new to you" for popular workflows (per-ISO-week buckets) -------

/**
 * ISO-week key 'YYYY-Www' for a Date — must match the backend's `_iso_week_key`
 * (Python isocalendar) so this-week / last-week buckets line up across the wire.
 */
export function isoWeekKey(date = new Date()) {
  const d = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()));
  const day = d.getUTCDay() || 7;             // Mon=1 … Sun=7 (ISO)
  d.setUTCDate(d.getUTCDate() + 4 - day);     // shift to the week's Thursday
  const isoYear = d.getUTCFullYear();
  const yearStart = new Date(Date.UTC(isoYear, 0, 1));
  const week = Math.ceil(((d - yearStart) / 86400000 + 1) / 7);
  return `${isoYear}-W${String(week).padStart(2, '0')}`;
}

/**
 * This-week vs last-week run counts for a popular workflow, plus a `trending`
 * flag. Trending requires enough all-time runs to be real (>=5) AND a clear
 * week-over-week jump (this week >=3 and >1.5x last week) so a tiny cohort or a
 * single new run can't light the flame.
 */
export function workflowTrend(wf, now = new Date()) {
  const weeks = (wf && wf.weeks && typeof wf.weeks === 'object') ? wf.weeks : {};
  const thisWeek = Number(weeks[isoWeekKey(now)] || 0);
  const lastWeek = Number(weeks[isoWeekKey(new Date(now.getTime() - 7 * 86400000))] || 0);
  const count = Number(wf?.count || 0);
  const trending = count >= 5 && thisWeek >= 3 && thisWeek > 1.5 * lastWeek;
  return { thisWeek, lastWeek, trending };
}

/**
 * True when a popular workflow's signature isn't one the current user has run
 * themselves — i.e. "new to you", worth discovering. `ownSignatures` is the set
 * of the user's own workflow signatures (from groupByWorkflow).
 */
export function isNewToUser(wf, ownSignatures) {
  const sig = wf?.signature;
  if (!sig) return false;
  const set = ownSignatures instanceof Set ? ownSignatures : new Set(ownSignatures || []);
  return !set.has(sig);
}
