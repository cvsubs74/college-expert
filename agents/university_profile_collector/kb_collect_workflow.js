/**
 * University Profile Collector — Claude Workflow (replaces the ADK agent).
 *
 * Input:  args = { university: string, year: number }   // year = entering-cohort Fall year (e.g. 2024)
 * Output: a UniversityProfile-shaped JSON (model.py schema) + _provenance + _trust_report,
 *         year-pinned, self-verified, publish-or-null. Ingestible via
 *         scripts/ingest_universities.py --file <out> --year <year>.
 *
 * Doctrine (see REDESIGN.md): null-over-guess · provenance-mandatory · field-class routing ·
 * deterministic code is writer-of-record · blind adversarial verify · arithmetic hard-gates.
 *
 * Stage map (code = pure JS gate, LLM = agent):
 *   1 Resolve   (LLM)  official name, IPEDS UnitID, location, authoritative source URLs for the cycle
 *   2 Anchor    (LLM)  ALL deterministic-official fields from the CDS(year)+Scorecard, w/ quote+cell+cycle
 *   3 Verify    (LLM)  blind re-derivation of the highest-stakes deterministic fields
 *   3' Gate      (code) corroborate A vs verifier + arithmetic invariants -> publish/null per field
 *   4 Sections  (LLM)  official-unstructured + subjective sections (deadlines, majors, aid, credit, insights)
 *   5 Assemble  (code) build UniversityProfile, inject verified deterministics, null the rest, trust report
 */

export const meta = {
  name: 'university-profile-collector',
  description: 'Collect a year-versioned, self-verified university profile from official sources (university+year) — replaces the ADK agent',
  phases: [
    { title: 'Resolve', detail: 'official identity + IPEDS UnitID + authoritative source URLs for the cycle' },
    { title: 'Anchor', detail: 'deterministic-official fields from CDS + College Scorecard, with provenance' },
    { title: 'Verify', detail: 'blind re-derivation of high-stakes fields + arithmetic gate' },
    { title: 'Sections', detail: 'deadlines, majors, financial aid, credit policies, student insights' },
    { title: 'Assemble', detail: 'build the UniversityProfile, publish-or-null, emit trust report' },
  ],
}

// --------------------------------------------------------------------------- inputs
// args may arrive as an object OR a JSON string — parse defensively so a stringified
// arg never silently falls back to the default school.
let INPUT = args;
if (typeof INPUT === 'string') { try { INPUT = JSON.parse(INPUT); } catch (e) { INPUT = {}; } }
INPUT = INPUT || {};
const UNIVERSITY = INPUT.university || 'University of Illinois Urbana-Champaign';
const YEAR = Number(INPUT.year) || 2026;                   // entering-cohort Fall year
// Stamped into metadata.collector_version. Bump when the collection contract changes.
// v2 = #287 major-strategy asks: per-major entry_path enum, second_choice_major_policy,
//      internal_transfer_policy, undeclared_option, verification_status stamping.
const COLLECTOR_VERSION = 'kb_collect_workflow/v2';
log(`INPUT → university="${UNIVERSITY}", year=${YEAR}${INPUT.university ? '' : ' (DEFAULT — no university in args!)'}`);
const CDS_EDITION = `${YEAR}-${YEAR + 1}`;                  // e.g. "2024-2025"
const CYCLE = `Fall ${YEAR}`;
const SLUG = UNIVERSITY.toLowerCase()
  .replace(/[,.'']/g, '').replace(/&/g, 'and')
  .replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');

const NO_GUESS =
  `ABSOLUTE RULES: (1) Report a value ONLY if you fetched a real page and can quote the exact text stating it. ` +
  `(2) If you cannot find/verify a value, set found=false and value="" — NEVER estimate, infer, average, or recall from memory. ` +
  `(3) Pin every figure to its cycle/year. The target cycle is ${CYCLE} (the ${CDS_EDITION} Common Data Set). ` +
  `If only a different cycle is available, report it and record the real as_of_cycle. A correct null is success; a confident guess is a catastrophic failure.`;

// --------------------------------------------------------------------------- schemas
const OBS_SCHEMA = (fieldEnum) => ({
  type: 'object', required: ['observations'],
  properties: {
    observations: {
      type: 'array',
      items: {
        type: 'object',
        required: ['field', 'found', 'value', 'source_name', 'source_url', 'verbatim_quote', 'as_of_cycle'],
        properties: {
          field: fieldEnum ? { type: 'string', enum: fieldEnum } : { type: 'string' },
          found: { type: 'boolean' },
          value: { type: 'string' },
          source_name: { type: 'string' },
          source_url: { type: 'string' },
          verbatim_quote: { type: 'string' },
          as_of_cycle: { type: 'string' },
          source_tier: { type: 'string', enum: ['canonical', 'official', 'aggregator', 'community', 'none'] },
        },
      },
    },
    sources_consulted: SRC_LIST,
  },
});

// every agent returns this: the full list of URLs it touched, for end-to-end transparency
const SRC_LIST = {
  type: 'array',
  description: 'EVERY URL searched or fetched while answering — used OR rejected',
  items: {
    type: 'object', required: ['url'],
    properties: {
      url: { type: 'string' },
      used: { type: 'boolean', description: 'true if it contributed to a value, false if consulted but not used' },
      note: { type: 'string', description: 'what was taken from it, or why it was skipped/rejected' },
    },
  },
};
const LOG_SOURCES = ' TRANSPARENCY REQUIREMENT: also return sources_consulted = EVERY URL you searched or fetched while answering this (used OR rejected), each with used:true/false and a one-line note on what you took from it or why you skipped it. Completeness is the point — this is the public record of how the data was assembled.';

