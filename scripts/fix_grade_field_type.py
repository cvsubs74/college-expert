"""
One-shot Firestore migration: coerce integer `grade` values to string strings
in all live student profiles.

Background (issue #130)
-----------------------
profile_extraction.py's LLM schema previously described `grade` as
"integer 9-12", so profiles extracted from PDF/DOCX documents were stored
as e.g. `grade: 12` (int) in Firestore.  The GuidedInterview and
ProfileBuilder write paths always used string literals (`'12'`).  This
inconsistency caused the #123 crash when a consumer called `.trim()` on
a number.

The extraction schema and post-extraction coercion were fixed in PR #143
(issue #130).  This script back-fills existing documents so no live
profile retains an integer grade.

Idempotency
-----------
`normalize_grade` is a pure function; calling it on an already-string value
is a no-op.  The script skips documents whose grade field is already a
string (or None/missing), so re-running it is safe.

Usage
-----
    python scripts/fix_grade_field_type.py [--dry-run]

    --dry-run   Print what would change without writing to Firestore.

GCP credentials must be available in the environment (e.g. via
`GOOGLE_APPLICATION_CREDENTIALS`) and the caller must have write access to
the `college-counselling-478115` project.
"""

import argparse
import sys


# ---------------------------------------------------------------------------
# Pure helper — importable by tests without touching Firestore.
# ---------------------------------------------------------------------------

def normalize_grade(value):
    """
    Coerce a grade value to str, or return None if value is None.

    Examples:
        normalize_grade(12)    -> '12'
        normalize_grade('12')  -> '12'
        normalize_grade(None)  -> None
        normalize_grade('11')  -> '11'   (idempotent)
    """
    if value is None:
        return None
    return str(value)


# ---------------------------------------------------------------------------
# Migration logic — only runs when executed as a script.
# ---------------------------------------------------------------------------

def _run_migration(dry_run: bool) -> None:
    try:
        from google.cloud import firestore
    except ImportError:
        print("ERROR: google-cloud-firestore is not installed.", file=sys.stderr)
        sys.exit(1)

    db = firestore.Client(project='college-counselling-478115')

    users_ref = db.collection('users')
    users = users_ref.stream()

    updated = 0
    skipped = 0
    errors = 0

    for user_doc in users:
        uid = user_doc.id
        try:
            profile_ref = users_ref.document(uid).collection('profile').document('data')
            profile_snap = profile_ref.get()

            if not profile_snap.exists:
                skipped += 1
                continue

            data = profile_snap.to_dict()
            grade_val = data.get('grade')

            # Already correct type or absent — skip.
            if grade_val is None or isinstance(grade_val, str):
                skipped += 1
                continue

            normalized = normalize_grade(grade_val)
            print(f"  uid={uid}: grade {grade_val!r} ({type(grade_val).__name__}) -> {normalized!r}")

            if not dry_run:
                profile_ref.update({'grade': normalized})

            updated += 1

        except Exception as e:
            print(f"  uid={uid}: ERROR — {e}", file=sys.stderr)
            errors += 1

    action = "Would update" if dry_run else "Updated"
    print(f"\n{action} {updated} profile(s). Skipped {skipped}. Errors {errors}.")
    if dry_run:
        print("Dry-run mode: no writes performed. Re-run without --dry-run to apply.")
    if errors:
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Coerce integer grade fields to strings in Firestore.")
    parser.add_argument('--dry-run', action='store_true', help="Print changes without writing.")
    args = parser.parse_args()

    print(f"fix_grade_field_type.py — dry_run={args.dry_run}")
    _run_migration(dry_run=args.dry_run)


if __name__ == '__main__':
    main()
