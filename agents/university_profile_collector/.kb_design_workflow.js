export const meta = {
  name: 'kb-collector-redesign',
  description: 'Audit stored university profiles against live sources + design a self-verifying 100%-accurate collector',
  phases: [
    { title: 'ExternalAudit', detail: 'verify stored numbers against live authoritative sources' },
    { title: 'DesignPanel', detail: '4 independent architectures for a self-verifying collector' },
    { title: 'Judge', detail: 'score each architecture on accuracy-guarantee strength' },
    { title: 'Synthesize', detail: 'merge into one recommended architecture + accuracy strategy' },
  ],
}

const CONTEXT = `
PROJECT: "university_profile_collector" — an agent that builds a university knowledge base (one JSON profile per US university) for a college-admissions app. The profile schema has ~12 top-level sections covering: metadata, strategic_profile (rank, vibe), admissions_data (current acceptance rates, 5yr longitudinal trends, admitted-student GPA/SAT/ACT, demographics/race breakdown, waitlist), academic_structure (colleges + majors w/ impaction, weeder courses, internal-transfer GPA), application_process (deadlines, supplements, holistic factors), financials (COA, aid philosophy, scholarships), credit_policies (AP/IB/transfer), student_insights (crowdsourced), outcomes (median earnings, employers), student_retention (retention + grad rates).

FIELD CLASSES (critical distinction):
 - DETERMINISTIC_OFFICIAL: exists verbatim in IPEDS / U.S. Dept of Ed College Scorecard / the school's Common Data Set (CDS): acceptance rates, app/admit/enroll counts, SAT/ACT mid-50, GPA, race/ethnicity, retention, 4/6-yr grad rates, COA/tuition, yield, waitlist counts. These have a single correct value.
 - OFFICIAL_UNSTRUCTURED: on official .edu pages but as prose: deadlines, test policy, AP/IB credit rules, supplemental requirements, scholarships, impacted-major lists, internal-transfer GPA, curriculum.
 - SUBJECTIVE_CROWDSOURCED: opinion, not fact: campus vibe, student archetype, weeder courses, essay tips, red flags, analyst takeaways, gaming tactics.

CURRENT SYSTEM: Google ADK, Gemini-2.5-Flash everywhere. ParallelAgent fan-out of ~13 research sub-agents, most using google_search; a few hit College Scorecard + Urban-Institute IPEDS APIs but only ~40 schools are hardcoded in an IPEDS_LOOKUP dict (the other ~200 fall back to unreliable name search). A ProfileBuilder LLM aggregates everything to JSON. The only "validation" is JSON-syntax repair + a Pydantic shape check + TYPE COERCION that FABRICATES values (missing acceptance_rate -> 0.0, missing counts -> 0). There is NO factual verification, NO per-field provenance, NO cross-source corroboration, NO arithmetic invariants, NO confidence scoring.

FAILURE EVIDENCE (deterministic, LLM-free audit of 179 stored profiles): 92% record ZERO provenance; 17% self-contradict on the FEW fields where two values exist to cross-check (20 have fabricated zero app/admit counts; 13 have SAT composite != section-sum — a hallucination signature; several have yield != enrolled/admits). 17% is a FLOOR because most fields have null siblings and cannot be cross-checked at all.

HARD CONSTRAINT: Humans CANNOT review the output. The agent workflow must verify ITSELF before data is published. The bar is "never surface a wrong value." An explicit null or "unverified" flag is acceptable and good; a confident hallucination is a catastrophic failure. Coverage may be sacrificed for correctness.
`;

const AUDIT_SCHEMA = {
  type: 'object',
  required: ['school', 'checks', 'verdict_summary'],
  properties: {
    school: { type: 'string' },
    checks: {
      type: 'array',
      items: {
        type: 'object',
        required: ['field', 'stored_value', 'authoritative_value', 'verdict', 'source'],
        properties: {
          field: { type: 'string' },
          stored_value: { type: 'string' },
          authoritative_value: { type: 'string' },
          source: { type: 'string', description: 'e.g. College Scorecard, <school> Common Data Set 2023-24, official admissions page' },
          source_url: { type: 'string' },
          verdict: { type: 'string', enum: ['MATCH', 'CLOSE', 'MISMATCH', 'UNVERIFIABLE'] },
          note: { type: 'string' },
        },
      },
    },
    verdict_summary: { type: 'string' },
  },
};

const JUDGE_SCHEMA = {
  type: 'object',
  required: ['scores', 'overall', 'strongest_ideas', 'weaknesses'],
  properties: {
    scores: {
      type: 'object',
      required: ['accuracy_guarantee', 'self_verification', 'no_fabrication', 'feasibility', 'coverage_honesty'],
      properties: {
        accuracy_guarantee: { type: 'number', description: '0-10: how strongly does it prevent a wrong value reaching output' },
        self_verification: { type: 'number', description: '0-10: can it verify without a human' },
        no_fabrication: { type: 'number', description: '0-10: does it guarantee null-over-guess' },
        feasibility: { type: 'number', description: '0-10: buildable on the existing stack / as a Claude workflow' },
        coverage_honesty: { type: 'number', description: '0-10: honest about what it cannot verify' },
      },
    },
    overall: { type: 'number' },
    strongest_ideas: { type: 'array', items: { type: 'string' } },
    weaknesses: { type: 'array', items: { type: 'string' } },
  },
};