// --------------------------------------------------------------------------- 1. RESOLVE
phase('Resolve');
log(`Resolving identity + authoritative sources for ${UNIVERSITY} (${CYCLE})...`);
const RESOLVE_SCHEMA = {
  type: 'object',
  required: ['official_name', 'id_slug', 'ipeds_unitid', 'city', 'state', 'institution_type', 'sources'],
  properties: {
    official_name: { type: 'string' },
    id_slug: { type: 'string', description: 'snake_case URL-safe id, e.g. university_of_illinois_urbana_champaign' },
    ipeds_unitid: { type: 'string', description: 'the IPEDS UnitID (6-digit) confirmed on name+city+state, or "" if not confirmed' },
    city: { type: 'string' }, state: { type: 'string' },
    institution_type: { type: 'string', enum: ['Public', 'Private', 'Unknown'] },
    sources: {
      type: 'object',
      required: ['common_data_set_url', 'scorecard_url'],
      properties: {
        common_data_set_url: { type: 'string', description: `direct URL to the ${CDS_EDITION} CDS PDF/xlsx (or the CDS index page if the exact year is not yet posted)` },
        common_data_set_cycle_found: { type: 'string', description: 'the actual CDS edition you located, e.g. "2024-2025" or "2023-2024 (latest available)"' },
        scorecard_url: { type: 'string' },
        official_admissions_url: { type: 'string' },
        financial_aid_url: { type: 'string' },
        majors_catalog_url: { type: 'string' },
      },
    },
    sources_consulted: SRC_LIST,
  },
};
const resolved = await agent(
  `Resolve canonical identity and the AUTHORITATIVE data sources for "${UNIVERSITY}" for the ${CYCLE} admissions cycle.\n` +
  `1) Confirm the official name, city, state, Public/Private, and the IPEDS UnitID — cross-check the UnitID on name+city+state via the NCES/IPEDS institution lookup or College Scorecard; if you cannot confirm it unambiguously, return "".\n` +
  `2) Locate, by fetching pages: the school's Common Data Set for ${CDS_EDITION} (the actual PDF/xlsx URL — search "${UNIVERSITY} Common Data Set ${CDS_EDITION}"; if that edition isn't posted yet, give the most recent and say which), its College Scorecard page, official admissions page, financial-aid page, and undergraduate majors/catalog page.\n${NO_GUESS}${LOG_SOURCES}`,
  { label: 'resolve', phase: 'Resolve', schema: RESOLVE_SCHEMA }
);
const ID = resolved.id_slug || SLUG;
log(`Resolved: ${resolved.official_name} · IPEDS ${resolved.ipeds_unitid || 'UNCONFIRMED'} · CDS ${resolved.sources.common_data_set_cycle_found || '?'}`);

// --------------------------------------------------------------------------- 2. ANCHOR (deterministic-official)
phase('Anchor');
const DET_FIELDS = [
  'overall_acceptance_rate', 'in_state_acceptance_rate', 'out_of_state_acceptance_rate',
  'transfer_acceptance_rate', 'international_acceptance_rate',
  'applications_total', 'admits_total', 'enrolled_total', 'yield_rate', 'admits_class_size',
  'sat_composite_middle_50', 'sat_reading_middle_50', 'sat_math_middle_50', 'act_composite_middle_50',
  'test_submission_rate', 'gpa_weighted_avg', 'gpa_unweighted_avg',
  'race_white', 'race_black', 'race_hispanic', 'race_asian', 'race_native_american',
  'race_pacific_islander', 'race_two_or_more', 'race_unknown', 'race_international',
  'first_gen_percentage', 'international_percentage',
  'freshman_retention_rate', 'graduation_rate_4_year', 'graduation_rate_6_year',
  'in_state_tuition', 'out_of_state_tuition', 'total_coa_in_state', 'total_coa_out_of_state',
  'median_earnings_10yr', 'is_test_optional', 'test_policy_details',
  'ed_applications', 'ed_admits', 'ed_acceptance_rate', 'ea_applications', 'ea_admits', 'ea_acceptance_rate',
  'waitlist_offered', 'waitlist_accepted', 'waitlist_admitted', 'waitlist_admit_rate',
];
log(`Anchoring ${DET_FIELDS.length} deterministic-official fields from the CDS + College Scorecard...`);
const anchor = await agent(
  `You are the deterministic ANCHOR. Pull these official statistics for "${resolved.official_name}" for ${CYCLE} from STRUCTURED AUTHORITIES ONLY: ` +
  `the school's Common Data Set ${CDS_EDITION} (${resolved.sources.common_data_set_url}) and the U.S. Dept of Education College Scorecard (${resolved.sources.scorecard_url}). Fetch them and read the actual tables/cells.\n` +
  `CDS map: C1=applications/admits/enrolled & acceptance; C2=waitlist; C8=test policy; C9=SAT/ACT percentiles & GPA & % submitting; B2=race/ethnicity; B22=retention; B=4/6-yr graduation; G=cost of attendance/tuition. median_earnings_10yr comes from College Scorecard ONLY.\n` +
  `Return one observation per field key below. For rates use a plain number string ("42.4"); for ranges use "low-high" ("1390-1520"); for counts a plain integer string; for is_test_optional "true"/"false". Cite the exact CDS cell/section or Scorecard field in the quote.\n\n` +
  `FIELD KEYS: ${DET_FIELDS.join(', ')}\n\n${NO_GUESS}${LOG_SOURCES}`,
  { label: 'anchor:cds+scorecard', phase: 'Anchor', schema: OBS_SCHEMA(DET_FIELDS) }
);

