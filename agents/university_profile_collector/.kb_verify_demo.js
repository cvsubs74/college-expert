export const meta = {
  name: 'kb-collect-verify-demo',
  description: 'Reference self-verifying collector: collect high-stakes university fields from 2 independent source paths, cross-verify, gate on arithmetic, publish-or-null with provenance — no human review',
  phases: [
    { title: 'AnchorA', detail: 'authoritative path: College Scorecard + Common Data Set' },
    { title: 'CollectB', detail: 'independent path: official admissions / IR pages' },
    { title: 'Adjudicate', detail: 'referee resolves conflicts from canonical authority' },
    { title: 'Ledger', detail: 'assemble provenance + confidence; publish or null' },
  ],
}

const SCHOOL = (args && args.school) || 'University of Illinois Urbana-Champaign';

// The high-stakes DETERMINISTIC_OFFICIAL fields students rely on most.
const FIELDS = [
  { key: 'overall_acceptance_rate', desc: 'overall undergraduate admit rate, % (admits/applicants for the most recent completed cycle)', unit: '%' },
  { key: 'sat_composite_middle_50', desc: 'SAT total (EBRW+Math) middle-50% range of enrolled first-years, "low-high"', unit: 'range' },
  { key: 'act_composite_middle_50', desc: 'ACT composite middle-50% range of enrolled first-years, "low-high"', unit: 'range' },
  { key: 'freshman_retention_rate', desc: 'first-year-to-second-year full-time retention rate, %', unit: '%' },
  { key: 'graduation_rate_6_year', desc: 'six-year graduation rate, %', unit: '%' },
  { key: 'test_policy', desc: 'standardized-test policy for the upcoming cycle: Required / Optional / Free / Blind', unit: 'enum' },
];

const FIELD_OBS_SCHEMA = {
  type: 'object',
  required: ['observations'],
  properties: {
    observations: {
      type: 'array',
      items: {
        type: 'object',
        required: ['field', 'value', 'source_name', 'source_url', 'verbatim_quote', 'as_of_cycle', 'found'],
        properties: {
          field: { type: 'string' },
          found: { type: 'boolean', description: 'false if no authoritative value could be located — DO NOT GUESS' },
          value: { type: 'string', description: 'the value exactly as published, or "" if not found' },
          source_name: { type: 'string' },
          source_url: { type: 'string' },
          verbatim_quote: { type: 'string', description: 'the exact sentence/figure from the source that states this value' },
          as_of_cycle: { type: 'string', description: 'the admission/reporting year the figure belongs to, e.g. "Fall 2023" or "2023-24 CDS"' },
        },
      },
    },
  },
};

const ANTI_HALLUCINATION =
  'CRITICAL RULES: (1) Only report a value you can tie to a VERBATIM quote from a real fetched page. ' +
  '(2) If you cannot find an authoritative figure, set found=false and value="" — NEVER estimate, infer, or recall from memory. ' +
  '(3) Record the exact cycle/year of every figure. (4) A correct null is success; a confident guess is failure.';

// --------------------------------------------------------------------------
phase('AnchorA');
log(`Collecting ${SCHOOL} via PATH A (authoritative: College Scorecard + Common Data Set)...`);
const pathA = await agent(
  `You are collecting verified admissions facts for "${SCHOOL}" from AUTHORITATIVE STRUCTURED SOURCES ONLY.\n` +
  `Use these sources, in order: (1) U.S. Dept of Education College Scorecard (collegescorecard.ed.gov — search the school, open its page), ` +
  `(2) the school's own Common Data Set (web-search "${SCHOOL} Common Data Set" and fetch the most recent PDF/page — Section C1 for acceptance, C9 for SAT/ACT, Section B for retention/graduation).\n` +
  `Fetch the actual pages. For EACH field below, return the published value with a verbatim quote, the source, the URL, and the cycle year.\n\n` +
  `FIELDS:\n${FIELDS.map((f) => `- ${f.key}: ${f.desc}`).join('\n')}\n\n${ANTI_HALLUCINATION}`,
  { label: 'pathA:scorecard+CDS', phase: 'AnchorA', schema: FIELD_OBS_SCHEMA }
);

