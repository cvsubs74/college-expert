#!/usr/bin/env python3
"""
Execute the consolidated system scenarios (docs/scenarios/system-scenarios.md)
and write a dated markdown report to docs/scenarios/.

    .venv/bin/python scripts/run_scenarios.py             # everything
    .venv/bin/python scripts/run_scenarios.py --skip-live # unit/build only

Live scenarios target prod (college-counselling-478115) with sentinel
documents (_harness_scenario_*) and clean up after themselves. No scenario
spends LLM credits or touches real user data.
"""
import argparse
import json
import subprocess
import sys
import time
import types
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PY = str(REPO / '.venv' / 'bin' / 'python')
KB_URL = 'https://knowledge-base-manager-universities-v2-pfnwjfp26a-ue.a.run.app'
PM_URL = 'https://profile-manager-v2-pfnwjfp26a-ue.a.run.app'
SENTINEL_UNI = '_harness_scenario_university'
SENTINEL_USER = '_harness_scenario_user@test.com'

results = []  # {id, name, status, detail}


def record(sid, name, ok, detail=''):
    results.append({'id': sid, 'name': name,
                    'status': 'PASS' if ok else 'FAIL', 'detail': detail})
    print(f"[{'PASS' if ok else 'FAIL'}] {sid} — {name}" + (f" — {detail}" if detail else ''))
    return ok


def run(cmd, cwd=REPO, timeout=900):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


# --- S1 / S2: unit suites -----------------------------------------------

def s1_backend():
    rc, out = run([PY, '-m', 'pytest', 'tests/', '-q'])
    tail = out.strip().splitlines()[-1] if out.strip() else ''
    record('S1', 'Backend unit suite (pytest)', rc == 0 and ' passed' in tail, tail)


def s2_frontend():
    rc1, out1 = run(['npx', 'vitest', 'run'], cwd=REPO / 'frontend')
    tests_line = next((l.strip() for l in out1.splitlines() if 'Tests' in l and 'passed' in l), '')
    rc2, out2 = run(['npm', 'run', '-s', 'build'], cwd=REPO / 'frontend')
    record('S2', 'Frontend unit suite + build (vitest, vite)',
           rc1 == 0 and rc2 == 0, tests_line or 'see output')


# --- live helpers ----------------------------------------------------------

def _kb_db():
    sys.path.insert(0, str(REPO / 'cloud_functions' / 'knowledge_base_manager_universities_v2'))
    from firestore_db import FirestoreDB
    return FirestoreDB()


def _doc(marker, uid=SENTINEL_UNI):
    return {
        'university_id': uid, 'official_name': 'Harness Scenario University',
        'location': {'city': 'Nowhere', 'state': 'CA', 'type': 'Private'},
        'acceptance_rate': 25.0, 'summary': f'data from {marker}',
        'profile': {'_id': uid},
        'indexed_at': '2026-06-12T00:00:00+00:00',
    }


# --- S3: KB versioning lifecycle -------------------------------------------

def s3_lifecycle():
    db = _kb_db()
    checks = []
    try:
        r = db.save_university(SENTINEL_UNI, _doc('2025'), year=2025)
        checks.append(('first ingest promotes', r['promoted'] and r['available_years'] == [2025]))

        r = db.save_university(SENTINEL_UNI, _doc('2026'), year=2026)
        main = db.get_university(SENTINEL_UNI)
        checks.append(('newer year promotes', r['promoted'] and main['data_year'] == 2026))
        checks.append(('prior snapshot intact',
                       db.get_university(SENTINEL_UNI, year=2025)['summary'] == 'data from 2025'))

        r = db.save_university(SENTINEL_UNI, _doc('2024'), year=2024)
        main = db.get_university(SENTINEL_UNI)
        checks.append(('older year archives without clobber',
                       not r['promoted'] and main['data_year'] == 2026
                       and main['available_years'] == [2024, 2025, 2026]))

        db.save_university(SENTINEL_UNI, _doc('2026 refresh'), year=2026)
        checks.append(('same-year refresh idempotent',
                       db.get_university(SENTINEL_UNI)['summary'] == 'data from 2026 refresh'
                       and db.get_university(SENTINEL_UNI)['available_years'] == [2024, 2025, 2026]))

        # Legacy auto-archive (#199): fresh sentinel with a raw legacy doc.
        legacy_uni = SENTINEL_UNI + '_legacy'
        db.collection.document(legacy_uni).set(_doc('legacy', uid=legacy_uni))
        db.save_university(legacy_uni, _doc('2026', uid=legacy_uni), year=2026)
        legacy = db.get_university(legacy_uni, year=2025)
        checks.append(('legacy doc auto-archived under year-1',
                       legacy is not None and legacy['summary'] == 'data from legacy'))
        db.delete_university(legacy_uni)

        db.delete_university(SENTINEL_UNI, year=2026)
        main = db.get_university(SENTINEL_UNI)
        checks.append(('deleting serving year promotes latest remaining',
                       main['data_year'] == 2025))
    finally:
        db.delete_university(SENTINEL_UNI)
        gone = (db.get_university(SENTINEL_UNI) is None
                and db.list_university_versions(SENTINEL_UNI) == [])
        checks.append(('full delete + cleanup verified', gone))

    failed = [n for n, ok in checks if not ok]
    record('S3', 'KB versioning lifecycle (live Firestore)',
           not failed, f"{len(checks)} checks" + (f"; FAILED: {failed}" if failed else ''))


