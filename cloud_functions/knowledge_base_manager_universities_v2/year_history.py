"""Read-time helpers for year-versioned university access.

Section projection (`?sections=`) and the two-axis history view
(`?action=history`). Everything here is pure — no Firestore, no HTTP — so
it unit-tests without fakes.

History returns two deliberately SEPARATE structures; they must never be
merged into one timeline:

- ``snapshots`` — one compact row per stored KB version, keyed by the
  ADR-0002 CYCLE year (year N = applications due fall N / winter N+1,
  enrolling fall N+1). A cycle-N row describes the KB's state of knowledge
  during cycle N: its deadlines are for cycle-N applicants, and its
  admitted-class stats are the most recent numbers the school had published
  when the snapshot was collected.
- ``reported_trends`` — the current profile's
  ``admissions_data.longitudinal_trends`` rows passed through with
  ``verified: false``. Their ``year`` follows the collector's
  entering-class convention — a DIFFERENT axis from cycle year — and most
  rows predate the provenance pipeline. Merging the axes double-counts the
  same admitted class under adjacent year keys.
"""
from typing import Dict, List, Optional, Tuple

# The canonical top-level profile sections (UniversityProfile in
# agents/university_profile_collector/model.py). Kept permissive on the
# read path: projection intersects with what the stored profile actually
# has; this tuple only decides which requested names count as typos.
PROFILE_SECTIONS = (
    'metadata',
    'strategic_profile',
    'admissions_data',
    'academic_structure',
    'application_process',
    'application_strategy',
    'financials',
    'credit_policies',
    'student_insights',
    'outcomes',
    'student_retention',
)


def project_profile_sections(profile: Optional[Dict], sections: List[str]) -> Tuple[Dict, List[str], List[str]]:
    """Project a stored profile down to the requested top-level sections.

    Returns (projected_profile, sections_returned, unknown_sections).
    A valid section name the profile simply lacks is neither returned nor
    unknown — absence is honest data, not an error.
    """
    profile = profile or {}
    requested = [s for s in (sections or []) if s]
    returned = [s for s in requested if s in profile]
    unknown = [s for s in requested if s not in PROFILE_SECTIONS]
    projected = {s: profile[s] for s in returned}
    return projected, returned, unknown


def _pct(value):
    """Best-effort percent normalization for read paths.

    Snapshots written before ingest-time normalize_percentages (and legacy
    docs auto-archived verbatim) can carry fraction-style rates: 0.459
    meaning 45.9%. Same disambiguation rule as versioning.normalize_percentages
    (no US university has a sub-1% value for these fields).
    """
    if isinstance(value, float) and 0 < value < 1:
        return round(value * 100, 2)
    return value


def _deadline_rows(profile: Dict) -> List[Dict]:
    """Deadlines with both stored key spellings handled (plan_type|type, date|deadline)."""
    rows = []
    app_process = profile.get('application_process') or {}
    for d in (app_process.get('application_deadlines') or []):
        if isinstance(d, dict):
            rows.append({
                'plan': d.get('plan_type') or d.get('type'),
                'date': d.get('date') or d.get('deadline'),
                'is_binding': d.get('is_binding'),
            })
    return rows


def extract_year_summary(doc: Dict, source: str = 'kb_snapshot') -> Dict:
    """One compact history row from a stored KB doc (version snapshot or main).

    Pure and defensive: tolerates missing sections, fraction-style rates,
    and both deadline key spellings. `year` may be None for a legacy main
    doc that was never re-ingested (source 'kb_current').
    """
    doc = doc or {}
    profile = doc.get('profile') or {}
    admissions = profile.get('admissions_data') or {}
    current = admissions.get('current_status') or {}
    admitted = admissions.get('admitted_student_profile') or {}
    gpa = admitted.get('gpa') or {}
    testing = admitted.get('testing') or {}
    financials = profile.get('financials') or {}
    coa = financials.get('cost_of_attendance_breakdown') or {}
    in_state = coa.get('in_state') or {}
    out_of_state = coa.get('out_of_state') or {}
    strategic = profile.get('strategic_profile') or {}

    year = doc.get('data_year')

    rate = current.get('overall_acceptance_rate')
    if rate is None:
        rate = doc.get('acceptance_rate')

    rank = strategic.get('us_news_rank')
    if rank is None:
        rank = doc.get('us_news_rank')

    early = []
    for e in (current.get('early_admission_stats') or []):
        if isinstance(e, dict):
            early.append({
                'plan_type': e.get('plan_type'),
                'acceptance_rate': _pct(e.get('acceptance_rate')),
                'class_fill_percentage': _pct(e.get('class_fill_percentage')),
            })

    return {
        'year': year,
        'cycle_label': f"{year}–{(year + 1) % 100:02d}" if isinstance(year, int) else None,
        'source': source,
        'vintage_estimated': bool(doc.get('vintage_estimated')),
        'as_of': doc.get('indexed_at'),
        'acceptance_rate': _pct(rate),
        'in_state_acceptance_rate': _pct(current.get('in_state_acceptance_rate')),
        'out_of_state_acceptance_rate': _pct(current.get('out_of_state_acceptance_rate')),
        'admits_class_size': current.get('admits_class_size'),
        'test_policy': current.get('test_policy_details') or doc.get('test_policy') or None,
        'is_test_optional': current.get('is_test_optional'),
        'early_admission': early,
        'sat_middle_50': testing.get('sat_composite_middle_50'),
        'act_middle_50': testing.get('act_composite_middle_50'),
        'gpa_weighted_middle_50': gpa.get('weighted_middle_50'),
        'tuition_in_state': in_state.get('tuition'),
        'tuition_out_of_state': out_of_state.get('tuition'),
        'total_coa_in_state': in_state.get('total_coa'),
        'total_coa_out_of_state': out_of_state.get('total_coa'),
        'us_news_rank': rank,
        'deadlines': _deadline_rows(profile),
    }


