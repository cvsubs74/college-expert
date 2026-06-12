"""
KB provenance stamping + staleness detection for college-fit analyses.

Phase 1 of docs/design/DESIGN-kb-refresh-fit-staleness.md (#204):
- build_kb_provenance() — stamped onto every fit at compute time so a fit
  records which KB vintage produced it and the load-bearing inputs.
- classify_kb_changes() — deterministic (no LLM) diff of a saved fit's
  inputs against the university's current KB doc, with severity per field.
- get_kb_updates() — the per-user sweep behind /check-fit-recomputation.

Severity rules (design §2):
  material — acceptance rate crosses a selectivity-tier boundary or moves
             more than 5 points; any application-deadline change; any
             test-policy change.
  minor    — within-tier rate drift; cost-of-attendance drift under 10%.
  unknown  — the fit predates provenance stamping (legacy doc).
"""

import hashlib
import json
import logging
import os
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

KNOWLEDGE_BASE_UNIVERSITIES_URL = os.environ.get(
    'KNOWLEDGE_BASE_UNIVERSITIES_URL',
    'https://knowledge-base-manager-universities-v2-pfnwjfp26a-ue.a.run.app'
)

# Selectivity tiers — mirrors the inline rules in fit_computation.py's
# calculate_fit_with_llm (acceptance-rate thresholds 8/15/25/40). If those
# change, change these too; test_fit_staleness pins the contract.
_TIER_BOUNDS = (
    (8, 'ULTRA_SELECTIVE', 'SUPER_REACH'),
    (15, 'HIGHLY_SELECTIVE', 'REACH'),
    (25, 'VERY_SELECTIVE', None),
    (40, 'SELECTIVE', None),
    (101, 'ACCESSIBLE', None),
)

# Category ordering for floor comparisons (most → least selective).
_CATEGORY_RANK = {'SUPER_REACH': 0, 'REACH': 1, 'TARGET': 2, 'SAFETY': 3}


def selectivity_tier(acceptance_rate) -> Optional[str]:
    if not isinstance(acceptance_rate, (int, float)) or acceptance_rate <= 0:
        return None
    for bound, tier, _floor in _TIER_BOUNDS:
        if acceptance_rate < bound:
            return tier
    return None


def category_floor(acceptance_rate) -> Optional[str]:
    """Minimum (most optimistic) category the deterministic rules allow."""
    if not isinstance(acceptance_rate, (int, float)) or acceptance_rate <= 0:
        return None
    for bound, _tier, floor in _TIER_BOUNDS:
        if acceptance_rate < bound:
            return floor
    return None


def _profile_of(university_data: Dict) -> Dict:
    return (university_data or {}).get('profile') or {}


def _acceptance_rate(university_data: Dict):
    p = _profile_of(university_data)
    rate = ((p.get('admissions_data') or {}).get('current_status') or {}) \
        .get('overall_acceptance_rate')
    if rate is None:
        rate = university_data.get('acceptance_rate')
    return rate


def _test_policy(university_data: Dict) -> str:
    p = _profile_of(university_data)
    return (((p.get('admissions_data') or {}).get('current_status') or {})
            .get('test_policy_details') or '')


def _deadlines(university_data: Dict) -> list:
    p = _profile_of(university_data)
    return ((p.get('application_process') or {}).get('application_deadlines') or [])


def _deadlines_hash(university_data: Dict) -> str:
    rows = sorted(
        (str(d.get('plan_type') or d.get('type') or ''), str(d.get('date') or ''))
        for d in _deadlines(university_data) if isinstance(d, dict)
    )
    return hashlib.sha1(json.dumps(rows).encode()).hexdigest()


def _total_coa(university_data: Dict):
    p = _profile_of(university_data)
    coa = ((p.get('financials') or {}).get('cost_of_attendance_breakdown') or {})
    for residency in ('out_of_state', 'in_state'):
        block = coa.get(residency)
        if isinstance(block, dict) and block.get('total_coa'):
            return block['total_coa']
    return None


def build_kb_provenance(university_data: Dict) -> Dict:
    """The fields stamped onto a fit doc at compute time."""
    return {
        'kb_data_year': (university_data or {}).get('data_year'),
        'kb_last_updated': (university_data or {}).get('last_updated'),
        'input_snapshot': {
            'acceptance_rate': _acceptance_rate(university_data),
            'test_policy': _test_policy(university_data),
            'deadlines_hash': _deadlines_hash(university_data),
            'total_coa': _total_coa(university_data),
        },
    }


