#!/usr/bin/env python3
"""Backfill the global major catalog (#303) from all stored university profiles.

The catalog (`major_catalog/current` in the KB's Firestore) is the union of
every major offered across all universities, keyed by a normalized name — the
candidate universe the school-agnostic Major Map draws from. `ingest_university`
maintains it incrementally going forward; this script is the full-rebuild
source of truth (run once now, and any time you suspect drift).

Two modes:
  # Rebuild directly against Firestore (default; needs GOOGLE creds + the
  # KB package importable — run from the KB function dir or with it on PYTHONPATH)
  python3 scripts/build_major_catalog.py --write

  # Offline preview from the local collector corpus (no Firestore) — sizes
  # the catalog and prints the top majors without writing anything
  python3 scripts/build_major_catalog.py --from-corpus --top 30

Account/project pin (Firestore mode): the KB Firestore client uses ADC; ensure
`gcloud auth application-default login` is the college-counselling project.
"""
import argparse
import glob
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KB_DIR = ROOT / 'cloud_functions' / 'knowledge_base_manager_universities_v2'
sys.path.insert(0, str(KB_DIR))

import major_catalog  # noqa: E402  (from KB_DIR)


def _corpus_pairs():
    dirs = ['research', 'research_2026', 'verified_samples']
    base = ROOT / 'agents' / 'university_profile_collector'
    for d in dirs:
        for f in glob.glob(str(base / d / '*.json')):
            try:
                profile = json.load(open(f))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            uid = profile.get('_id') or Path(f).stem
            yield uid, profile


def _firestore_pairs():
    from firestore_db import get_db  # noqa: E402
    db = get_db()
    for doc in db.collection.stream():
        data = doc.to_dict() or {}
        yield doc.id, (data.get('profile') or {})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--from-corpus', action='store_true',
                    help='build from the local collector corpus (no Firestore)')
    ap.add_argument('--write', action='store_true',
                    help='write the rebuilt catalog to Firestore')
    ap.add_argument('--top', type=int, default=25, help='how many majors to preview')
    args = ap.parse_args()

    pairs = _corpus_pairs() if args.from_corpus else _firestore_pairs()
    catalog = major_catalog.build_catalog(pairs)
    view = major_catalog.catalog_view(catalog, limit=args.top)

    print(f"universities contributing: {catalog['university_count']}")
    print(f"distinct majors: {view['total']}")
    print(f"top {args.top} by # schools offering:")
    for row in view['majors']:
        print(f"  {row['offered_count']:4}  {row['name']}")

    if args.write:
        if args.from_corpus:
            print("\nrefusing to --write a corpus-built catalog "
                  "(run without --from-corpus to rebuild from live Firestore)",
                  file=sys.stderr)
            return 2
        from firestore_db import get_db
        ok = get_db().save_major_catalog(catalog)
        print(f"\nwrote major_catalog/current: {'OK' if ok else 'FAILED'}")
        return 0 if ok else 1
    print("\n(dry run — pass --write to persist)")
    return 0


if __name__ == '__main__':
    sys.exit(main())
