"""
Work feed aggregator for the consolidated Roadmap surface.

Composes a unified focus list across four sources:
  - roadmap_tasks       (user-owned, profile_manager_v2)
  - essay_tracker       (user-owned, profile_manager_v2)
  - scholarship_tracker (user-owned, profile_manager_v2)
  - college deadlines   (KB-derived via fetch_aggregated_deadlines)

Sorted by due-date ascending; per-instance in-memory cache with short TTL.
This module is the single source of truth for the /work-feed endpoint;
main.py only dispatches to get_work_feed().
"""

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import requests

from counselor_tools import fetch_aggregated_deadlines

logger = logging.getLogger(__name__)

PROFILE_MANAGER_URL = os.getenv('PROFILE_MANAGER_URL', 'http://localhost:8080')

# Per-instance work-feed cache. Survives across warm invocations on the same
# Cloud Functions instance. Key: user_email -> (cached_at_monotonic, items).
# Short TTL — stale data here is preferable to refetching on every tab switch,
# but the underlying calls are cheap enough that misses are tolerable.
_CACHE_TTL_SECONDS = 90
_cache: dict = {}

# How many days past a deadline we still surface as "overdue" before dropping it.
_OVERDUE_GRACE_DAYS = 7

# Per-call timeout for each upstream HTTP fetch.
_FETCH_TIMEOUT_SECONDS = 15

# Hard cap on items per response, regardless of caller's `limit`.
_MAX_LIMIT = 50


def get_work_feed(user_email: str, limit: int = 8) -> dict:
    """Return the unified focus list for `user_email`, capped at `limit`."""
    items = _cached_or_build(user_email)
    bounded = max(1, min(limit, _MAX_LIMIT))
    return {
        'success': True,
        'items': items[:bounded],
        'total': len(items),
    }


def invalidate_cache(user_email=None) -> None:
    """Drop the cache entry for `user_email`, or all entries if None."""
    if user_email is None:
        _cache.clear()
    else:
        _cache.pop(user_email, None)


def _cached_or_build(user_email: str) -> list:
    """Return cached normalized items if fresh, else recompute and store."""
    now = time.monotonic()
    cached = _cache.get(user_email)
    if cached and (now - cached[0]) < _CACHE_TTL_SECONDS:
        return cached[1]
    items = _build_normalized_items(user_email)
    _cache[user_email] = (now, items)
    return items


def _build_normalized_items(user_email: str) -> list:
    """Fetch all four sources in parallel and merge into a sorted, normalized list."""
    with ThreadPoolExecutor(max_workers=4) as ex:
        f_tasks = ex.submit(_fetch_roadmap_tasks, user_email)
        f_essays = ex.submit(_fetch_essays, user_email)
        f_scholarships = ex.submit(_fetch_scholarships, user_email)
        f_deadlines = ex.submit(_safe_fetch_deadlines, user_email)
        tasks = f_tasks.result()
        essays = f_essays.result()
        scholarships = f_scholarships.result()
        deadlines = f_deadlines.result()

    today = datetime.now(timezone.utc).date()
    items = []
    items.extend(_normalize_tasks(tasks, today))
    items.extend(_normalize_essays(essays, today))
    items.extend(_normalize_scholarships(scholarships, today))
    items.extend(_normalize_deadlines(deadlines, today))
    items.sort(key=_sort_key)
    return items


# ---------- Source fetchers (best-effort: log + return [] on failure) ----------

def _fetch_roadmap_tasks(user_email: str) -> list:
    return _fetch_pm_collection('/get-roadmap-tasks', user_email, json_key='tasks')


def _fetch_essays(user_email: str) -> list:
    return _fetch_pm_collection('/get-essay-tracker', user_email, json_key='essays')


def _fetch_scholarships(user_email: str) -> list:
    return _fetch_pm_collection('/get-scholarship-tracker', user_email, json_key='scholarships')


def _fetch_pm_collection(path: str, user_email: str, json_key: str) -> list:
    try:
        url = f"{PROFILE_MANAGER_URL}{path}"
        resp = requests.get(
            url,
            params={'user_email': user_email},
            timeout=_FETCH_TIMEOUT_SECONDS,
        )
        if resp.status_code != 200:
            logger.warning(
                "work-feed: %s returned %s for %s",
                path, resp.status_code, user_email,
            )
            return []
        return resp.json().get(json_key, []) or []
    except Exception as e:
        logger.warning("work-feed: failed %s for %s: %s", path, user_email, e)
        return []


def _safe_fetch_deadlines(user_email: str) -> list:
    try:
        return fetch_aggregated_deadlines(user_email) or []
    except Exception as e:
        logger.warning("work-feed: deadline fetch failed for %s: %s", user_email, e)
        return []


# ---------- Normalizers (one per source, output the unified item shape) ----------

