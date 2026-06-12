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
