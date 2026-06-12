#!/usr/bin/env python3
"""
Canonical ingestion CLI for the year-versioned university knowledge base.

Takes collector JSONs (agents/university_profile_collector/research/*.json)
and POSTs them to knowledge_base_manager_universities_v2, filing each under
an admission cycle year (ADR 0002 — harness/decisions/0002-*.md). The KB
keeps one snapshot per year; re-running for the same year refreshes that
year only, and ingesting a newer year becomes the serving "current" data
without destroying prior years.

Usage:
    # Refresh the whole KB for the current cycle
    python scripts/ingest_universities.py --dir agents/university_profile_collector/research

    # Ingest one university for an explicit cycle year
    python scripts/ingest_universities.py --file research/stanford_university.json --year 2026

    # Validate without writing
    python scripts/ingest_universities.py --dir research/ --dry-run

    # Subset by university id
    python scripts/ingest_universities.py --dir research/ --only mit,stanford_university
"""
import argparse
import json
import sys
from pathlib import Path

import requests

# Make the cloud function's validation importable so the CLI pre-checks
# exactly what the server will enforce.
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / 'cloud_functions' / 'knowledge_base_manager_universities_v2'))
from versioning import (  # noqa: E402
    coerce_year, merge_cycle_refresh, normalize_percentages, validate_profile,
)

DEFAULT_URL = "https://knowledge-base-manager-universities-v2-pfnwjfp26a-ue.a.run.app"


def iter_profiles(args):
    if args.file:
        paths = [Path(args.file)]
    else:
        paths = sorted(Path(args.dir).glob('*.json'))
    only = set(args.only.split(',')) if args.only else None
    for path in paths:
        try:
            profile = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError) as e:
            yield path, None, f"unreadable JSON: {e}"
            continue
        if only and profile.get('_id') not in only:
            continue
        yield path, profile, None


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--file', help='Single collector JSON to ingest')
    source.add_argument('--dir', help='Directory of collector JSONs')
    parser.add_argument('--year', type=int, default=None,
                        help='Admission cycle year (default: derived from today, ADR 0002)')
    parser.add_argument('--url', default=DEFAULT_URL, help='KB v2 function URL')
    parser.add_argument('--only', help='Comma-separated university _ids to include')
    parser.add_argument('--dry-run', action='store_true', help='Validate only; write nothing')
    parser.add_argument('--merge-with-current', action='store_true',
                        help='Yearly-refresh mode: overlay cycle-sensitive sections '
                             '(current admissions status, deadlines, rank, costs) from '
                             'the fresh JSON onto the KB\'s current rich profile, so a '
                             'thinner fresh collection never degrades durable data')
    args = parser.parse_args()

    year = coerce_year(args.year)
    print(f"Ingesting for admission cycle year {year} → {args.url}"
          + (" [DRY RUN]" if args.dry_run else ""))

    ok, failed = 0, 0
    for path, profile, read_error in iter_profiles(args):
        if read_error:
            print(f"  FAIL  {path.name}: {read_error}")
            failed += 1
            continue

        fixed = normalize_percentages(profile)
        if fixed:
            print(f"  norm  {path.name}: {fixed} fraction-style percent fields → percents")

        # Validate the FRESH collection before any merge: a fragment file
        # (broken extraction) merged onto the rich base looks like a
        # successful ingest but silently delivers no refresh at all.
        fresh_errors, _ = validate_profile(profile, year)
        if fresh_errors:
            print(f"  FAIL  {path.name}: fresh collection invalid (re-collect): "
                  f"{'; '.join(fresh_errors)}")
            failed += 1
            continue

        if args.merge_with_current:
            try:
                resp = requests.get(args.url, params={"id": profile.get('_id')}, timeout=60)
                current = (resp.json().get('university') or {}).get('profile') if resp.ok else None
            except (requests.RequestException, ValueError):
                current = None
            if current:
                profile = merge_cycle_refresh(current, profile)
                # The base may carry fraction-style fields from a prior bad
                # ingest — normalize the merged result too.
                normalize_percentages(profile)
                print(f"  merge {path.name}: cycle-sensitive sections refreshed onto current profile")
            else:
                print(f"  merge {path.name}: no current profile in KB — ingesting fresh as-is")

        errors, warnings = validate_profile(profile, year)
        if errors:
            print(f"  FAIL  {path.name}: {'; '.join(errors)}")
            failed += 1
            continue
        for w in warnings:
            print(f"  warn  {path.name}: {w}")

        if args.dry_run:
            print(f"  ok    {path.name} (validated, not written)")
            ok += 1
            continue

        try:
            resp = requests.post(args.url, json={"profile": profile, "year": year}, timeout=120)
            body = resp.json()
        except (requests.RequestException, ValueError) as e:
            print(f"  FAIL  {path.name}: request failed: {e}")
            failed += 1
            continue

        if resp.status_code == 200 and body.get('success'):
            if 'year' not in body:
                # Old pre-versioning function deployed: it just overwrote the
                # main doc with no snapshot. Stop before doing more damage.
                print(f"  FAIL  {path.name}: server doesn't support versioning yet "
                      f"(deploy knowledge-universities-v2 first) — aborting")
                failed += 1
                break
            promo = "current" if body.get('promoted_to_current') else "archived"
            print(f"  ok    {path.name} → year {body.get('year')} [{promo}] "
                  f"years={body.get('available_years')}")
            ok += 1
        else:
            print(f"  FAIL  {path.name}: HTTP {resp.status_code}: "
                  f"{body.get('error', resp.text[:200])}")
            failed += 1

    print(f"\nDone: {ok} ok, {failed} failed (cycle year {year})")
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