def extract_reported_trends(profile: Optional[Dict]) -> List[Dict]:
    """The profile's own longitudinal_trends rows, labeled and passed through."""
    rows = []
    admissions = (profile or {}).get('admissions_data') or {}
    for t in (admissions.get('longitudinal_trends') or []):
        if not isinstance(t, dict):
            continue
        waitlist = t.get('waitlist_stats') if isinstance(t.get('waitlist_stats'), dict) else {}
        rows.append({
            'year': t.get('year'),
            'cycle_name': t.get('cycle_name'),
            'applications_total': t.get('applications_total'),
            'admits_total': t.get('admits_total'),
            'enrolled_total': t.get('enrolled_total'),
            'acceptance_rate_overall': _pct(t.get('acceptance_rate_overall')),
            'acceptance_rate_in_state': _pct(t.get('acceptance_rate_in_state')),
            'acceptance_rate_out_of_state': _pct(t.get('acceptance_rate_out_of_state')),
            'yield_rate': _pct(t.get('yield_rate')),
            'waitlist_admitted': (waitlist or {}).get('admitted_from_waitlist'),
            'notes': t.get('notes') or None,
            'source': 'profile_trend',
            'verified': False,
        })
    rows.sort(key=lambda r: (r['year'] is not None, r['year'] or 0), reverse=True)
    return rows


def build_history(main_doc: Optional[Dict], version_docs: List[Dict],
                  years: Optional[List[int]] = None,
                  sections: Optional[List[str]] = None) -> Dict:
    """Assemble the history payload from one university's stored docs.

    Compact mode (no sections): {'snapshots': [...], 'reported_trends': [...],
    'notes': [...]}. Sections mode: {'years': {year: {section: data}},
    'notes': [...]} over kb snapshots only. The main doc never contributes
    its own snapshot row when version snapshots exist — post-versioning it
    always duplicates one of them; a zero-version legacy school gets a
    single 'kb_current' row (year possibly null, never guessed).
    """
    version_docs = version_docs or []
    if years:
        wanted = set(years)
        version_docs = [d for d in version_docs if d.get('data_year') in wanted]

    notes: List[str] = []

    if sections:
        year_map: Dict[str, Dict] = {}
        for doc in version_docs:
            year = doc.get('data_year')
            if year is None:
                continue
            projected, _, _ = project_profile_sections(doc.get('profile'), sections)
            year_map[str(year)] = projected
        if not year_map:
            notes.append(
                'No versioned snapshots match this request — most of the KB has '
                'only recently become year-versioned; check available_years.'
            )
        return {'years': year_map, 'notes': notes}

    snapshots = [extract_year_summary(d) for d in version_docs]
    snapshots.sort(key=lambda s: (s['year'] is not None, s['year'] or 0), reverse=True)
    if not snapshots and main_doc:
        snapshots = [extract_year_summary(main_doc, source='kb_current')]
        notes.append(
            'No versioned snapshots stored yet for this university — the single '
            'row reflects the current serving doc (year may be null for '
            'pre-versioning data); multi-year context below comes only from '
            'school-reported trend rows.'
        )
    if any(s.get('vintage_estimated') for s in snapshots):
        notes.append(
            'Rows marked vintage_estimated were auto-archived from pre-versioning '
            'data — their year is a best guess, not a verified collection cycle.'
        )

    reported_trends = extract_reported_trends((main_doc or {}).get('profile'))

    return {
        'snapshots': snapshots,
        'reported_trends': reported_trends,
        'notes': notes,
    }