// index anchor observations
const aMap = {};
for (const o of anchor.observations || []) aMap[o.field] = o;

// --------------------------------------------------------------------------- 3. BLIND VERIFY (high-stakes)
phase('Verify');
const VERIFY_FIELDS = [
  { key: 'overall_acceptance_rate', what: 'overall undergraduate admit rate (%)' },
  { key: 'sat_composite_middle_50', what: 'SAT total middle-50% range of enrolled first-years' },
  { key: 'act_composite_middle_50', what: 'ACT composite middle-50% range of enrolled first-years' },
  { key: 'freshman_retention_rate', what: 'first-to-second-year retention (%)' },
  { key: 'graduation_rate_6_year', what: 'six-year graduation rate (%)' },
  { key: 'out_of_state_tuition', what: 'published out-of-state (or private) tuition for the cycle' },
];
const ONE_OBS = {
  type: 'object', required: ['found', 'value', 'source_name', 'source_url', 'verbatim_quote', 'as_of_cycle'],
  properties: {
    found: { type: 'boolean' }, value: { type: 'string' },
    source_name: { type: 'string' }, source_url: { type: 'string' },
    verbatim_quote: { type: 'string' }, as_of_cycle: { type: 'string' },
    sources_consulted: SRC_LIST,
  },
};
const verifications = await parallel(VERIFY_FIELDS.map((f) => () =>
  agent(
    `BLIND VERIFIER. Independently establish ONE value for "${resolved.official_name}", ${CYCLE}: the ${f.what}.\n` +
    `You are NOT told any prior value — find it yourself from the most canonical source (the school's ${CDS_EDITION} Common Data Set, or College Scorecard). Fetch the page, quote the exact figure, record the cycle. Your prior is to REJECT: if you cannot independently confirm a value with a verbatim quote, return found=false.\n${NO_GUESS}${LOG_SOURCES}`,
    { label: `verify:${f.key}`, phase: 'Verify', schema: ONE_OBS }
  ).then((v) => ({ key: f.key, v }))
)).then((r) => r.filter(Boolean));
const vMap = {}; for (const x of verifications) vMap[x.key] = x.v;

// --------------------------------------------------------------------------- 3'. DETERMINISTIC GATE (pure code)
function num(s) { if (s == null) return null; const m = String(s).match(/-?\d+(\.\d+)?/); return m ? parseFloat(m[0]) : null; }
// match an adjacent "low-high" pair (digits touching the hyphen) so verbose verifier text
// like "(25th-75th percentile) range: 30-34" yields [30,34], not [25,75].
function range(s) { if (!s) return null; const m = String(s).match(/(\d{2,4})\s*[-–—]\s*(\d{2,4})/); return m ? [parseInt(m[1]), parseInt(m[2])] : null; }
function found(o) { return o && o.found !== false && o.value !== '' && o.value != null; }
function agreeNum(a, b, tolAbs, tolFrac) { const x = num(a), y = num(b); if (x == null || y == null) return null; return Math.abs(x - y) <= Math.max(tolAbs, (tolFrac || 0) * x); }
function agreeRange(a, b, tol) { const x = range(a), y = range(b); if (!x || !y) return null; return Math.abs(x[0] - y[0]) <= tol && Math.abs(x[1] - y[1]) <= tol; }

const prov = {};        // field -> provenance record
const detVal = {};      // field -> published numeric/string value (or null)
const trust = { corroborated: 0, canonical_single: 0, conflict_nulled: 0, unverified_nulled: 0, fields: {} };

for (const key of DET_FIELDS) {
  const a = aMap[key];
  const ver = vMap[key]; // only present for VERIFY_FIELDS
  let status, value = null, confidence = 'none';
  const isRange = key.includes('middle_50');
  const isBoolOrText = key === 'is_test_optional' || key === 'test_policy_details';

  if (ver !== undefined) {
    const ag = isRange ? agreeRange(a && a.value, ver.value, key.startsWith('act') ? 1 : 30)
      : agreeNum(a && a.value, ver.value, key.includes('tuition') ? 800 : 1.5, 0.05);
    if (found(a) && found(ver) && ag === true) { status = 'CORROBORATED'; value = a.value; confidence = 'high'; trust.corroborated++; }
    else if (found(a) && found(ver) && ag === false) { status = 'CONFLICT'; value = null; trust.conflict_nulled++; }
    else if (found(a) && !found(ver)) { status = 'CANONICAL_SINGLE'; value = a.value; confidence = 'medium'; trust.canonical_single++; }
    else if (!found(a) && found(ver)) { status = 'CANONICAL_SINGLE'; value = ver.value; confidence = 'medium'; trust.canonical_single++; }
    else { status = 'UNVERIFIED'; value = null; trust.unverified_nulled++; }
  } else {
    if (found(a)) { status = (a.source_tier === 'aggregator') ? 'AGGREGATOR_ONLY' : 'CANONICAL_SINGLE'; value = (status === 'AGGREGATOR_ONLY') ? null : a.value; confidence = (status === 'AGGREGATOR_ONLY') ? 'none' : 'medium'; if (value != null) trust.canonical_single++; else trust.unverified_nulled++; }
    else { status = 'UNVERIFIED'; value = null; trust.unverified_nulled++; }
  }

  const src = (status === 'CONFLICT') ? null : (found(a) ? a : (ver && found(ver) ? ver : null));
  detVal[key] = isBoolOrText ? (value === null ? null : value) : (value === null ? null : (isRange ? value : num(value)));
  prov[key] = {
    status, confidence,
    value: detVal[key],
    source: src ? src.source_name : null,
    url: src ? src.source_url : null,
    quote: src ? src.verbatim_quote : null,
    as_of_cycle: src ? src.as_of_cycle : null,
    conflict: status === 'CONFLICT' ? { anchor: a && a.value, verifier: ver && ver.value } : undefined,
  };
  trust.fields[key] = status;
}

