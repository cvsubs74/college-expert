#!/usr/bin/env python3
"""Audit stored KB docs for values corrupted by the old percent normalizer (#289).

Before this fix, `normalize_percentages` multiplied ANY 0<v<1 float on a
percent-like key by 100 at ingest — including fields with genuine sub-1%
values (transfer_acceptance_rate, waitlist_admit_rate, demographic slices).
This script finds the damage. It is REPORT-ONLY: it never writes.

Detection is source-anchored AND context-classified. A sub-1 source value is
ambiguous by itself (Auburn's transfer 0.509 was a FRACTION meaning 50.9%;
Harvard's 0.8 was a real 0.8%), so each stored ×100 conversion is classified:

  likely_correct   — provable fraction context: share group summing to ~1.0,
                     or a singleton rate at a school whose overall acceptance
                     rate is high (>=20%: no such school has a sub-1% transfer
                     admit rate).
  likely_corrupted — provable percent context: the value sits in a same-unit
                     series with >1 members (CMU waitlist [1.5, 0.9, 8.3]), or
                     a sub-1 rate at a hyper-selective school (overall <10%,
                     where genuine sub-1% rates occur — Harvard).
  ambiguous        — neither test decides; listed for manual review.

Usage:
  # offline: corpus-only scan (no Firestore) — lists at-risk source values
  python3 scripts/audit_percent_corruption.py --offline

  # full audit against the live KB (uses the service HTTP API; read-only)
  python3 scripts/audit_percent_corruption.py

Remediation plan (documented per #289, not executed here):
  corrupted values are fixed by re-ingesting the affected universities from
  their corpus files with the fixed normalizer (`scripts/ingest_universities.py
  --only <ids> --merge-with-current`), which overwrites only the same-cycle
  snapshot (idempotent per ADR 0002). Version snapshots from other cycles that
  no corpus file covers are listed separately for manual review.
"""
import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS_DIRS = [
    ROOT / 'agents' / 'university_profile_collector' / 'research',
    ROOT / 'agents' / 'university_profile_collector' / 'research_2026',
    ROOT / 'agents' / 'university_profile_collector' / 'verified_samples',
]
KB_URL = 'https://knowledge-base-manager-universities-v2-pfnwjfp26a-ue.a.run.app'

# The keys the old normalizer corrupted (now in _PERCENT_KEY_EXCLUDE).
AT_RISK_KEYS = {
    'transfer_acceptance_rate', 'waitlist_admit_rate', 'waitlist_acceptance_rate',
    'waitlist_yield_rate', 'international_percentage', 'legacy_percentage',
    'first_gen_percentage', 'percentage',
}