// ---------------------------------------------------------------------------
phase('ExternalAudit');
log('Verifying stored numbers against LIVE authoritative sources (College Scorecard + Common Data Set)...');

const AUDIT_TARGETS = [
  { school: 'University of Michigan-Ann Arbor', stored: 'overall_acceptance_rate=15.6%, SAT mid-50=1360-1530, ACT=31-35, 6yr grad=93.7%, test_policy=Test Optional' },
  { school: 'Boston University', stored: 'overall_acceptance_rate=11.1%, SAT mid-50=1400-1520, ACT=32-34, 6yr grad=89%, test_policy=Test Optional' },
  { school: 'University of Wisconsin-Madison', stored: 'overall_acceptance_rate=40.8%, SAT mid-50=1360-1510, ACT=28-33, 6yr grad=89.7%, test_policy=Test Optional' },
  { school: 'Purdue University', stored: 'overall_acceptance_rate=43.4%, SAT mid-50=1210-1470, ACT=26-33, 6yr grad=83%, test_policy=Test Required' },
  { school: 'University of California, San Diego', stored: 'overall_acceptance_rate=26.8% (a second stored copy says 28.41%), 6yr grad=87% (other copy 88%), test_policy=Test Blind' },
];

const auditResults = await parallel(AUDIT_TARGETS.map((t) => () =>
  agent(
    `You are a meticulous data auditor. Verify whether these STORED values for ${t.school} match authoritative reality.\n\nSTORED: ${t.stored}\n\n` +
    `For EACH numeric field, find the authoritative value. Use web search/fetch. Priority of sources: (1) the school's own Common Data Set (search "${t.school} Common Data Set" — sections C1 acceptance, C9 SAT/ACT/GPA, B retention/grad), (2) U.S. Dept of Education College Scorecard (collegescorecard.ed.gov), (3) official admissions/IR pages. Note the admission cycle/year of the authoritative figure. ` +
    `Mark MATCH (within rounding), CLOSE (off by a little / different cycle), MISMATCH (clearly wrong), or UNVERIFIABLE (could not find an authoritative figure). Quote the source and give the URL. Be skeptical and precise — do not rubber-stamp.`,
    { label: `audit:${t.school.slice(0, 18)}`, phase: 'ExternalAudit', schema: AUDIT_SCHEMA }
  )
)).then((r) => r.filter(Boolean));

const mismatchCount = auditResults.flatMap((r) => r.checks || []).filter((c) => c.verdict === 'MISMATCH').length;
const totalChecks = auditResults.flatMap((r) => r.checks || []).length;
log(`External audit done: ${mismatchCount}/${totalChecks} checked fields are clear MISMATCHES vs authoritative sources.`);

// ---------------------------------------------------------------------------
phase('DesignPanel');
log('Four independent architects designing a self-verifying collector, each from a distinct angle...');

const LENSES = [
  { key: 'provenance-ledger', angle:
    `ANGLE: Provenance-first. Every field in the output must carry {value, source_url, verbatim_quote, source_tier, confidence, as_of_cycle}. A value with no quote-backed source is forbidden — it becomes null. "Verification" = independent corroboration: a field is PUBLISHABLE only if ≥2 independent sources agree (or 1 source if it is the canonical authority, e.g. the school's own CDS for that field). Design the data model, the corroboration rules per field-class, and how the agent decides MATCH vs CONFLICT vs INSUFFICIENT.` },
  { key: 'deterministic-anchor', angle:
    `ANGLE: Deterministic-anchor-first. Treat structured public datasets (IPEDS via Urban Institute API, College Scorecard API, and the school's machine-readable CDS) as GROUND TRUTH for every DETERMINISTIC_OFFICIAL field — the LLM is NOT allowed to produce those numbers, it only fetches/parses them. The LLM is used only for OFFICIAL_UNSTRUCTURED and SUBJECTIVE_CROWDSOURCED fields. Specify: how to resolve the IPEDS UnitID for ANY of ~3000 schools (not a 40-school hardcoded dict), how to pull each deterministic field from the API, and the ARITHMETIC INVARIANTS that act as hard gates (admits/apps==rate; enrolled/admits==yield; SAT sections sum to composite; race sums ~100; 4yr<=6yr grad; waitlist admitted/accepted==wl_rate). Any record failing an invariant is rejected, never coerced.` },
  { key: 'adversarial-consensus', angle:
    `ANGLE: Adversarial multi-agent. Separate, independent roles: a COLLECTOR proposes a value+source; an independent VERIFIER tries to REFUTE it from a different source and re-derives it; a REFEREE adjudicates and assigns a confidence; a CONSISTENCY ENGINE checks cross-field arithmetic. A value is published only on consensus. Design the message contracts, the refutation protocol (verifier defaults to "reject if not independently confirmed"), the tie-break/escalation when collector and verifier disagree, and how this avoids the two failure modes: fabrication and false-rejection of true values.` },
  { key: 'claude-workflow-native', angle:
    `ANGLE: Express the ENTIRE thing as a Claude Workflow (the orchestration primitive: pipeline()/parallel()/agent(schema)/loop-until). Show the concrete phase graph: anchor → collect-per-section (fan-out) → adversarial-verify-per-field → consistency-gate → provenance-assemble → publish-or-null, with loop-until-corroborated for conflicts. Specify which steps are deterministic code vs agent() calls, the StructuredOutput schemas at each stage, and how "humans can't review" is satisfied by the workflow's own gates. Be concrete enough that it could be implemented.` },
];