// arithmetic invariants — demote violators to null (never coerce)
function demote(key, why) { if (detVal[key] != null) { detVal[key] = null; prov[key].status = 'INVARIANT_FAIL'; prov[key].value = null; prov[key].reason = why; trust.fields[key] = 'INVARIANT_FAIL'; trust.conflict_nulled++; if (trust.canonical_single > 0) trust.canonical_single--; } }
const apps = num(detVal.applications_total), adm = num(detVal.admits_total), enr = num(detVal.enrolled_total);
const accept = num(detVal.overall_acceptance_rate), yld = num(detVal.yield_rate);
if (apps && adm && accept != null && Math.abs(adm / apps * 100 - accept) > Math.max(2, 0.15 * accept)) { demote('overall_acceptance_rate', 'admits/apps disagrees with stated rate'); }
if (adm && enr && yld != null && Math.abs(enr / adm * 100 - yld) > Math.max(3, 0.2 * yld)) { demote('yield_rate', 'enrolled/admits disagrees with stated yield'); }
const cr = range(detVal.sat_reading_middle_50 && detVal.sat_reading_middle_50.join ? detVal.sat_reading_middle_50.join('-') : null);
const mr = range(detVal.sat_math_middle_50 && detVal.sat_math_middle_50.join ? detVal.sat_math_middle_50.join('-') : null);
const comp = detVal.sat_composite_middle_50;
if (cr && mr && comp && (Math.abs(cr[0] + mr[0] - comp[0]) > 40 || Math.abs(cr[1] + mr[1] - comp[1]) > 40)) { demote('sat_composite_middle_50', 'composite != section sum'); }
const g4 = num(detVal.graduation_rate_4_year), g6 = num(detVal.graduation_rate_6_year);
if (g4 != null && g6 != null && g4 > g6 + 1) { demote('graduation_rate_4_year', '4yr grad > 6yr grad'); }
const races = ['race_white', 'race_black', 'race_hispanic', 'race_asian', 'race_native_american', 'race_pacific_islander', 'race_two_or_more', 'race_unknown', 'race_international'].map((k) => num(detVal[k])).filter((x) => x != null);
if (races.length >= 5) { const s = races.reduce((a, b) => a + b, 0); if (s < 80 || s > 120) { for (const k of ['race_white', 'race_black', 'race_hispanic', 'race_asian', 'race_native_american', 'race_pacific_islander', 'race_two_or_more', 'race_unknown', 'race_international']) demote(k, `race sum=${s.toFixed(0)}%`); } }
// never publish a 0 / out-of-range acceptance rate (the legacy bug)
if (detVal.overall_acceptance_rate != null && !(detVal.overall_acceptance_rate > 0 && detVal.overall_acceptance_rate <= 100)) demote('overall_acceptance_rate', 'out of (0,100]');

log(`Gate: ${trust.corroborated} corroborated, ${trust.canonical_single} canonical-single, ${trust.conflict_nulled} nulled (conflict/invariant), ${trust.unverified_nulled} unverified.`);