# --- S4: versioned read APIs ------------------------------------------------

def s4_read_apis():
    import requests
    cur = requests.get(f"{KB_URL}/?id=princeton_university", timeout=30).json()
    uni = cur.get('university') or {}
    legacy_keys = {'university_id', 'official_name', 'location', 'acceptance_rate',
                   'market_position', 'profile', 'indexed_at', 'last_updated'}
    ok_cur = cur.get('success') and legacy_keys <= set(uni) and uni.get('data_year') == 2026

    old = requests.get(f"{KB_URL}/?id=princeton_university&year=2025", timeout=30).json()
    ok_old = (old.get('success') and old['university'].get('data_year') == 2025
              and old['university'].get('acceptance_rate') != uni.get('acceptance_rate'))

    vers = requests.get(f"{KB_URL}/?id=princeton_university&action=versions", timeout=30).json()
    years = [v['year'] for v in vers.get('versions', [])]
    ok_vers = vers.get('success') and years[:2] == [2026, 2025]

    record('S4', 'Versioned read APIs (deployed)',
           ok_cur and ok_old and ok_vers,
           f"current data_year=2026, 2025 archive readable, versions={years}")


# --- S5: ingest validation gate ----------------------------------------------

def s5_validation_gate():
    import requests
    bad = requests.post(KB_URL, json={'profile': {'metadata': {}}}, timeout=30)
    ok_bad = bad.status_code == 400 and bad.json().get('validation_errors')

    bad_year = requests.post(
        KB_URL, json={'profile': {'_id': SENTINEL_UNI,
                                  'metadata': {'official_name': 'X'}},
                      'year': 1990}, timeout=30)
    ok_year = bad_year.status_code == 400 and 'year' in bad_year.json().get('error', '').lower()

    db = _kb_db()
    nothing_written = db.get_university(SENTINEL_UNI) is None

    record('S5', 'Ingest validation gate (deployed)',
           bool(ok_bad and ok_year and nothing_written),
           'invalid profile → 400; year 1990 → 400; nothing written')


# --- S6: 2026 data integrity ---------------------------------------------------

def s6_data_integrity():
    db = _kb_db()
    total = on_2026 = with_2025 = bad_rate = fraction = 0
    for doc in db.collection.stream():
        d = doc.to_dict()
        total += 1
        if d.get('data_year') == 2026:
            on_2026 += 1
        if 2025 in (d.get('available_years') or []):
            with_2025 += 1
        r = d.get('acceptance_rate')
        if r is not None:
            if not (0 < r <= 100):
                bad_rate += 1
            elif 0 < r < 1:
                fraction += 1
    ok = (total >= 191 and on_2026 == total and bad_rate == 0
          and fraction == 0 and with_2025 >= 185)
    record('S6', 'KB 2026 data integrity (live)', ok,
           f"{total} docs; {on_2026} on 2026; {with_2025} with 2025 archive; "
           f"{bad_rate} bad rates; {fraction} fraction-style")


# --- S7: collector corpus validation ----------------------------------------