def walk(obj, path=''):
    """Yield (dotted_path, key, value) for every leaf."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk(v, f'{path}.{k}' if path else k)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            yield from walk(item, f'{path}[{i}]')
    else:
        yield path, path.rsplit('.', 1)[-1].split('[')[0], obj


def at_risk_values(profile):
    """{path: value} for every at-risk key holding a number."""
    out = {}
    for path, key, value in walk(profile):
        if key in AT_RISK_KEYS and isinstance(value, (int, float)):
            out[path] = float(value)
    return out


def classify(src_profile, path, source):
    """likely_correct / likely_corrupted / ambiguous for one sub-1 source value."""
    key = path.rsplit('.', 1)[-1].split('[')[0]
    # Share groups summing to ~1.0 are provable fractions -> conversion correct.
    if key == 'percentage' and 'geographic_breakdown' in path:
        demo_path = path.split('.geographic_breakdown')[0]
        node = src_profile
        for part in demo_path.split('.'):
            node = node.get(part, {}) if isinstance(node, dict) else {}
        group = [g.get('percentage') for g in (node.get('geographic_breakdown') or [])
                 if isinstance(g, dict) and isinstance(g.get('percentage'), (int, float))]
        if len(group) >= 2 and 0.95 <= sum(group) <= 1.05:
            return 'likely_correct'
        return 'ambiguous'
    # Same-unit series with >1 members proves percents -> conversion corrupted.
    if key in ('waitlist_admit_rate', 'waitlist_acceptance_rate', 'waitlist_yield_rate'):
        trends = ((src_profile.get('admissions_data') or {}).get('longitudinal_trends') or [])
        series = [(t.get('waitlist_stats') or {}).get(key) for t in trends
                  if isinstance(t, dict) and isinstance(t.get('waitlist_stats'), dict)]
        series = [v for v in series if isinstance(v, (int, float))]
        if any(v > 1 for v in series) and any(0 < v < 1 for v in series):
            return 'likely_corrupted'
        return 'ambiguous'
    # Rare-event rate at a school selective enough for genuine sub-1% values.
    if key in ('transfer_acceptance_rate', 'international_percentage',
               'legacy_percentage', 'first_gen_percentage'):
        overall = ((src_profile.get('admissions_data') or {})
                   .get('current_status') or {}).get('overall_acceptance_rate')
        if isinstance(overall, (int, float)):
            if overall >= 20:
                return 'likely_correct'      # 0.x was a fraction at an open school
            if 1 <= overall < 10:
                return 'likely_corrupted'    # genuine sub-1% plausible (Harvard)
        return 'ambiguous'
    return 'ambiguous'


def load_corpus():
    """{university_id: {path: value}} from every local corpus file (later
    dirs override earlier on id collision — verified_samples wins)."""
    corpus = {}
    for d in CORPUS_DIRS:
        if not d.is_dir():
            continue
        for f in sorted(d.glob('*.json')):
            try:
                profile = json.loads(f.read_text())
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            uid = profile.get('_id') or f.stem
            corpus[uid] = {'file': str(f.relative_to(ROOT)),
                           'values': at_risk_values(profile)}
    return corpus


def fetch_stored(uid):
    """[(label, profile)] for the main doc + each version snapshot."""
    docs = []
    base = f'{KB_URL}?id={urllib.parse.quote(uid)}'
    try:
        with urllib.request.urlopen(base, timeout=30) as r:
            data = json.load(r)
        uni = data.get('university') or {}
        if data.get('success') and uni.get('profile'):
            docs.append((f"main (data_year={uni.get('data_year')})", uni['profile']))
            for year in (uni.get('available_years') or []):
                if year == uni.get('data_year'):
                    continue
                with urllib.request.urlopen(f'{base}&year={year}', timeout=30) as r2:
                    d2 = json.load(r2)
                if d2.get('success') and (d2.get('university') or {}).get('profile'):
                    docs.append((f'versions/{year}', d2['university']['profile']))
    except Exception as e:  # noqa: BLE001 — audit must report, not crash
        print(f'  !! fetch failed for {uid}: {e}', file=sys.stderr)
    return docs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--offline', action='store_true',
                    help='corpus-only scan; no Firestore/HTTP reads')
    ap.add_argument('--only', nargs='*', help='limit to these university ids')
    args = ap.parse_args()

    corpus = load_corpus()
    ids = args.only or sorted(corpus)

    sub1_sources = {}   # uid -> {path: value}  (values the old rule WOULD corrupt)
    corrupted = []      # (uid, doc_label, path, stored, source)

    for uid in ids:
        entry = corpus.get(uid)
        if not entry:
            print(f'  -- no corpus file for {uid}; skipping', file=sys.stderr)
            continue
        sub1 = {p: v for p, v in entry['values'].items() if 0 < v < 1}
        if sub1:
            sub1_sources[uid] = sub1
        if args.offline or not sub1:
            continue
        src_profile = json.loads((ROOT / entry['file']).read_text())
        for label, stored_profile in fetch_stored(uid):
            stored_vals = at_risk_values(stored_profile)
            for path, source in sub1.items():
                stored = stored_vals.get(path)
                if stored is not None and abs(stored - source * 100) < 0.01:
                    corrupted.append((uid, label, path, stored, source,
                                      classify(src_profile, path, source)))

    print(f'\nCorpus files scanned: {len(corpus)}')
    print(f'Universities with genuine sub-1%% at-risk source values: {len(sub1_sources)}')
    for uid, vals in sorted(sub1_sources.items()):
        for path, v in sorted(vals.items()):
            print(f'  {uid}: {path} = {v}')

    if args.offline:
        print('\n(offline mode — stored docs not checked; rerun without '
              '--offline to detect actual corruption)')
        return 0

    print(f'\nStored ×100 conversions of sub-1 sources: {len(corrupted)}')
    for verdict in ('likely_corrupted', 'ambiguous', 'likely_correct'):
        rows = [c for c in corrupted if c[5] == verdict]
        print(f'\n  [{verdict}] {len(rows)}')
        for uid, label, path, stored, source, _ in rows:
            print(f'    {uid} [{label}]: {path} stored={stored} (source {source})')
    actionable = [c for c in corrupted if c[5] != 'likely_correct']
    if actionable:
        affected = sorted({uid for uid, *_ in actionable})
        print('\nRemediation: re-ingest with the fixed normalizer —')
        print(f"  python3 scripts/ingest_universities.py --dir agents/university_profile_collector/research "
              f"--merge-with-current --only {' '.join(affected)}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