// --------------------------------------------------------------------------- 4. SECTIONS (official-unstructured + subjective)
phase('Sections');
const SECTION_SCHEMA = {
  type: 'object', required: ['data', 'sources_consulted'],
  properties: {
    data: { type: 'object', additionalProperties: true, description: 'the section JSON in the requested shape' },
    sources_consulted: SRC_LIST,
    notes: { type: 'string' },
  },
};
const SECTIONS = [
  { key: 'strategic_profile', tier: 'mixed', prompt:
    `Build strategic_profile for ${resolved.official_name}: {executive_summary (2-3 sentences), market_position, admissions_philosophy, us_news_rank (integer or null — only from a US News page you fetch), analyst_takeaways:[{category,insight,implication}] (3-5), campus_dynamics:{social_environment,transportation_impact,research_impact}}. us_news_rank is a FACT: null unless quoted. The rest are sourced opinion — attribute and keep concise.` },
  { key: 'academic_structure', tier: 'official', prompt:
    `Build academic_structure for ${resolved.official_name} from the official catalog (${resolved.sources.majors_catalog_url}) and the school's official admissions/advising/change-of-major pages:\n` +
    `{structure_type,\n` +
    ` colleges:[{name, admissions_model, is_restricted_or_capped (bool), strategic_fit_advice, housing_profile, student_archetype,\n` +
    `   internal_transfer_policy: {allowed (bool or null), competitive (bool or null), gpa_floor (number or null), application_required (bool or null), quote, source_url} or null — this college's OFFICIAL policy for already-enrolled students switching in from elsewhere at the university. The quote must carry the nuance a bare number loses (e.g. "a 3.5 GPA is the minimum to apply, not a guarantee of admission" → gpa_floor 3.5 AND competitive true). Each non-null flag must be directly supported by the quoted official text; anything the page does not state → null.\n` +
    `   second_choice_major_policy: {allowed (bool or null), constraints:[strings], quote, source_url} or null — ONLY when this college's second-choice-major rules differ from the university-wide policy below; otherwise omit/null.\n` +
    `   majors:[{name, degree_type, is_impacted (bool, ONLY if the school officially designates it capped/impacted — else false),\n` +
    `     admissions_pathway (the school's OWN wording for how a freshman enters this major — quote it as close to verbatim as possible),\n` +
    `     entry_path ("direct_admit" | "pre_major" | "secondary_application" | "open_declaration" or null — set ONLY when the official text you quoted in admissions_pathway clearly supports exactly ONE of these; ambiguous, mixed, or unstated → null. A downstream classifier handles raw text; a wrong enum here is worse than a null),\n` +
    `     direct_admit_only (bool), internal_transfer_gpa (number or null), prerequisite_courses:[]}]}],\n` +
    ` minors_certificates:[],\n` +
    ` second_choice_major_policy: {allowed (bool or null), constraints:[strings — e.g. "CS+X blended degrees are unavailable as a second choice"], quote, source_url} or null — the UNIVERSITY-WIDE policy on listing a second-choice major on the freshman application,\n` +
    ` undeclared_option: {exists (bool or null), division_name (string or null — e.g. "Division of General Studies"), restrictions (string or null), quote, source_url} or null — the official undeclared/exploratory entry path for freshmen}.\n` +
    `List the real colleges and 8-15 real majors each from the catalog. Every policy object above is null-over-guess: a verbatim quote + official (.edu) source_url is REQUIRED for any non-null flag, else null the whole object. Do NOT invent weeder courses or GPA cutoffs — null/omit unless officially stated.` },
  { key: 'application_process', tier: 'official', prompt:
    `Build application_process for ${resolved.official_name} for the ${CYCLE} cycle from the official admissions site (${resolved.sources.official_admissions_url}): {platforms:[], application_deadlines:[{plan_type, date "YYYY-MM-DD", is_binding (bool), notes}] (dates MUST fall in the ${YEAR}..${YEAR + 1} window — quote them), supplemental_requirements:[{target_program, requirement_type, details}], holistic_factors:{primary_factors:[], secondary_factors:[], essay_importance, demonstrated_interest, interview_policy, legacy_consideration, first_gen_boost}}. Holistic factors come from the CDS C7 if available. Null anything not stated officially.` },
  { key: 'financials', tier: 'official', prompt:
    `Build financials for ${resolved.official_name} for ${CDS_EDITION} from the official financial-aid/bursar pages (${resolved.sources.financial_aid_url}): {tuition_model, aid_philosophy, average_need_based_aid (number or null), average_merit_aid (number or null), percent_receiving_aid (number or null), scholarships:[{name, type, amount, benefits, application_method, deadline}]}. Tuition/COA numbers themselves come from the anchor — do NOT restate them here; focus on aid philosophy + named scholarships (3-7 real ones). Quote sources; null unknowns.` },
  { key: 'credit_policies', tier: 'official', prompt:
    `Build credit_policies for ${resolved.official_name} from official AP/IB/transfer-credit pages: {philosophy, ap_policy:{general_rule, exceptions:[], usage}, ib_policy:{general_rule, diploma_bonus (bool)}, transfer_articulation:{tools:[], restrictions}}. Quote the official policy text. Null anything not found on an official page.` },
  { key: 'student_insights', tier: 'community', prompt:
    `Build student_insights for ${resolved.official_name} synthesized from MULTIPLE community sources (Reddit, Niche, College Confidential): {what_it_takes:[3-5], common_activities:[5-10], essay_tips:[3-5], red_flags:[2-3], insights:[{source,category,insight}]}. This is explicitly crowdsourced OPINION — only include points mentioned by multiple sources; attribute. Never present as fact.` },
  { key: 'application_strategy', tier: 'community', prompt:
    `Build application_strategy for ${resolved.official_name}: {major_selection_tactics:[3-5], college_ranking_tactics:[] (only for residential-college systems), alternate_major_strategy}. Sourced community tactics tied to THIS school's actual admissions structure. Empty arrays if not applicable — do not invent.` },
  { key: 'outcomes_extra', tier: 'official', prompt:
    `Build the non-earnings parts of outcomes for ${resolved.official_name}: {employment_rate_2yr (number or null), grad_school_rate (number or null), top_employers:[5-7 from the career-center outcomes report or LinkedIn alumni], loan_default_rate (number or null)}. median_earnings comes from the anchor. Quote the career-outcomes source; null unknowns.` },
];
const sectionResults = await parallel(SECTIONS.map((s) => () =>
  agent(`${s.prompt}\n\nReturn {data:<the section JSON>, notes}. ${NO_GUESS}${LOG_SOURCES}`,
    { label: `section:${s.key}`, phase: 'Sections', schema: SECTION_SCHEMA })
    .then((r) => ({ key: s.key, ...r }))
)).then((r) => r.filter(Boolean));
const sec = {}; for (const s of sectionResults) sec[s.key] = s;