def _normalize_tasks(tasks: list, today) -> list:
    out = []
    for t in tasks:
        if (t.get('status') or '').lower() == 'completed':
            continue
        due = _parse_iso_date(t.get('due_date'))
        task_id = t.get('task_id') or t.get('id')
        out.append({
            'id': str(task_id or ''),
            'source': 'roadmap_task',
            'title': t.get('title') or 'Untitled task',
            'subtitle': t.get('description') or None,
            'due_date': _to_iso(due),
            'days_until': _days_until(due, today),
            'urgency': _urgency(due, today),
            'university_id': t.get('university_id'),
            'university_name': t.get('university_name'),
            'status': t.get('status'),
            'notes': t.get('notes'),
            'deep_link': (
                f'/roadmap?tab=plan&task_id={task_id}' if task_id else '/roadmap?tab=plan'
            ),
        })
    return out


def _normalize_essays(essays: list, today) -> list:
    out = []
    for e in essays:
        if (e.get('status') or '').lower() == 'final':
            continue
        essay_id = e.get('essay_id')
        out.append({
            'id': str(essay_id or ''),
            'source': 'essay',
            'title': _essay_title(e),
            'subtitle': e.get('university_name'),
            # Essays don't carry a per-row due_date today; treated as "no date".
            'due_date': None,
            'days_until': None,
            'urgency': None,
            'university_id': e.get('university_id'),
            'university_name': e.get('university_name'),
            'status': e.get('status'),
            'notes': e.get('notes'),
            'deep_link': (
                f'/roadmap?tab=essays&essay_id={essay_id}' if essay_id else '/roadmap?tab=essays'
            ),
        })
    return out


def _normalize_scholarships(scholarships: list, today) -> list:
    out = []
    for s in scholarships:
        status = (s.get('status') or '').lower()
        if status in ('received', 'not_eligible'):
            continue
        due = _parse_iso_date(s.get('deadline'))
        sch_id = s.get('scholarship_id')
        out.append({
            'id': str(sch_id or ''),
            'source': 'scholarship',
            'title': s.get('scholarship_name') or 'Scholarship',
            'subtitle': s.get('university_name'),
            'due_date': _to_iso(due),
            'days_until': _days_until(due, today),
            'urgency': _urgency(due, today),
            'university_id': s.get('university_id'),
            'university_name': s.get('university_name'),
            'status': s.get('status'),
            'notes': s.get('notes'),
            'deep_link': (
                f'/roadmap?tab=scholarships&scholarship_id={sch_id}'
                if sch_id else '/roadmap?tab=scholarships'
            ),
        })
    return out


def _normalize_deadlines(deadlines: list, today) -> list:
    out = []
    cutoff = today - timedelta(days=_OVERDUE_GRACE_DAYS)
    for d in deadlines:
        due = _parse_iso_date(d.get('date'))
        if due is not None and due < cutoff:
            continue
        uni_id = d.get('university_id')
        uni_name = d.get('university_name')
        deadline_type = d.get('deadline_type') or 'Deadline'
        out.append({
            'id': _deadline_id(uni_id, deadline_type),
            'source': 'college_deadline',
            'title': f'{deadline_type} — {uni_name}' if uni_name else deadline_type,
            'subtitle': d.get('notes') or None,
            'due_date': _to_iso(due),
            'days_until': _days_until(due, today),
            'urgency': _urgency(due, today),
            'university_id': uni_id,
            'university_name': uni_name,
            'status': None,
            'notes': None,
            'deep_link': (
                f'/roadmap?tab=colleges&school={uni_id}' if uni_id else '/roadmap?tab=colleges'
            ),
        })
    return out


# ---------- Helpers ----------

def _parse_iso_date(value):
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value[:10], '%Y-%m-%d').date()
    except ValueError:
        return None


def _to_iso(date_obj):
    return date_obj.isoformat() if date_obj else None


def _days_until(due, today):
    if due is None:
        return None
    return (due - today).days


def _urgency(due, today):
    if due is None:
        return None
    days = (due - today).days
    if days < 0:
        return 'overdue'
    if days <= 7:
        return 'urgent'
    if days <= 30:
        return 'soon'
    return 'later'


def _sort_key(item):
    """Date-bearing items first, oldest due first; ties broken by source/title."""
    d = item.get('due_date')
    return (
        0 if d else 1,
        d or '',
        item.get('source', ''),
        item.get('title', ''),
    )


def _essay_title(e):
    base = e.get('university_name') or 'Essay'
    idx = e.get('prompt_index')
    suffix = f' #{idx + 1}' if isinstance(idx, int) else ''
    prompt = e.get('prompt_text') or ''
    short = (prompt[:60] + '…') if len(prompt) > 60 else prompt
    return f'{base}{suffix}: {short}' if short else f'{base}{suffix}'


def _deadline_id(uni_id, deadline_type):
    safe_type = (deadline_type or 'deadline').replace(' ', '_')
    return f'deadline_{uni_id or "unknown"}_{safe_type}'
