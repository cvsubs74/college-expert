#!/usr/bin/env python3
"""
Persist + validate a profile produced by kb_collect_workflow.js.

The Claude Workflow returns {profile, _provenance, _trust_report, ...}. This
helper takes that JSON (the whole return object OR just the profile), validates
it against BOTH the Pydantic model (model.py) and the ingest-boundary check
(knowledge_base_manager_universities_v2/versioning.validate_profile), writes the
profile to research/<_id>.json and the provenance sidecar to
research/_provenance/<_id>.json, and prints the trust report.

Usage:
    python save_profile.py result.json --year 2024
    cat result.json | python save_profile.py --year 2024
Then ingest:
    python scripts/ingest_universities.py --file research/<id>.json --year 2024
"""
import argparse, json, sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "cloud_functions" / "knowledge_base_manager_universities_v2"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("infile", nargs="?", help="workflow result JSON (default: stdin)")
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--dry-run", action="store_true", help="validate only, do not write")
    args = ap.parse_args()

    raw = Path(args.infile).read_text() if args.infile else sys.stdin.read()
    obj = json.loads(raw)
    profile = obj.get("profile", obj)            # accept whole return or bare profile
    provenance = obj.get("_provenance")
    trust = obj.get("_trust_report")

    # --- 1. Pydantic shape (model.py) ---
    pyd_ok, pyd_err = True, ""
    try:
        from model import UniversityProfile
        UniversityProfile.model_validate(profile)
    except ImportError:
        pyd_err = "model.py not importable (skipped)"
    except Exception as e:
        pyd_ok = False
        if hasattr(e, "errors"):
            pyd_err = "; ".join(f"{'.'.join(str(l) for l in er['loc'])}: {er['msg']}" for er in e.errors()[:6])
        else:
            pyd_err = str(e)[:300]

    # --- 2. Ingest-boundary check (server) ---
    ing_errors, ing_warnings = [], []
    try:
        from versioning import validate_profile
        ing_errors, ing_warnings = validate_profile(profile, args.year)
    except ImportError:
        ing_warnings = ["versioning.py not importable (skipped)"]

    print(f"\n=== {profile.get('metadata', {}).get('official_name', profile.get('_id'))} (cycle {args.year}) ===")
    print(f"Pydantic model.py : {'PASS' if pyd_ok else 'FAIL — ' + pyd_err}")
    print(f"Ingest validate   : {'PASS' if not ing_errors else 'FAIL'}")
    for e in ing_errors:   print(f"   ERROR  {e}")
    for w in ing_warnings: print(f"   warn   {w}")

    if trust:
        d = trust.get("deterministic_fields", {})
        print(f"\nTrust: {d.get('published')}/{d.get('total')} deterministic fields published, "
              f"{d.get('held_null')} held null. acceptance={trust.get('acceptance_rate_published')}, "
              f"IPEDS={trust.get('ipeds_unitid')}, CDS={trust.get('cds_edition_used')}")
        v = trust.get("verification", {})
        print(f"   corroborated={v.get('corroborated')} canonical_single={v.get('canonical_single')} "
              f"nulled(conflict/invariant)={v.get('conflict_nulled')} unverified_nulled={v.get('unverified_nulled')}")

    if args.dry_run:
        print("\n(dry-run — nothing written)")
        return 0 if (pyd_ok and not ing_errors) else 1

    out_dir = HERE / "research"
    prov_dir = out_dir / "_provenance"
    out_dir.mkdir(exist_ok=True)
    prov_dir.mkdir(exist_ok=True)
    pid = profile["_id"]
    (out_dir / f"{pid}.json").write_text(json.dumps(profile, indent=2))
    if provenance:
        (prov_dir / f"{pid}.json").write_text(json.dumps({"trust_report": trust, "provenance": provenance}, indent=2))
    print(f"\nWrote research/{pid}.json" + (f" + _provenance/{pid}.json" if provenance else ""))
    print(f"Ingest: python scripts/ingest_universities.py --file agents/university_profile_collector/research/{pid}.json --year {args.year}")
    return 0 if (pyd_ok and not ing_errors) else 1


if __name__ == "__main__":
    sys.exit(main())