// --------------------------------------------------------------------------- 5. ASSEMBLE (pure code, null-over-guess)
phase('Assemble');
const pub = (k) => (detVal[k] === undefined ? null : detVal[k]);
const rangeStr = (k) => Array.isArray(detVal[k]) ? detVal[k].join('-') : (detVal[k] || null);
// section agents sometimes wrap a scalar in a provenance object {value, source, quote, ...};
// strip those wrappers recursively so the section data is plain scalars/arrays the schema expects.
function unwrap(x) {
  if (Array.isArray(x)) return x.map(unwrap);
  if (x && typeof x === 'object') {
    if ('value' in x && ('source' in x || 'source_url' in x || 'found' in x || 'quote' in x || 'as_of_cycle' in x))
      return unwrap(x.value);
    const o = {}; for (const k of Object.keys(x)) o[k] = unwrap(x[k]); return o;
  }
  return x;
}
const D = (k) => unwrap(sec[k] && sec[k].data ? sec[k].data : {});
// defensive shape coercion: section agents sometimes return richer objects than the
// schema's List[str] fields — flatten to strings so the profile stays model.py-valid (null-over-guess).
const toStr = (x) => typeof x === 'string' ? x
  : (x && (x.tactic || x.value || x.insight || x.text || x.detail)) ? String(x.tactic || x.value || x.insight || x.text)
  : (x == null ? null : JSON.stringify(x));
const toStrArr = (a) => Array.isArray(a) ? a.map(toStr).filter(Boolean) : [];
const numN = (x) => { if (x == null || x === '') return null; const n = Number(String(x).replace(/[^0-9.\-]/g, '')); return Number.isFinite(n) ? n : null; };
const boolN = (x) => x === true || x === 1 || x === 'true' || x === 'Yes' || x === 'yes';
const AS = D('application_strategy');
const SI = D('student_insights');
const OX = D('outcomes_extra');
const CP = D('credit_policies');
const FIN = D('financials');

const earlyStats = [];
if (pub('ed_applications') != null || pub('ed_acceptance_rate') != null)
  earlyStats.push({ plan_type: 'ED', applications: pub('ed_applications'), admits: pub('ed_admits'), acceptance_rate: pub('ed_acceptance_rate') });
if (pub('ea_applications') != null || pub('ea_acceptance_rate') != null)
  earlyStats.push({ plan_type: 'EA', applications: pub('ea_applications'), admits: pub('ea_admits'), acceptance_rate: pub('ea_acceptance_rate') });

const waitlist = (pub('waitlist_offered') != null || pub('waitlist_admitted') != null) ? {
  year: YEAR, offered_spots: pub('waitlist_offered'), accepted_spots: pub('waitlist_accepted'),
  admitted_from_waitlist: pub('waitlist_admitted'), waitlist_admit_rate: pub('waitlist_admit_rate'),
  is_waitlist_ranked: null,
} : null;