def classify_kb_changes(fit_doc: Dict, university_data: Dict) -> Optional[Dict]:
    """Diff a saved fit's recorded inputs against the current KB doc.

    Returns a kb_update entry when the fit is stale, else None.
    """
    university_id = fit_doc.get('university_id')
    current_year = (university_data or {}).get('data_year')
    fit_year = fit_doc.get('kb_data_year')
    snapshot = fit_doc.get('input_snapshot')

    entry = {
        'university_id': university_id,
        'university_name': fit_doc.get('university_name')
                           or (university_data or {}).get('official_name'),
        'fit_kb_year': fit_year,
        'current_kb_year': current_year,
        'changes': [],
        'projected_category_shift': None,
    }

    # Legacy fit: predates provenance stamping. We can't diff inputs, but it
    # is stale by definition relative to any versioned KB doc.
    if fit_year is None or not isinstance(snapshot, dict):
        if current_year is None:
            return None  # neither side versioned — nothing to say
        entry['changes'].append({
            'field': 'provenance',
            'severity': 'unknown',
            'detail': 'fit predates KB provenance stamping — inputs unknown',
        })
        return entry

    if current_year is not None and fit_year >= current_year:
        return None  # fit is current

    changes = entry['changes']

    old_rate = snapshot.get('acceptance_rate')
    new_rate = _acceptance_rate(university_data)
    if old_rate is not None and new_rate is not None and old_rate != new_rate:
        tier_crossed = selectivity_tier(old_rate) != selectivity_tier(new_rate)
        material = tier_crossed or abs(new_rate - old_rate) > 5
        changes.append({
            'field': 'acceptance_rate',
            'old': old_rate,
            'new': new_rate,
            'severity': 'material' if material else 'minor',
        })
        # Projected shift: the new rate's category floor is stricter than the
        # category the student currently sees → guaranteed change.
        old_cat = fit_doc.get('fit_category')
        floor = category_floor(new_rate)
        if (floor and old_cat in _CATEGORY_RANK
                and _CATEGORY_RANK[floor] < _CATEGORY_RANK[old_cat]):
            entry['projected_category_shift'] = f"{old_cat} → {floor}"

    if snapshot.get('deadlines_hash') != _deadlines_hash(university_data):
        changes.append({
            'field': 'application_deadlines',
            'severity': 'material',
            'detail': 'application deadlines changed',
        })

    old_policy = snapshot.get('test_policy') or ''
    new_policy = _test_policy(university_data)
    if old_policy != new_policy:
        changes.append({
            'field': 'test_policy',
            'old': old_policy,
            'new': new_policy,
            'severity': 'material',
        })

    old_coa = snapshot.get('total_coa')
    new_coa = _total_coa(university_data)
    if (isinstance(old_coa, (int, float)) and isinstance(new_coa, (int, float))
            and old_coa > 0 and old_coa != new_coa):
        drift = abs(new_coa - old_coa) / old_coa
        changes.append({
            'field': 'total_coa',
            'old': old_coa,
            'new': new_coa,
            'severity': 'material' if drift >= 0.10 else 'minor',
        })

    # Stale year but nothing load-bearing moved — still report (the vintage
    # chip needs it), as a single minor entry.
    if not changes:
        changes.append({
            'field': 'kb_data_year',
            'old': fit_year,
            'new': current_year,
            'severity': 'minor',
            'detail': 'newer cycle data, no material input changes',
        })
    return entry


# College-list statuses that mean the application clock has run out for
# nudging purposes (design §3f) — the student applied or has a decision.
SETTLED_STATUSES = ('applied', 'accepted', 'rejected')


def mark_suppressed(kb_updates: List[Dict], college_list: List[Dict]) -> List[Dict]:
    """Flag kb_updates for colleges the student already applied to.

    Suppressed entries still carry their staleness data (the vintage chip
    renders from it) — the flag only gates banners/nudges. Mutates and
    returns kb_updates.
    """
    settled = {
        item.get('university_id')
        for item in (college_list or [])
        if item.get('status') in SETTLED_STATUSES
    }
    for update in kb_updates:
        update['nudge_suppressed'] = update.get('university_id') in settled
    return kb_updates


def _batch_fetch_universities(university_ids: List[str]) -> Dict[str, Dict]:
    """One KB batch call → {university_id: university_doc}."""
    if not university_ids:
        return {}
    try:
        resp = requests.post(
            KNOWLEDGE_BASE_UNIVERSITIES_URL,
            json={'university_ids': university_ids},
            timeout=30,
        )
        resp.raise_for_status()
        body = resp.json()
        return {
            u.get('university_id'): u
            for u in (body.get('universities') or [])
            if u.get('university_id')
        }
    except (requests.RequestException, ValueError) as e:
        logger.error(f"[FIT_STALENESS] KB batch fetch failed: {e}")
        return {}


def get_kb_updates(fits: List[Dict],
                   fetch_batch=_batch_fetch_universities) -> List[Dict]:
    """kb_updates[] for a user's saved fits. `fetch_batch` injectable for tests.

    Note: the batch endpoint's docs don't include data_year yet on old
    deploys; entries whose university is missing from the batch result are
    skipped (can't classify without current data).
    """
    ids = [f.get('university_id') for f in fits if f.get('university_id')]
    current = fetch_batch(ids)
    updates = []
    for fit in fits:
        uni = current.get(fit.get('university_id'))
        if not uni:
            continue
        entry = classify_kb_changes(fit, uni)
        if entry:
            updates.append(entry)
    return updates
