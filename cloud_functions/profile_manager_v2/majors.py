"""Major-selection plumbing (#281, epic #280).

Three concerns, all deterministic (no LLM, no credits):
- onboarding persistence: the OnboardingModal payload finally gets a writer
  (`flatten_onboarding_profile` matches the modal's REAL nested shape).
- the candidate set: `set_intended_majors` writes the ranked list and mirrors
  `intended_major` (the single string is load-bearing in fit computation).
- the per-school decision: `set_major_choice` validates the name against the
  school's KB majors (exact/strong auto-canonicalize; fuzzy stored with
  matched=False — never silently rewrite student intent) and persists
  `major_choice` + the legacy `selected_major` mirror on the list item.
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional

from firestore_db import get_db
from major_match import kb_major_names, match_major

logger = logging.getLogger(__name__)

MAX_INTENDED_MAJORS = 5


def flatten_onboarding_profile(profile_data: Dict) -> Dict:
    """Flatten the OnboardingModal payload into flat profile fields.

    Modal shape (frontend/src/components/OnboardingModal.jsx handleComplete):
    {student_info:{name,grade,high_school,state}, academic_profile:{gpa:{weighted},
    test_scores:{sat:{composite},act:{composite}}, ap_courses},
    interests:{intended_majors[],top_activity,activity_type},
    preferences:{preferred_locations[],school_size,campus_type},
    onboarding_status, onboarding_completed_at} — plus optional major_openness.
    """
    profile_data = profile_data or {}
    student = profile_data.get('student_info') or {}
    academic = profile_data.get('academic_profile') or {}
    gpa = academic.get('gpa') or {}
    tests = academic.get('test_scores') or {}
    sat = tests.get('sat') or {}
    act = tests.get('act') or {}
    interests = profile_data.get('interests') or {}
    preferences = profile_data.get('preferences') or {}

    majors = [m for m in (interests.get('intended_majors') or [])
              if isinstance(m, str) and m.strip()][:3]

    flat = {
        'name': student.get('name'),
        'grade': str(student['grade']) if student.get('grade') not in (None, '') else None,
        'school': student.get('high_school'),
        'location': student.get('state'),
        'gpa_weighted': gpa.get('weighted'),
        'sat_total': sat.get('composite'),
        'act_composite': act.get('composite'),
        'ap_courses_count': academic.get('ap_courses'),
        'intended_majors': majors or None,
        'intended_major': majors[0] if majors else None,
        'top_activity': interests.get('top_activity'),
        'activity_type': interests.get('activity_type'),
        'preferences': preferences or None,
        'major_openness': profile_data.get('major_openness'),
        'onboarding_status': profile_data.get('onboarding_status'),
        'onboarding_completed_at': profile_data.get('onboarding_completed_at'),
    }
    return {k: v for k, v in flat.items() if v is not None}


def save_onboarding_profile(user_email: str, profile_data: Dict) -> Dict:
    """Persist the onboarding wizard's payload (merge — never clobbers an
    existing richer profile field with null)."""
    try:
        flat = flatten_onboarding_profile(profile_data)
        if not flat:
            return {'success': False, 'error': 'empty onboarding payload'}
        flat['user_id'] = user_email
        flat['onboarding_source'] = 'onboarding_wizard'
        ok = get_db().save_profile(user_email, flat, merge=True)
        if not ok:
            return {'success': False, 'error': 'failed to save profile'}
        return {'success': True, 'saved_fields': sorted(k for k in flat
                                                        if k != 'user_id')}
    except Exception as e:
        logger.error(f"[MAJORS] save_onboarding_profile failed: {e}")
        return {'success': False, 'error': str(e)}


def set_intended_majors(user_email: str, majors: List, primary: Optional[str] = None) -> Dict:
    """Write the ranked candidate-major list (≤5, deduped case-insensitively)
    and mirror intended_major = primary (default: first item)."""
    try:
        cleaned, seen = [], set()
        for m in (majors or []):
            if not isinstance(m, str) or not m.strip():
                continue
            key = m.strip().lower()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(m.strip())
        if not cleaned:
            return {'success': False, 'error': 'majors must be a non-empty list of strings'}
        if len(cleaned) > MAX_INTENDED_MAJORS:
            return {'success': False,
                    'error': f'at most {MAX_INTENDED_MAJORS} majors (got {len(cleaned)})'}

        if primary and primary.strip():
            p = primary.strip()
            for existing in cleaned:
                if existing.lower() == p.lower():
                    cleaned.remove(existing)
                    break
            cleaned.insert(0, p)
            cleaned = cleaned[:MAX_INTENDED_MAJORS]

        ok = get_db().save_profile(user_email, {
            'intended_majors': cleaned,
            'intended_major': cleaned[0],
        }, merge=True)
        if not ok:
            return {'success': False, 'error': 'failed to save profile'}
        return {'success': True, 'intended_majors': cleaned, 'intended_major': cleaned[0]}
    except Exception as e:
        logger.error(f"[MAJORS] set_intended_majors failed: {e}")
        return {'success': False, 'error': str(e)}


def set_major_choice(user_email: str, university_id: str, primary_major: str,
                     backup_major: Optional[str] = None,
                     rationale: Optional[str] = None,
                     source: Optional[str] = None,
                     university_envelope: Optional[Dict] = None) -> Dict:
    """Record which major the student will LIST at one school.

    `university_envelope` is the KB get-university response body ('university'
    value: {..., data_year, profile}); the caller fetches it so this function
    stays HTTP-free and unit-testable. A missing envelope degrades to an
    unvalidated (matched=False) choice — never blocks.
    """
    try:
        if not isinstance(primary_major, str) or not primary_major.strip():
            return {'success': False, 'error': 'primary_major required'}
        primary_major = primary_major.strip()

        profile = (university_envelope or {}).get('profile') or {}
        names = kb_major_names(profile)
        match = match_major(primary_major, names) if names else {
            'found': False, 'kb_major_name': None, 'confidence': 'none', 'near_misses': []}

        # Only exact/strong matches auto-canonicalize to the KB spelling;
        # fuzzy keeps the student's words and is flagged for confirmation.
        matched = match['confidence'] in ('exact', 'strong')
        stored_primary = match['kb_major_name'] if matched else primary_major

        choice = {
            'primary': stored_primary,
            'backup': backup_major.strip() if isinstance(backup_major, str) and backup_major.strip() else None,
            'rationale': rationale.strip() if isinstance(rationale, str) and rationale.strip() else None,
            'source': source or 'app',
            'matched': matched,
            'match_confidence': match['confidence'],
            'kb_year': (university_envelope or {}).get('data_year'),
            'updated_at': datetime.utcnow().isoformat(),
        }

        ok = get_db().update_college_list_item(user_email, university_id, {
            'major_choice': choice,
            'selected_major': stored_primary,  # legacy mirror the UI reads
            'updated_at': choice['updated_at'],
        })
        if not ok:
            return {'success': False,
                    'error': f"'{university_id}' is not on the college list — add it first"}
        return {
            'success': True,
            'university_id': university_id,
            'major_choice': choice,
            'near_misses': match.get('near_misses') or [],
            'note': (None if matched else
                     f"'{primary_major}' couldn't be matched to this school's official "
                     f"major list — stored as given; confirm the name (see near_misses)."),
        }
    except Exception as e:
        logger.error(f"[MAJORS] set_major_choice failed: {e}")
        return {'success': False, 'error': str(e)}


def resolve_intended_major(profile: Optional[Dict], list_item: Optional[Dict],
                           explicit: Optional[str] = None) -> Dict:
    """Fit-computation major resolution order (#281):
    explicit request param → the school's saved major_choice.primary →
    legacy selected_major → profile.intended_major.
    Returns {major, source} so the fit doc can stamp intended_major_used."""
    if isinstance(explicit, str) and explicit.strip():
        return {'major': explicit.strip(), 'source': 'request'}
    choice = (list_item or {}).get('major_choice') or {}
    if isinstance(choice.get('primary'), str) and choice['primary'].strip():
        return {'major': choice['primary'].strip(), 'source': 'major_choice'}
    selected = (list_item or {}).get('selected_major')
    if isinstance(selected, str) and selected.strip():
        return {'major': selected.strip(), 'source': 'selected_major'}
    fallback = (profile or {}).get('intended_major') or ''
    return {'major': fallback, 'source': 'profile'}