const profile = {
  _id: ID,
  metadata: {
    official_name: resolved.official_name,
    location: { city: resolved.city, state: resolved.state, type: resolved.institution_type },
    last_updated: `${YEAR}-CYCLE`,            // stamped by ingest; cycle-pinned
    cycle_year: YEAR,
    // The badge switch: major_facts.py (knowledge_base_manager_universities_v2) flips
    // per-major basis labels kb_reported → kb_verified when this reads 'verified'.
    verification_status: 'verified',
    collector_version: COLLECTOR_VERSION,
    report_source_files: [resolved.sources.common_data_set_url, resolved.sources.scorecard_url].filter(Boolean),
  },
  strategic_profile: {
    executive_summary: D('strategic_profile').executive_summary || '',
    market_position: D('strategic_profile').market_position || '',
    admissions_philosophy: D('strategic_profile').admissions_philosophy || '',
    us_news_rank: D('strategic_profile').us_news_rank ?? null,
    analyst_takeaways: D('strategic_profile').analyst_takeaways || [],
    campus_dynamics: D('strategic_profile').campus_dynamics || null,
  },
  admissions_data: {
    current_status: {
      overall_acceptance_rate: pub('overall_acceptance_rate'),
      in_state_acceptance_rate: pub('in_state_acceptance_rate'),
      out_of_state_acceptance_rate: pub('out_of_state_acceptance_rate'),
      international_acceptance_rate: pub('international_acceptance_rate'),
      transfer_acceptance_rate: pub('transfer_acceptance_rate'),
      admits_class_size: pub('admits_class_size'),
      is_test_optional: detVal.is_test_optional === 'true' ? true : (detVal.is_test_optional === 'false' ? false : null),
      test_policy_details: pub('test_policy_details'),
      early_admission_stats: earlyStats,
    },
    longitudinal_trends: [{
      year: YEAR, cycle_name: `Class entering ${CYCLE}`,
      applications_total: pub('applications_total'), admits_total: pub('admits_total'),
      enrolled_total: pub('enrolled_total'), acceptance_rate_overall: pub('overall_acceptance_rate'),
      yield_rate: pub('yield_rate'), waitlist_stats: waitlist, notes: '',
    }],
    admitted_student_profile: {
      gpa: { weighted_middle_50: null, unweighted_middle_50: null, average_weighted: pub('gpa_weighted_avg'), notes: '' },
      testing: {
        sat_composite_middle_50: rangeStr('sat_composite_middle_50'),
        sat_reading_middle_50: rangeStr('sat_reading_middle_50'),
        sat_math_middle_50: rangeStr('sat_math_middle_50'),
        act_composite_middle_50: rangeStr('act_composite_middle_50'),
        submission_rate: pub('test_submission_rate'), policy_note: '',
      },
      demographics: {
        first_gen_percentage: pub('first_gen_percentage'),
        international_percentage: pub('international_percentage'),
        geographic_breakdown: [], gender_breakdown: null,
        racial_breakdown: {
          white: pub('race_white'), black_african_american: pub('race_black'),
          hispanic_latino: pub('race_hispanic'), asian: pub('race_asian'),
          native_american_alaskan: pub('race_native_american'), pacific_islander: pub('race_pacific_islander'),
          two_or_more_races: pub('race_two_or_more'), unknown: pub('race_unknown'),
          non_resident_alien: pub('race_international'),
        },
        religious_affiliation: null,
      },
    },
  },
  academic_structure: (() => {
    const AC = D('academic_structure');
    // second_choice_major_policy / undeclared_option (university level) and the per-college
    // internal_transfer_policy / second_choice_major_policy objects flow through the spread —
    // their {.., quote, source_url} shape has no 'value' key, so unwrap() leaves them intact.
    if (!AC || !Array.isArray(AC.colleges) || !AC.colleges.length) return { structure_type: 'Colleges', colleges: [], minors_certificates: [], second_choice_major_policy: null, undeclared_option: null };
    return { ...AC, structure_type: toStr(AC.structure_type) || 'Colleges', minors_certificates: toStrArr(AC.minors_certificates), second_choice_major_policy: AC.second_choice_major_policy || null, undeclared_option: AC.undeclared_option || null };
  })(),
  application_process: (() => {
    const AP = D('application_process');
    if (!AP || !AP.application_deadlines) return null;
    const hf = AP.holistic_factors || {};
    return {
      platforms: toStrArr(AP.platforms),
      application_deadlines: Array.isArray(AP.application_deadlines) ? AP.application_deadlines.map((d) => ({
        plan_type: toStr(d.plan_type) || '', date: d.date ? toStr(d.date) : null, is_binding: !!d.is_binding, notes: toStr(d.notes) || '',
      })) : [],
      supplemental_requirements: Array.isArray(AP.supplemental_requirements) ? AP.supplemental_requirements.map((s) => ({
        target_program: toStr(s.target_program) || 'General', requirement_type: toStr(s.requirement_type) || '', deadline: toStr(s.deadline) || '', details: toStr(s.details) || '',
      })) : [],
      holistic_factors: {
        primary_factors: toStrArr(hf.primary_factors), secondary_factors: toStrArr(hf.secondary_factors),
        essay_importance: toStr(hf.essay_importance) || 'High', demonstrated_interest: toStr(hf.demonstrated_interest) || 'Not Considered',
        interview_policy: toStr(hf.interview_policy) || 'Not Offered', legacy_consideration: toStr(hf.legacy_consideration) || 'Unknown',
        first_gen_boost: toStr(hf.first_gen_boost) || 'Unknown', specific_differentiators: toStr(hf.specific_differentiators) || '',
      },
    };
  })(),
  application_strategy: {
    major_selection_tactics: toStrArr(AS.major_selection_tactics),
    college_ranking_tactics: toStrArr(AS.college_ranking_tactics),
    alternate_major_strategy: typeof AS.alternate_major_strategy === 'string' ? AS.alternate_major_strategy : (toStr(AS.alternate_major_strategy) || ''),
  },
  financials: {
    tuition_model: toStr(FIN.tuition_model) || '',
    cost_of_attendance_breakdown: {
      academic_year: CDS_EDITION,
      in_state: { tuition: pub('in_state_tuition'), total_coa: pub('total_coa_in_state'), housing: null },
      out_of_state: { tuition: pub('out_of_state_tuition'), total_coa: pub('total_coa_out_of_state'), supplemental_tuition: null },
    },
    aid_philosophy: toStr(FIN.aid_philosophy) || '',
    average_need_based_aid: numN(FIN.average_need_based_aid),
    average_merit_aid: numN(FIN.average_merit_aid),
    percent_receiving_aid: numN(FIN.percent_receiving_aid),
    scholarships: (Array.isArray(FIN.scholarships) ? FIN.scholarships : []).map((s) => ({
      name: toStr(s.name) || 'Unnamed Scholarship', type: toStr(s.type) || 'General', amount: toStr(s.amount) || '',
      deadline: toStr(s.deadline) || '', deadline_date: s.deadline_date == null ? null : toStr(s.deadline_date),
      benefits: toStr(s.benefits) || '', application_method: toStr(s.application_method) || '',
    })),
  },
  credit_policies: {
    philosophy: toStr(CP.philosophy) || '',
    ap_policy: { general_rule: toStr((CP.ap_policy || {}).general_rule) || '', exceptions: toStrArr((CP.ap_policy || {}).exceptions), usage: toStr((CP.ap_policy || {}).usage) || '' },
    ib_policy: { general_rule: toStr((CP.ib_policy || {}).general_rule) || '', diploma_bonus: boolN((CP.ib_policy || {}).diploma_bonus) },
    transfer_articulation: { tools: toStrArr((CP.transfer_articulation || {}).tools), restrictions: toStr((CP.transfer_articulation || {}).restrictions) || '' },
  },
  student_insights: {
    what_it_takes: toStrArr(SI.what_it_takes), common_activities: toStrArr(SI.common_activities),
    essay_tips: toStrArr(SI.essay_tips), red_flags: toStrArr(SI.red_flags),
    insights: Array.isArray(SI.insights) ? SI.insights : [],
  },
  outcomes: {
    median_earnings_10yr: pub('median_earnings_10yr'),
    employment_rate_2yr: numN(OX.employment_rate_2yr),
    grad_school_rate: numN(OX.grad_school_rate),
    top_employers: toStrArr(OX.top_employers),
    loan_default_rate: numN(OX.loan_default_rate),
  },
  student_retention: {
    freshman_retention_rate: pub('freshman_retention_rate'),
    graduation_rate_4_year: pub('graduation_rate_4_year'),
    graduation_rate_6_year: pub('graduation_rate_6_year'),
  },
};

