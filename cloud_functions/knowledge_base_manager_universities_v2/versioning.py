"""
Cycle-year derivation and ingest-boundary validation for the university KB.

See harness/decisions/0002-university-kb-year-versioning.md for the design.
"""
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

# Months April-December belong to the cycle that opens that fall; Jan-Mar
# are the tail of the cycle that opened the previous fall.
_CYCLE_ROLLOVER_MONTH = 4


def current_cycle_year(today: Optional[datetime] = None) -> int:
    """Admission cycle year for `today` (default: now, UTC).

    cycle_year = N covers applications due fall N / winter N+1.
    """
    if today is None:
        today = datetime.now(timezone.utc)
    if today.month >= _CYCLE_ROLLOVER_MONTH:
        return today.year
    return today.year - 1


def coerce_year(raw, default: Optional[int] = None) -> int:
    """Parse a caller-supplied year; fall back to the current cycle year.

    Raises ValueError for present-but-garbage values so the API can 400
    instead of silently filing data under the wrong year.
    """
    if raw is None or raw == '':
        return default if default is not None else current_cycle_year()
    year = int(raw)  # ValueError propagates for non-numeric input
    if not 2000 <= year <= 2100:
        raise ValueError(f"year {year} out of range 2000-2100")
    return year


# Percent-like fields that research passes sometimes return as fractions
# (0.459 for 45.9%). The heuristic 0 < v < 1 ⇒ fraction is only safe for
# fields with no legitimate sub-1% values (overall admission-style rates:
# the lowest real acceptance rate ≈ 3%). It is UNSAFE — and corrupts data —
# for rare-event rates and small population slices, where genuine sub-1%
# values exist in the corpus (#289):
#   transfer_acceptance_rate      Harvard: a real 0.8% became 80%
#   waitlist_admit_rate           CMU series [1.5, 0.9, ...] → [1.5, 90, ...]
#   international/legacy/first_gen_percentage, geographic 'percentage'
#                                 Clemson intl 0.84% → 84%
# Those keys are excluded: null-over-guess — an unconverted fraction is a
# recoverable ambiguity, a silent ×100 is corruption.
_PERCENT_KEY_SUFFIXES = ('_rate', '_percentage')
_PERCENT_KEY_EXACT = {'percent_receiving_aid', 'class_fill_percentage'}
_PERCENT_KEY_EXCLUDE = {
    'loan_default_rate',
    'transfer_acceptance_rate',
    'waitlist_admit_rate',
    'waitlist_acceptance_rate',
    'waitlist_yield_rate',
    'international_percentage',
    'legacy_percentage',
    'first_gen_percentage',
}


def _normalize_share_groups(obj):
    """Convert PROVABLE fraction groups: a list of dicts whose 'percentage'
    values sum to ~1.0 is a share breakdown stored as fractions (0.57+0.43);
    ×100 all members. This is arithmetic, not a guess — sub-1 'percentage'
    values are otherwise excluded as ambiguous (#289). Returns count converted.
    """
    converted = 0
    if isinstance(obj, dict):
        for value in obj.values():
            converted += _normalize_share_groups(value)
    elif isinstance(obj, list):
        shares = [item.get('percentage') for item in obj
                  if isinstance(item, dict) and isinstance(item.get('percentage'), (int, float))]
        if len(shares) >= 2 and all(0 < v <= 1 for v in shares) and 0.95 <= sum(shares) <= 1.05:
            for item in obj:
                if isinstance(item, dict) and isinstance(item.get('percentage'), (int, float)):
                    item['percentage'] = round(item['percentage'] * 100, 2)
                    converted += 1
        for item in obj:
            converted += _normalize_share_groups(item)
    return converted


def normalize_percentages(obj):
    """Recursively convert fraction-style percent fields to percents, in place.

    Returns the number of fields converted.
    """
    converted = _normalize_share_groups(obj)
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, (dict, list)):
                converted += normalize_percentages(value)
                continue
            is_pct_key = (
                key not in _PERCENT_KEY_EXCLUDE
                and (key.endswith(_PERCENT_KEY_SUFFIXES)
                     or '_rate_' in key  # acceptance_rate_overall, graduation_rate_4_year
                     or key in _PERCENT_KEY_EXACT)
            )
            if is_pct_key and isinstance(value, float) and 0 < value < 1:
                obj[key] = round(value * 100, 2)
                converted += 1
    elif isinstance(obj, list):
        for item in obj:
            converted += normalize_percentages(item)
    return converted


# Sections replaced wholesale from the fresh collection on a yearly refresh.
# Everything else is durable knowledge (majors, strategy, insights) that a
# single fresh research pass tends to cover more thinly than the original
# multi-agent collection — keep the richer base for those.
_CYCLE_SENSITIVE_PATHS = (
    ('admissions_data', 'current_status'),
    ('application_process', 'application_deadlines'),
    ('financials', 'cost_of_attendance_breakdown'),
    ('strategic_profile', 'us_news_rank'),
    ('strategic_profile', 'rankings'),
    ('metadata', 'last_updated'),
)