// --------------------------------------------------------------------------
phase('CollectB');
log(`Collecting ${SCHOOL} via PATH B (independent: official admissions / institutional-research pages)...`);
const pathB = await agent(
  `You are INDEPENDENTLY collecting the same admissions facts for "${SCHOOL}" from a DIFFERENT source path than College Scorecard/CDS.\n` +
  `Use: the school's OFFICIAL admissions / institutional-research / "class profile" / "first-year profile" pages (site:*.edu), and as a secondary cross-check a reputable aggregator (e.g. the school's US News or Niche stats page). Fetch the actual pages.\n` +
  `Do NOT use College Scorecard or the Common Data Set for this pass — we want an independent path to corroborate against.\n` +
  `For EACH field, return the published value with a verbatim quote, source, URL, and cycle year.\n\n` +
  `FIELDS:\n${FIELDS.map((f) => `- ${f.key}: ${f.desc}`).join('\n')}\n\n${ANTI_HALLUCINATION}`,
  { label: 'pathB:official+aggregator', phase: 'CollectB', schema: FIELD_OBS_SCHEMA }
);

// --------------------------------------------------------------------------
// DETERMINISTIC CROSS-VERIFY + CONSISTENCY GATE (plain code, no LLM)
function obsMap(res) {
  const m = {};
  for (const o of (res && res.observations) || []) m[o.field] = o;
  return m;
}
const A = obsMap(pathA), B = obsMap(pathB);

function numOf(s) {
  if (!s) return null;
  const m = String(s).match(/-?\d+(\.\d+)?/);
  return m ? parseFloat(m[0]) : null;
}
function rangeOf(s) {
  if (!s) return null;
  const nums = String(s).match(/\d+/g);
  if (!nums || nums.length < 2) return null;
  return [parseInt(nums[0]), parseInt(nums[1])];
}
function agree(field, a, b) {
  if (!a || !b || a.found === false || b.found === false) return null; // can't corroborate
  if (field === 'test_policy') {
    const norm = (x) => String(x).toLowerCase().replace(/[^a-z]/g, '');
    return norm(a.value).includes(norm(b.value).slice(0, 6)) || norm(b.value).includes(norm(a.value).slice(0, 6));
  }
  if (field.includes('middle_50')) {
    const ra = rangeOf(a.value), rb = rangeOf(b.value);
    if (!ra || !rb) return null;
    return Math.abs(ra[0] - rb[0]) <= 30 && Math.abs(ra[1] - rb[1]) <= 30; // SAT within 30, ACT within ~1
  }
  const na = numOf(a.value), nb = numOf(b.value);
  if (na == null || nb == null) return null;
  return Math.abs(na - nb) <= Math.max(1.5, 0.05 * na); // within 1.5pp or 5%
}

const ledger = FIELDS.map((f) => {
  const a = A[f.key], b = B[f.key];
  const ag = agree(f.key, a, b);
  let status, published, confidence, reason;
  const aFound = a && a.found !== false && a.value;
  const bFound = b && b.found !== false && b.value;
  if (aFound && bFound && ag === true) {
    status = 'CORROBORATED'; published = a.value; confidence = 'high';
    reason = 'two independent sources agree';
  } else if (aFound && bFound && ag === false) {
    status = 'CONFLICT'; published = null; confidence = 'none';
    reason = `sources disagree: A="${a.value}" (${a.source_name}) vs B="${b.value}" (${b.source_name})`;
  } else if (aFound && !bFound) {
    status = 'SINGLE_SOURCE_CANONICAL'; published = a.value; confidence = 'medium';
    reason = 'only the authoritative path (Scorecard/CDS) found it';
  } else if (!aFound && bFound) {
    status = 'SINGLE_SOURCE_SECONDARY'; published = null; confidence = 'low';
    reason = 'only the secondary path found it — needs canonical confirmation';
  } else {
    status = 'UNVERIFIED'; published = null; confidence = 'none';
    reason = 'no authoritative value located';
  }
  return { field: f.key, status, published, confidence, reason, pathA: a || null, pathB: b || null };
});