def s7_corpus():
    sys.path.insert(0, str(REPO / 'cloud_functions' / 'knowledge_base_manager_universities_v2'))
    from versioning import validate_profile
    corpus = sorted((REPO / 'agents' / 'university_profile_collector' / 'research_2026').glob('*.json'))
    failed, warned = [], 0
    for p in corpus:
        try:
            errors, warnings = validate_profile(json.loads(p.read_text()), 2026)
        except Exception as e:
            errors, warnings = [str(e)], []
        if errors:
            failed.append(p.name)
        warned += 1 if warnings else 0
    # 189, not 191: georgia_institute_of_technology + michigan_state's
    # deep-research output truncates on their large program catalogs
    # (3 attempts each) — known exceptions, their KB docs serve the merged
    # rich data; re-collect manually next cycle.
    record('S7', 'Collector output validation (research_2026)',
           len(corpus) >= 189 and not failed,
           f"{len(corpus)} files, 0 errors, {warned} with warnings" if not failed
           else f"failed: {failed[:5]}")


# --- S8/S9: fit staleness + history (deployed, sentinel user) ------------------

def _user_db():
    from google.cloud import firestore
    return firestore.Client(project='college-counselling-478115')


def _cleanup_sentinel_user(db):
    user_ref = db.collection('users').document(SENTINEL_USER)
    for fit in user_ref.collection('college_fits').stream():
        for h in fit.reference.collection('history').stream():
            h.reference.delete()
        fit.reference.delete()
    for item in user_ref.collection('college_list').stream():
        item.reference.delete()
    user_ref.delete()


def s8_s9_fit_staleness():
    import requests
    db = _user_db()
    user_ref = db.collection('users').document(SENTINEL_USER)
    try:
        # Stale fits: kb_data_year 2025, old inputs chosen to force a
        # material tier-crossing (10% HIGHLY_SELECTIVE → current <8% ULTRA).
        stale_fit = {
            'university_id': 'princeton_university',
            'university_name': 'Princeton University',
            'fit_category': 'REACH', 'match_percentage': 40,
            'kb_data_year': 2025,
            'kb_last_updated': '2026-01-01T00:00:00+00:00',
            'input_snapshot': {'acceptance_rate': 10.0, 'test_policy': 'old policy',
                               'deadlines_hash': 'stale', 'total_coa': 70000},
            'computed_at': '2026-01-01T00:00:00',
        }
        user_ref.collection('college_fits').document('princeton_university').set(stale_fit)
        applied_fit = dict(stale_fit, university_id='stanford_university',
                           university_name='Stanford University')
        user_ref.collection('college_fits').document('stanford_university').set(applied_fit)
        user_ref.collection('college_list').document('princeton_university').set(
            {'university_id': 'princeton_university', 'status': 'planning'})
        user_ref.collection('college_list').document('stanford_university').set(
            {'university_id': 'stanford_university', 'status': 'applied'})

        resp = requests.post(f"{PM_URL}/check-fit-recomputation",
                             json={'user_email': SENTINEL_USER}, timeout=60).json()
        updates = {u['university_id']: u for u in resp.get('kb_updates', [])}
        pri, stan = updates.get('princeton_university'), updates.get('stanford_university')

        checks = [
            ('both stale fits detected', pri is not None and stan is not None),
            ('years recorded', pri and pri['fit_kb_year'] == 2025 and pri['current_kb_year'] == 2026),
            ('tier-crossing rate is material',
             pri and any(c['field'] == 'acceptance_rate' and c['severity'] == 'material'
                         for c in pri['changes'])),
            ('projected shift from floor rules',
             pri and pri.get('projected_category_shift') == 'REACH → SUPER_REACH'),
            ('applied college nudge-suppressed', stan and stan.get('nudge_suppressed') is True),
            ('planning college not suppressed', pri and pri.get('nudge_suppressed') is False),
            ('suppressed entry keeps staleness data', stan and stan.get('changes')),
        ]

        empty = requests.post(f"{PM_URL}/check-fit-recomputation",
                              json={'user_email': '_harness_scenario_nobody@test.com'},
                              timeout=60).json()
        checks.append(('no-fits user → empty kb_updates',
                       empty.get('success') and empty.get('kb_updates') == []))

        failed = [n for n, ok in checks if not ok]
        record('S8', 'Fit staleness detection + suppression (deployed)',
               not failed, f"{len(checks)} checks" + (f"; FAILED: {failed}" if failed else ''))

        # S9: saving a new fit archives the old one under its kb year.
        new_fit = {'fit_category': 'SUPER_REACH', 'match_percentage': 22,
                   'kb_data_year': 2026, 'university_id': 'princeton_university'}
        save = requests.post(f"{PM_URL}/save-fit-analysis",
                             json={'user_email': SENTINEL_USER,
                                   'university_id': 'princeton_university',
                                   'fit_analysis': new_fit}, timeout=60).json()
        hist = requests.post(f"{PM_URL}/get-fit-history",
                             json={'user_email': SENTINEL_USER,
                                   'university_id': 'princeton_university'}, timeout=60).json()
        entries = hist.get('history', [])
        ok9 = (save.get('success') and hist.get('success')
               and any(e.get('history_key') == '2025' and e.get('fit_category') == 'REACH'
                       for e in entries))
        record('S9', 'Fit history archival (deployed)', bool(ok9),
               f"replaced fit archived under 2025; history={[e.get('history_key') for e in entries]}")
    finally:
        _cleanup_sentinel_user(db)
        leftover = list(user_ref.collection('college_fits').stream())
        record('S8.cleanup', 'Sentinel user removed', not leftover and not user_ref.get().exists,
               'all sentinel docs deleted')


