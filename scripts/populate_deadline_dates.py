#!/usr/bin/env python3
"""
Populate structured `deadline_date` on KB scholarships and refresh stale
application-deadline `date`s for the #191 pilot schools (Duke, Ohio State,
UCSD, USC), against the versioned university KB.

Idempotent read-modify-write of ONLY the deadline fields — never touches other
data, never re-researches. Re-running converges (the deadline values are
stable). `--dry-run` prints the diff and writes nothing.

    GOOGLE_CLOUD_PROJECT=college-counselling-478115 \
        .venv/bin/python scripts/populate_deadline_dates.py --dry-run
    GOOGLE_CLOUD_PROJECT=college-counselling-478115 \
        .venv/bin/python scripts/populate_deadline_dates.py --apply

The deadline values below were authored from the free-text `deadline` already
stored in each KB record, corrected to the upcoming 2026-27 cycle (Fall 2026
entry). `None` = no separate fixed date (Automatic / Varies / FAFSA-driven) —
the scholarship still gets the key so consumers can trust it (#191).
"""
import argparse
import copy
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT = "college-counselling-478115"

# {university_id: {
#    "application_deadlines": {existing_iso_date: corrected_iso_date},
#    "scholarships": {scholarship_name: deadline_date_iso_or_None},
# }}
PILOT = {
    "duke_university": {
        # ED 2025-11-01 / RD 2026-01-02 already correct for 2026-27.
        "application_deadlines": {},
        "scholarships": {
            "Robertson Scholars Leadership Program": "2026-01-15",
            "A.B. Duke Memorial Scholars Program": None,        # automatic
            "Karsh International Scholars Program": None,        # need-based, no separate app
            "Need-Based Financial Aid/Grants": None,            # FAFSA/CSS
            "B.N. Duke Scholars Program": None,                 # automatic
            "Alumni Endowed Scholarship": None,                 # automatic
        },
    },
    "ohio_state_university": {
        "application_deadlines": {
            "2024-11-01": "2025-11-01",   # Early Action
            "2025-01-15": "2026-01-15",   # Regular (year-shift; preserves KB month/day)
        },
        "scholarships": {
            "Stamps Eminence Scholarship Program": "2025-11-10",   # separate app
            "President's Ohio Scholarship Program": None,          # automatic
            "Land Grant Opportunity Scholarship": None,            # automatic
            "Morrill Scholarship Program (MSP)": "2025-11-01",     # competitive, Nov 1
            "Maximus, Provost, and Trustees Scholarships": None,   # automatic
            "Departmental and College Scholarships (via ScholarshipUniverse)": "2026-02-15",
        },
    },
    "university_of_california_san_diego": {
        "application_deadlines": {
            "2024-11-30": "2025-11-30",   # UC application (RD)
        },
        "scholarships": {
            "Regents Scholarship": None,                # automatic w/ UC app
            "Chancellor's Scholars Program": None,      # automatic
            "Triton Achievement Scholarship": None,     # automatic
            "Goins Alumni Scholarship Fund (formerly Black Alumni Scholarship Fund)": None,  # varies
            "Marc Canel and Jun Song Fellowship (Computer Science)": "2026-01-26",
            "Chen Del Pero Endowed Scholarship (Social Sciences)": "2026-04-02",
            "General Need-Based Grants": None,          # FAFSA/Cal Dream Act
        },
    },
    "university_of_southern_california": {
        "application_deadlines": {
            "2024-11-01": "2025-11-01",   # Early Action
            "2024-12-01": "2025-12-01",   # specific-major / scholarship deadline
            "2025-01-15": "2026-01-15",   # Regular Decision
        },
        "scholarships": {
            "USC Trustee Scholarship": None,        # automatic w/ admission app
            "USC Presidential Scholarship": None,   # automatic
            "USC National Merit Finalist Scholarship": None,
            "USC Dean's Scholarship": None,         # automatic
            "USC Departmental Scholarships": None,  # varies by department
            "USC Need-Based Grants": None,          # FAFSA/CSS
            "Town and Gown of USC Scholarship": "2025-11-15",  # separate app
        },
    },
}


def apply_to_doc(doc, mapping):
    """Return (new_doc, changes) applying the deadline mapping to a KB doc.

    Pure: deep-copies the doc, edits ONLY scholarship `deadline_date` (matched
    by name) and application-deadline `date` (matched by existing date), and
    records a human-readable change list. Never deletes or alters other fields.
    """
    new_doc = copy.deepcopy(doc)
    changes = []
    profile = new_doc.get("profile") or {}

    # Application deadlines: refresh stale `date` (match by existing value).
    appdl_map = mapping.get("application_deadlines") or {}
    for dl in (profile.get("application_process") or {}).get("application_deadlines") or []:
        old = dl.get("date")
        if old in appdl_map and appdl_map[old] != old:
            dl["date"] = appdl_map[old]
            changes.append(f"application_deadline[{dl.get('plan_type', '?')}]: {old} -> {appdl_map[old]}")

    # Scholarships: set structured deadline_date (match by name).
    sch_map = mapping.get("scholarships") or {}
    matched = set()
    for sch in (profile.get("financials") or {}).get("scholarships") or []:
        name = sch.get("name")
        if name in sch_map:
            matched.add(name)
            new_val = sch_map[name]
            if sch.get("deadline_date") != new_val or "deadline_date" not in sch:
                changes.append(f"scholarship[{name!r}].deadline_date: {sch.get('deadline_date')} -> {new_val}")
            sch["deadline_date"] = new_val
    for missing in set(sch_map) - matched:
        changes.append(f"WARNING: scholarship not found in KB (skipped): {missing!r}")

    return new_doc, changes


def _kb_db():
    sys.path.insert(0, str(REPO / "cloud_functions" / "knowledge_base_manager_universities_v2"))
    from firestore_db import FirestoreDB
    return FirestoreDB()


def migrate(db, dry_run=True):
    total_changes = 0
    for uid, mapping in PILOT.items():
        doc = db.get_university(uid)
        if not doc:
            print(f"[SKIP] {uid}: not found in KB")
            continue
        year = doc.get("data_year")
        if not year:
            print(f"[SKIP] {uid}: no data_year on current doc (won't touch unversioned doc)")
            continue
        new_doc, changes = apply_to_doc(doc, mapping)
        print(f"\n=== {uid} (data_year={year}) — {len(changes)} change(s) ===")
        for c in changes:
            print(f"   {c}")
        # A dry run shows the diff; an apply writes only when something changed.
        material = [c for c in changes if not c.startswith("WARNING")]
        total_changes += len(material)
        if not dry_run and material:
            res = db.save_university(uid, new_doc, year=year)
            print(f"   -> saved (promoted={res.get('promoted')}, years={res.get('available_years')})")
        elif not dry_run:
            print("   -> no material change; not written")
    print(f"\n{'DRY-RUN' if dry_run else 'APPLIED'}: {total_changes} field change(s) across {len(PILOT)} schools.")
    return total_changes


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--dry-run", action="store_true", help="show the diff, write nothing (default)")
    g.add_argument("--apply", action="store_true", help="write the changes to the KB")
    ap.add_argument("--project", default=os.environ.get("GOOGLE_CLOUD_PROJECT", DEFAULT_PROJECT))
    args = ap.parse_args()

    # Pin the project BEFORE the KB module builds its firestore.Client(). The
    # machine's ADC default is a different project — never write there.
    os.environ["GOOGLE_CLOUD_PROJECT"] = args.project
    print(f"KB project: {args.project}")

    db = _kb_db()
    migrate(db, dry_run=not args.apply)


if __name__ == "__main__":
    main()
