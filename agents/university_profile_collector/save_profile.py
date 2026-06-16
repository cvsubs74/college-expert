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
    ap.add_argument("--out-dir", default="research", help="directory to write the profile into (default: research)")
    ap.add_argument("--dry-run", action="store_true", help="validate only, do not write")
    args = ap.parse_args()

    raw = Path(args.infile).read_text() if args.infile else sys.stdin.read()
    obj = json.loads(raw)
    profile = obj.get("profile", obj)            # accept whole return or bare profile
    provenance = obj.get("_provenance")
    trust = obj.get("_trust_report")
    source_ledger = obj.get("_source_ledger")

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
        if source_ledger is not None:
            print(f"   sources: {trust.get('total_sources_consulted', len(source_ledger))} URLs consulted, "
                  f"{trust.get('sources_backing_published_values')} backed a published value")

    if args.dry_run:
        print("\n(dry-run — nothing written)")
        return 0 if (pyd_ok and not ing_errors) else 1

    out_dir = (HERE / args.out_dir) if not Path(args.out_dir).is_absolute() else Path(args.out_dir)
    prov_dir = out_dir / "_provenance"
    out_dir.mkdir(exist_ok=True)
    prov_dir.mkdir(exist_ok=True)
    pid = profile["_id"]
    rel = args.out_dir.rstrip("/")
    (out_dir / f"{pid}.json").write_text(json.dumps(profile, indent=2))
    wrote = [f"{rel}/{pid}.json"]
    if provenance or source_ledger:
        (prov_dir / f"{pid}.json").write_text(json.dumps(
            {"trust_report": trust, "provenance": provenance, "source_ledger": source_ledger}, indent=2))
        wrote.append(f"{rel}/_provenance/{pid}.json")
    if source_ledger is not None:
        md = render_sources_md(profile, trust, source_ledger)
        (out_dir / f"{pid}.sources.md").write_text(md)
        wrote.append(f"{rel}/{pid}.sources.md")
    print(f"\nWrote " + ", ".join(wrote))
    print(f"Ingest: python scripts/ingest_universities.py --file agents/university_profile_collector/{rel}/{pid}.json --year {args.year}")
    return 0 if (pyd_ok and not ing_errors) else 1


def render_sources_md(profile, trust, ledger):
    """Human-readable transparency report: every URL consulted, grouped by role."""
    name = profile.get("metadata", {}).get("official_name", profile.get("_id"))
    backed = [s for s in ledger if s.get("backed_published_fields")]
    used_section = [s for s in ledger if not s.get("backed_published_fields") and s.get("used")]
    rejected = [s for s in ledger if not s.get("used")]
    lines = [f"# Sources consulted — {name} (cycle {trust.get('cycle') if trust else ''})", ""]
    lines.append(f"Every URL the collector searched or fetched, for full transparency — **{len(ledger)} distinct URLs**: "
                 f"{len(backed)} backed a published deterministic value, {len(used_section)} informed a section, "
                 f"{len(rejected)} were consulted but **not used** (each with the reason).")
    lines.append("")

    lines.append(f"## 1. Backed a published deterministic value ({len(backed)})")
    for s in backed:
        lines.append(f"- <{s['url']}>")
        lines.append(f"    - **fields:** {', '.join(s['backed_published_fields'])}")
        lines.append(f"    - roles: {', '.join(s.get('roles', []))}")
        for n in s.get("notes", [])[:2]:
            if n:
                lines.append(f"    - “{n[:260]}”")
    lines.append("")

    lines.append(f"## 2. Informed an official/community section ({len(used_section)})")
    for s in used_section:
        note = next((n for n in s.get("notes", []) if n), "")
        lines.append(f"- <{s['url']}> — {', '.join(s.get('roles', []))}" + (f"\n    - “{note[:240]}”" if note else ""))
    lines.append("")

    lines.append(f"## 3. Consulted but NOT used — with reason ({len(rejected)})")
    for s in rejected:
        note = next((n for n in s.get("notes", []) if n), "")
        lines.append(f"- <{s['url']}> — {', '.join(s.get('roles', []))}" + (f" — {note[:200]}" if note else ""))
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