// ---------- COMPLETE SOURCE LEDGER: every URL consulted across every stage ----------
const ledger = new Map(); // url -> { url, roles:Set, notes:[], consulted_only:bool, backed_published_fields:[] }
function addSrc(url, role, note, used) {
  if (!url || typeof url !== 'string') return;
  const u = url.trim();
  if (!/^https?:\/\//i.test(u)) return;
  if (!ledger.has(u)) ledger.set(u, { url: u, roles: new Set(), notes: [], used: false, backed_published_fields: [] });
  const e = ledger.get(u);
  e.roles.add(role);
  if (note && e.notes.length < 6 && !e.notes.includes(note)) e.notes.push(note);
  if (used) e.used = true;
}
// resolve stage
if (resolved.sources) {
  addSrc(resolved.sources.common_data_set_url, 'resolve:common_data_set', `CDS located (${resolved.sources.common_data_set_cycle_found || '?'})`, true);
  addSrc(resolved.sources.scorecard_url, 'resolve:scorecard', 'College Scorecard located', true);
  addSrc(resolved.sources.official_admissions_url, 'resolve:admissions', 'official admissions page', false);
  addSrc(resolved.sources.financial_aid_url, 'resolve:financial_aid', 'financial-aid page', false);
  addSrc(resolved.sources.majors_catalog_url, 'resolve:catalog', 'majors/catalog page', false);
}
(resolved.sources_consulted || []).forEach((s) => addSrc(s.url, 'resolve', s.note, s.used));
// anchor stage (both the full consulted list and every per-field source)
(anchor.sources_consulted || []).forEach((s) => addSrc(s.url, 'anchor', s.note, s.used));
(anchor.observations || []).forEach((o) => { if (o.source_url) addSrc(o.source_url, `anchor:${o.field}`, o.verbatim_quote, o.found !== false); });
// blind-verify stage
verifications.forEach((x) => {
  (x.v.sources_consulted || []).forEach((s) => addSrc(s.url, `verify:${x.key}`, s.note, s.used));
  if (x.v.source_url) addSrc(x.v.source_url, `verify:${x.key}`, x.v.verbatim_quote, x.v.found !== false);
});
// section stage
sectionResults.forEach((s) => (s.sources_consulted || []).forEach((src) => addSrc(src.url, `section:${s.key}`, src.note, src.used)));
// tag URLs that actually backed a PUBLISHED deterministic field
for (const key of DET_FIELDS) {
  const p = prov[key];
  if (p && p.value != null && p.url) { const e = ledger.get(String(p.url).trim()); if (e) e.backed_published_fields.push(key); }
}
const source_ledger = Array.from(ledger.values()).map((e) => ({
  url: e.url,
  roles: Array.from(e.roles),
  used: e.used || e.backed_published_fields.length > 0,
  backed_published_fields: e.backed_published_fields,
  notes: e.notes,
})).sort((a, b) => (b.backed_published_fields.length - a.backed_published_fields.length) || a.url.localeCompare(b.url));
log(`Source ledger: ${source_ledger.length} distinct URLs consulted; ${source_ledger.filter((s) => s.backed_published_fields.length).length} backed a published value.`);

const detTotal = DET_FIELDS.length;
const detPublished = DET_FIELDS.filter((k) => detVal[k] != null).length;
const trust_report = {
  university: resolved.official_name, id: ID, cycle: CYCLE, cds_edition_used: resolved.sources.common_data_set_cycle_found,
  ipeds_unitid: resolved.ipeds_unitid || null,
  deterministic_fields: { total: detTotal, published: detPublished, held_null: detTotal - detPublished },
  verification: trust,
  total_sources_consulted: source_ledger.length,
  sources_backing_published_values: source_ledger.filter((s) => s.backed_published_fields.length).length,
  acceptance_rate_published: profile.admissions_data.current_status.overall_acceptance_rate,
  ingest_ready: !!(profile._id && profile.metadata.official_name),
  doctrine: 'null-over-guess; deterministic fields anchored to CDS/Scorecard with provenance; high-stakes fields blind-verified; arithmetic-gated; every source consulted is logged',
};

log(`Assembled ${resolved.official_name}: ${detPublished}/${detTotal} deterministic fields published, ${detTotal - detPublished} honestly null.`);

return { profile, _provenance: prov, _trust_report: trust_report, _source_ledger: source_ledger };