const designs = await parallel(LENSES.map((l) => () =>
  agent(
    `${CONTEXT}\n\nYou are a principal architect. Design a BEST-IN-CLASS, self-verifying university-profile collector whose output never surfaces a wrong value, with NO human review.\n\n${l.angle}\n\n` +
    `Deliverables in your answer (markdown, concrete, ~600-900 words):\n` +
    `1. The core mechanism of YOUR angle and exactly how it prevents both (a) fabrication and (b) silent error.\n` +
    `2. How it handles the three field-classes differently.\n` +
    `3. The specific gates/checks that run with no human, and what happens to a field that fails them (null vs flag vs retry).\n` +
    `4. One concrete worked example for a single high-stakes field (e.g. overall acceptance rate, or SAT mid-50).\n` +
    `5. Honest limits: what your angle CANNOT guarantee, and the residual error it leaves.\n` +
    `Be rigorous and specific to THIS schema. Avoid generic "use better prompts" advice.`,
    { label: `design:${l.key}`, phase: 'DesignPanel' }
  )
)).then((r) => r.filter(Boolean));

// ---------------------------------------------------------------------------
phase('Judge');
const judged = await parallel(designs.map((d, i) => () =>
  agent(
    `Score this architecture proposal for a self-verifying university-data collector where HUMANS CANNOT REVIEW the output and the bar is "never surface a wrong value; null-over-guess".\n\nPROPOSAL (angle: ${LENSES[i].key}):\n${d}\n\nScore each dimension 0-10 and identify its strongest reusable ideas and its real weaknesses. Be critical.`,
    { label: `judge:${LENSES[i].key}`, phase: 'Judge', schema: JUDGE_SCHEMA }
  ).then((v) => ({ key: LENSES[i].key, design: d, verdict: v }))
)).then((r) => r.filter((x) => x && x.verdict));

const ranked = judged.sort((a, b) => (b.verdict.overall || 0) - (a.verdict.overall || 0));
log(`Judged. Ranking: ${ranked.map((r) => `${r.key}(${r.verdict.overall})`).join(' > ')}`);

// ---------------------------------------------------------------------------
phase('Synthesize');
const auditDigest = auditResults.map((r) =>
  `${r.school}: ${(r.checks || []).map((c) => `${c.field}[stored ${c.stored_value} vs auth ${c.authoritative_value} => ${c.verdict}]`).join('; ')} :: ${r.verdict_summary}`
).join('\n');

const bestIdeas = ranked.map((r) => `From ${r.key} (score ${r.verdict.overall}): ${(r.verdict.strongest_ideas || []).join('; ')}`).join('\n');

const synthesis = await agent(
  `${CONTEXT}\n\nYou are the chief architect writing the FINAL recommended design. You have:\n\n` +
  `=== LIVE EXTERNAL AUDIT (stored vs authoritative) ===\n${auditDigest}\n\n` +
  `=== BEST IDEAS FROM THE DESIGN PANEL (ranked) ===\n${bestIdeas}\n\n` +
  `=== FULL WINNING DESIGN (${ranked[0].key}) ===\n${ranked[0].design}\n\n` +
  `Write the single recommended architecture for a self-verifying, ~100%-accurate university-profile collector, merging the strongest ideas across all four angles. Structure it as:\n` +
  `A. The accuracy doctrine (the 4-5 non-negotiable principles, incl. null-over-guess and the field-class split).\n` +
  `B. The end-to-end pipeline (anchor -> collect -> adversarial-verify -> consistency-gate -> provenance-assemble -> publish/null), saying which stages are deterministic code vs LLM agents.\n` +
  `C. The per-field-class verification rules and the exact arithmetic invariants used as hard gates.\n` +
  `D. The provenance+confidence record every field must carry.\n` +
  `E. How to express it as a concrete Claude Workflow (phases, schemas, loop-until-corroborated) — answer "is a Claude workflow possible" decisively.\n` +
  `F. Honest residual-risk: where even this can still be wrong, and the monitoring to catch it.\n` +
  `Be concrete and specific to this schema and stack. ~1000-1400 words.`,
  { label: 'synthesis', phase: 'Synthesize' }
);

return {
  external_audit: auditResults,
  audit_mismatch_rate: `${mismatchCount}/${totalChecks}`,
  ranking: ranked.map((r) => ({ key: r.key, scores: r.verdict.scores, overall: r.verdict.overall })),
  recommended_architecture: synthesis,
};