def merge_cycle_refresh(base: Dict, fresh: Dict) -> Dict:
    """Merge a fresh yearly collection onto the current rich profile.

    - Cycle-sensitive sections come from `fresh` when present (the point of
      the refresh).
    - `admissions_data.longitudinal_trends` is unioned by year, fresh wins
      on collision (a new cycle adds a row instead of dropping history).
    - Everything else: `base` wins; keys only in `fresh` are added.

    Returns a new dict; neither input is mutated.
    """
    import copy

    merged = copy.deepcopy(base)

    def _ensure(d, key):
        if not isinstance(d.get(key), dict):
            d[key] = {}
        return d[key]

    # Add fresh-only top-level keys / fill gaps without overwriting base.
    def _fill_missing(dst, src):
        for k, v in src.items():
            if k not in dst or dst[k] in (None, '', [], {}):
                dst[k] = copy.deepcopy(v)
            elif isinstance(dst[k], dict) and isinstance(v, dict):
                _fill_missing(dst[k], v)

    _fill_missing(merged, fresh)

    # Cycle-sensitive sections: fresh replaces base when fresh has a value.
    for path in _CYCLE_SENSITIVE_PATHS:
        src = fresh
        for key in path:
            src = src.get(key) if isinstance(src, dict) else None
            if src is None:
                break
        if src in (None, '', [], {}):
            continue
        dst = merged
        for key in path[:-1]:
            dst = _ensure(dst, key)
        dst[path[-1]] = copy.deepcopy(src)

    # Longitudinal trends: union by year, fresh wins on collision.
    base_trends = ((base.get('admissions_data') or {}).get('longitudinal_trends') or [])
    fresh_trends = ((fresh.get('admissions_data') or {}).get('longitudinal_trends') or [])
    if base_trends or fresh_trends:
        by_year = {t.get('year'): t for t in base_trends if isinstance(t, dict)}
        for t in fresh_trends:
            if isinstance(t, dict):
                by_year[t.get('year')] = t
        # Newest year first; entries without a year sink to the end.
        trends = sorted(
            by_year.values(),
            key=lambda t: (t.get('year') is not None, t.get('year') or 0),
            reverse=True,
        )
        _ensure(merged, 'admissions_data')['longitudinal_trends'] = copy.deepcopy(trends)

    return merged


def _parse_date(value) -> Optional[datetime]:
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value.strip()[:10], '%Y-%m-%d')
    except ValueError:
        return None


def validate_profile(profile: Dict, year: int) -> Tuple[List[str], List[str]]:
    """Validate a collector profile at the ingest boundary.

    Returns (errors, warnings). Errors block the ingest; warnings are
    reported in the response but don't block. Deep accuracy checking
    (source cross-checks, gap filling) belongs to the collector/uniminer
    pipeline, not here.
    """
    errors: List[str] = []
    warnings: List[str] = []

    if not isinstance(profile, dict):
        return (["profile must be a JSON object"], [])

    if not profile.get('_id'):
        errors.append("profile missing '_id'")

    metadata = profile.get('metadata')
    if not isinstance(metadata, dict) or not metadata.get('official_name'):
        errors.append("profile missing 'metadata.official_name'")

    admissions = profile.get('admissions_data') or {}
    current = admissions.get('current_status') if isinstance(admissions, dict) else {}
    rate = current.get('overall_acceptance_rate') if isinstance(current, dict) else None
    if rate is not None:
        if not isinstance(rate, (int, float)) or not 0 < rate <= 100:
            errors.append(
                f"admissions_data.current_status.overall_acceptance_rate "
                f"must be in (0, 100], got {rate!r}"
            )
    else:
        warnings.append("no overall_acceptance_rate — fit categorization will be UNKNOWN")

    app_process = profile.get('application_process') or {}
    deadlines = app_process.get('application_deadlines') if isinstance(app_process, dict) else None
    if not deadlines:
        warnings.append("no application_deadlines — roadmap deadline tasks won't generate")
    elif isinstance(deadlines, list):
        for d in deadlines:
            if not isinstance(d, dict):
                warnings.append(f"non-object entry in application_deadlines: {d!r}")
                continue
            raw_date = d.get('date') or d.get('deadline')
            parsed = _parse_date(raw_date)
            label = d.get('plan_type') or d.get('type') or 'deadline'
            if parsed is None:
                warnings.append(f"unparseable date {raw_date!r} for '{label}'")
            elif not (year - 1 <= parsed.year <= year + 2):
                warnings.append(
                    f"'{label}' date {raw_date} is outside the cycle-{year} "
                    f"window ({year - 1}..{year + 2}) — wrong year's data?"
                )

    return errors, warnings
