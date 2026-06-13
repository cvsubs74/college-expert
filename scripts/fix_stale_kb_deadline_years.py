#!/usr/bin/env python3
"""
KB-wide sweep: normalize stale application-deadline (and ISO scholarship
deadline_date) YEARS to the correct admissions cycle, across every university.

The bug class this fixes: a deadline stored with a past-cycle year — e.g. a
2026-27 doc (data_year=2026) holding "2024-11-30" for Regular Decision. The
month/day are trusted; only the stale YEAR is corrected to the cycle window:

    2026-27 cycle (data_year=2026) = Fall 2026 entry
      → fall deadlines (Aug–Dec) belong to 2025
      → winter/spring deadlines (Jan–Jul) belong to 2026

This is deterministic and reviewable — it never invents a date, only shifts a
date that is already present onto its own cycle. Docs without a data_year
(unversioned) are skipped. Idempotent: a correct date is left untouched.

    GOOGLE_CLOUD_PROJECT=college-counselling-478115 \
        .venv/bin/python scripts/fix_stale_kb_deadline_years.py --dry-run
    GOOGLE_CLOUD_PROJECT=college-counselling-478115 \
        .venv/bin/python scripts/fix_stale_kb_deadline_years.py --apply
"""
import argparse
import copy
import os
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT = "college-counselling-478115"


def cycle_year(month, data_year):
    """The calendar year a deadline in `month` belongs to for `data_year`'s
    cycle. Fall (Aug–Dec) → data_year-1; winter/spring (Jan–Jul) → data_year."""
    return data_year - 1 if month >= 8 else data_year


def fix_iso_year(date_str, data_year):
    """Return a year-corrected ISO date, or None if unparseable or already
    correct for the cycle."""
    if not isinstance(date_str, str) or len(date_str) < 10:
        return None
    try:
        d = datetime.strptime(date_str[:10], "%Y-%m-%d")
    except ValueError:
        return None
    cy = cycle_year(d.month, data_year)
    if d.year == cy:
        return None
    try:
        return d.replace(year=cy).strftime("%Y-%m-%d")
    except ValueError:  # Feb 29 → Feb 28 in a non-leap cycle year
        return d.replace(month=2, day=28, year=cy).strftime("%Y-%m-%d")


def normalize_doc(doc):
    """Return (new_doc, changes) with stale deadline years corrected. Pure."""
    new_doc = copy.deepcopy(doc)
    changes = []
    dy = new_doc.get("data_year")
    if not isinstance(dy, int):
        return new_doc, changes  # unversioned — don't touch
    profile = new_doc.get("profile") or {}

    for dl in (profile.get("application_process") or {}).get("application_deadlines") or []:
        fixed = fix_iso_year(dl.get("date"), dy)
        if fixed:
            changes.append(f"app_deadline[{dl.get('plan_type', '?')}]: {dl.get('date')} -> {fixed}")
            dl["date"] = fixed

    for s in (profile.get("financials") or {}).get("scholarships") or []:
        fixed = fix_iso_year(s.get("deadline_date"), dy)
        if fixed:
            changes.append(f"scholarship[{s.get('name')!r}].deadline_date: {s.get('deadline_date')} -> {fixed}")
            s["deadline_date"] = fixed

    return new_doc, changes


def _kb_db():
    sys.path.insert(0, str(REPO / "cloud_functions" / "knowledge_base_manager_universities_v2"))
    from firestore_db import FirestoreDB
    return FirestoreDB()


def sweep(db, dry_run=True):
    scanned = stale_docs = stale_fields = skipped_unversioned = 0
    for snap in db.collection.stream():
        scanned += 1
        doc = snap.to_dict() or {}
        uid = snap.id
        if not isinstance(doc.get("data_year"), int):
            skipped_unversioned += 1
            continue
        new_doc, changes = normalize_doc(doc)
        if not changes:
            continue
        stale_docs += 1
        stale_fields += len(changes)
        print(f"\n=== {uid} (data_year={doc['data_year']}) — {len(changes)} stale ===")
        for c in changes:
            print(f"   {c}")
        if not dry_run:
            res = db.save_university(uid, new_doc, year=doc["data_year"])
            print(f"   -> saved (promoted={res.get('promoted')})")
    print(
        f"\n{'DRY-RUN' if dry_run else 'APPLIED'}: scanned {scanned}, "
        f"{stale_docs} schools with stale years ({stale_fields} fields); "
        f"{skipped_unversioned} unversioned docs skipped."
    )
    return stale_fields


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--dry-run", action="store_true", help="report stale years, write nothing (default)")
    g.add_argument("--apply", action="store_true", help="correct the stale years in the KB")
    ap.add_argument("--project", default=os.environ.get("GOOGLE_CLOUD_PROJECT", DEFAULT_PROJECT))
    args = ap.parse_args()

    os.environ["GOOGLE_CLOUD_PROJECT"] = args.project  # never write to the ADC default project
    print(f"KB project: {args.project}")
    sweep(_kb_db(), dry_run=not args.apply)


if __name__ == "__main__":
    main()