const conflicts = ledger.filter((l) => l.status === 'CONFLICT' || l.status === 'SINGLE_SOURCE_SECONDARY');
log(`Cross-verify: ${ledger.filter((l) => l.status === 'CORROBORATED').length} corroborated, ${conflicts.length} need adjudication.`);

// --------------------------------------------------------------------------
phase('Adjudicate');
const ADJ_SCHEMA = {
  type: 'object',
  required: ['field', 'resolved_value', 'decision', 'authority', 'authority_url', 'reason'],
  properties: {
    field: { type: 'string' },
    decision: { type: 'string', enum: ['RESOLVED', 'LEAVE_NULL'] },
    resolved_value: { type: 'string' },
    authority: { type: 'string' },
    authority_url: { type: 'string' },
    reason: { type: 'string' },
  },
};
const adjudicated = await parallel(conflicts.map((c) => () =>
  agent(
    `Referee an admissions-data conflict for "${SCHOOL}", field "${c.field}".\n` +
    `Path A (authoritative) said: ${JSON.stringify(c.pathA)}\nPath B (secondary) said: ${JSON.stringify(c.pathB)}\n\n` +
    `Go to the SINGLE most canonical authority for THIS field (the school's own Common Data Set for the relevant cycle, or College Scorecard) and fetch it. ` +
    `Decide the correct value, OR decide LEAVE_NULL if you cannot confirm one value with a verbatim quote. ` +
    `A wrong published value is unacceptable; leaving it null is fine. Watch for cycle mismatches (the two paths may just be different years — say so).`,
    { label: `adjudicate:${c.field}`, phase: 'Adjudicate', schema: ADJ_SCHEMA }
  )
)).then((r) => r.filter(Boolean));

for (const adj of adjudicated) {
  const row = ledger.find((l) => l.field === adj.field);
  if (!row) continue;
  if (adj.decision === 'RESOLVED') {
    row.status = 'ADJUDICATED'; row.published = adj.resolved_value; row.confidence = 'high';
    row.reason = `referee confirmed from ${adj.authority}: ${adj.reason}`;
    row.authority = adj.authority; row.authority_url = adj.authority_url;
  } else {
    row.status = 'LEFT_NULL'; row.published = null; row.confidence = 'none';
    row.reason = `referee left null: ${adj.reason}`;
  }
}

// --------------------------------------------------------------------------
phase('Ledger');
const publishable = ledger.filter((l) => l.published != null);
const nulled = ledger.filter((l) => l.published == null);
log(`FINAL: ${publishable.length}/${FIELDS.length} fields publishable with provenance; ${nulled.length} held null (never guessed).`);

return {
  school: SCHOOL,
  summary: {
    publishable: publishable.length,
    held_null: nulled.length,
    of_total: FIELDS.length,
  },
  field_ledger: ledger.map((l) => ({
    field: l.field,
    published_value: l.published,
    status: l.status,
    confidence: l.confidence,
    reason: l.reason,
    provenance: l.published != null ? {
      source: (l.authority) || (l.pathA && l.pathA.found !== false ? l.pathA.source_name : (l.pathB && l.pathB.source_name)),
      url: (l.authority_url) || (l.pathA && l.pathA.found !== false ? l.pathA.source_url : (l.pathB && l.pathB.source_url)),
      quote: (l.pathA && l.pathA.found !== false ? l.pathA.verbatim_quote : (l.pathB && l.pathB.verbatim_quote)),
      as_of: (l.pathA && l.pathA.as_of_cycle) || (l.pathB && l.pathB.as_of_cycle),
    } : null,
  })),
};