# --- S10: roadmap annotation (unit) ------------------------------------------

def s10_roadmap():
    rc, out = run([PY, '-m', 'pytest',
                   'tests/cloud_functions/counselor_agent/test_deadline_change_annotation.py', '-q'])
    tail = out.strip().splitlines()[-1] if out.strip() else ''
    record('S10', 'Roadmap deadline-change annotation (unit)', rc == 0, tail)


# --- S11: live QA monitoring ----------------------------------------------------

def s11_qa_runs():
    from google.cloud import firestore
    db = _user_db()
    runs = list(db.collection('qa_runs')
                .order_by('started_at', direction=firestore.Query.DESCENDING)
                .limit(1).stream())
    if not runs:
        return record('S11', 'Live QA synthetic monitoring', False, 'no runs found')
    d = runs[0].to_dict()
    scen = d.get('scenarios') or []
    fails = [s.get('scenario_id') for s in scen if isinstance(s, dict) and not s.get('passed')]
    record('S11', 'Live QA synthetic monitoring', bool(scen) and not fails,
           f"latest run {runs[0].id[:28]}: {len(scen)} scenarios, failures: {fails or 'none'}")


# --- S12: deployed health -------------------------------------------------------

def s12_health():
    import requests
    h = requests.get(f"{KB_URL}/health", timeout=30).json()
    ok = h.get('success') and h.get('status', {}).get('firestore')
    record('S12', 'Deployed function health', bool(ok), 'KB /health: firestore connected')


# --- report -------------------------------------------------------------------

def write_report(skip_live):
    now = datetime.now(timezone.utc)
    date = now.strftime('%Y-%m-%d')
    passed = sum(1 for r in results if r['status'] == 'PASS')
    failed = [r for r in results if r['status'] == 'FAIL']
    lines = [
        f"# Scenario run — {date}",
        '',
        f"- Executed: {now.strftime('%Y-%m-%d %H:%M UTC')}",
        f"- Commit: {subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=REPO, capture_output=True, text=True).stdout.strip()}",
        f"- Mode: {'unit/build only (--skip-live)' if skip_live else 'full (unit + live production)'}",
        f"- Result: **{passed}/{len(results)} PASS**" + ('' if not failed else f" — FAILURES: {[r['id'] for r in failed]}"),
        '',
        '| # | Scenario | Status | Detail |',
        '|---|---|---|---|',
    ]
    for r in results:
        lines.append(f"| {r['id']} | {r['name']} | {r['status']} | {r['detail']} |")
    lines += ['', 'Scenario definitions: [`system-scenarios.md`](system-scenarios.md).', '']
    out = REPO / 'docs' / 'scenarios' / f'SCENARIO-RUN-{date}.md'
    out.write_text('\n'.join(lines))
    print(f"\nReport: {out.relative_to(REPO)}  ({passed}/{len(results)} PASS)")
    return not failed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--skip-live', action='store_true',
                        help='unit/build gates only; no production calls')
    args = parser.parse_args()

    s1_backend()
    s2_frontend()
    if not args.skip_live:
        s3_lifecycle()
        s4_read_apis()
        s5_validation_gate()
        s6_data_integrity()
        s7_corpus()
        s8_s9_fit_staleness()
    s10_roadmap()
    if not args.skip_live:
        s11_qa_runs()
        s12_health()

    sys.exit(0 if write_report(args.skip_live) else 1)


if __name__ == '__main__':
    main()
