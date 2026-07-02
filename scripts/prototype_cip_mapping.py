#!/usr/bin/env python3
"""Prototype: map KB major names to 2020 CIP codes (#287, feeds #193/#280).

Why CIP codes: majors in the KB are free-text strings with no
cross-university identity (see cloud_functions/profile_manager_v2/
major_match.py). A CIP code per major unlocks cross-university major
identity and joins to IPEDS field-of-study data (per-major earnings,
completions) — reviving the dead College Scorecard anchor described in
agents/university_profile_collector/REDESIGN.md.

What this is: a stdlib-only prototype that measures how far an embedded
SEED TABLE (~80 common undergraduate majors -> 6-digit CIP 2020 codes,
TO BE REPLACED BY THE IPEDS CIP CROSSWALK) plus light normalization and
aliasing gets us on real collected profiles. Null-over-guess: a major
that does not clearly resolve to one CIP code stays UNMATCHED — no
fuzzy auto-binding (a wrong CIP identity is worse than none).

Usage:
    python scripts/prototype_cip_mapping.py             # the 3 verified samples
    python scripts/prototype_cip_mapping.py --file agents/university_profile_collector/research/mit.json

Observed coverage on the 3 verified samples (2026-07-01, seed table v1 —
143 majors + 65 aliases; the ask was ~60-80 rows, we overshot because CIP
families come in natural clusters and a row costs one line):
    purdue_university_main_campus              83/107 matched (77.6%)
    university_of_illinois_urbana_champaign    81/96  matched (84.4%)
    university_of_michigan_ann_arbor           47/52  matched (90.4%)
    TOTAL                                      211/255 matched (82.7%)
Caveat: table curation was informed by these same three schools, so treat
82.7% as "achievable with a curated seed", not generalization. Unmatched
are dominated by blended degrees (UIUC "CS + X"), school-specific program
brands (LEAPS, Explorers, Urban Technology) and narrow subfields — exactly
the tail the real IPEDS crosswalk (plus per-school overrides) is for.
"""
import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_SAMPLES_DIR = REPO / "agents" / "university_profile_collector" / "verified_samples"

# ---------------------------------------------------------------------------
# Seed table: normalized major name -> (CIP 2020 code, official CIP title).
# SEED TABLE, TO BE REPLACED BY THE IPEDS CIP CROSSWALK (nces.ed.gov/ipeds/cipcode).
# Codes are 6-digit CIP 2020. Curated for the most common undergraduate majors.
# ---------------------------------------------------------------------------
CIP_SEED = {
    # --- Engineering (14.xx) ---
    "aerospace engineering": ("14.0201", "Aerospace, Aeronautical, and Astronautical/Space Engineering, General"),
    "agricultural engineering": ("14.0301", "Agricultural Engineering"),
    "biological engineering": ("14.4501", "Biological/Biosystems Engineering"),
    "biomedical engineering": ("14.0501", "Bioengineering and Biomedical Engineering"),
    "bioengineering": ("14.0501", "Bioengineering and Biomedical Engineering"),
    "chemical engineering": ("14.0701", "Chemical Engineering"),
    "civil engineering": ("14.0801", "Civil Engineering, General"),
    "computer engineering": ("14.0901", "Computer Engineering, General"),
    "software engineering": ("14.0903", "Computer Software Engineering"),
    "electrical engineering": ("14.1001", "Electrical and Electronics Engineering"),
    "engineering mechanics": ("14.1101", "Engineering Mechanics"),
    "engineering physics": ("14.1201", "Engineering Physics/Applied Physics"),
    "environmental engineering": ("14.1401", "Environmental/Environmental Health Engineering"),
    "industrial engineering": ("14.3501", "Industrial Engineering"),
    "materials engineering": ("14.1801", "Materials Engineering"),
    "mechanical engineering": ("14.1901", "Mechanical Engineering"),
    "nuclear engineering": ("14.2301", "Nuclear Engineering"),
    "naval architecture and marine engineering": ("14.2401", "Ocean Engineering"),
    "systems engineering": ("14.2701", "Systems Engineering"),
    "construction engineering": ("14.3301", "Construction Engineering"),
    "robotics": ("14.4201", "Mechatronics, Robotics, and Automation Engineering"),
    # --- Engineering technology (15.xx) ---
    "aeronautical engineering technology": ("15.0801", "Aeronautical/Aerospace Engineering Technology/Technician"),
    "electrical engineering technology": ("15.0303", "Electrical, Electronic, and Communications Engineering Technology/Technician"),
    "mechanical engineering technology": ("15.0805", "Mechanical/Mechanical Engineering Technology/Technician"),
    # --- Computing & data (11.xx, 30.7x) ---
    "computer science": ("11.0701", "Computer Science"),
    "information science": ("11.0401", "Information Science/Studies"),
    "information technology": ("11.0103", "Information Technology"),
    "cybersecurity": ("11.1003", "Computer and Information Systems Security"),
    "artificial intelligence": ("11.0102", "Artificial Intelligence"),
    "data science": ("30.7001", "Data Science, General"),
    "data analytics": ("30.7101", "Data Analytics, General"),
    "business analytics": ("30.7102", "Business Analytics"),
    # --- Life sciences (26.xx) ---
    "biology": ("26.0101", "Biology/Biological Sciences, General"),
    "biochemistry": ("26.0202", "Biochemistry"),
    "molecular biology": ("26.0204", "Molecular Biology"),
    "cell and molecular biology": ("26.0406", "Cell/Cellular and Molecular Biology"),
    "microbiology": ("26.0502", "Microbiology, General"),
    "genetics": ("26.0801", "Genetics, General"),
    "neuroscience": ("26.1501", "Neuroscience"),
    "physiology": ("26.0901", "Physiology, General"),
    "ecology": ("26.1301", "Ecology"),
    "biotechnology": ("26.1201", "Biotechnology"),
    # --- Physical sciences (40.xx) ---
    "chemistry": ("40.0501", "Chemistry, General"),
    "physics": ("40.0801", "Physics, General"),
    "astronomy": ("40.0201", "Astronomy"),
    "astrophysics": ("40.0202", "Astrophysics"),
    "atmospheric science": ("40.0401", "Atmospheric Sciences and Meteorology, General"),
    "geology": ("40.0601", "Geology/Earth Science, General"),
    # --- Environment & agriculture (01.xx, 03.xx) ---
    "environmental science": ("03.0104", "Environmental Science"),
    "environmental studies": ("03.0103", "Environmental Studies"),
    "natural resources": ("03.0101", "Natural Resources/Conservation, General"),
    "forestry": ("03.0501", "Forestry, General"),
    "wildlife": ("03.0601", "Wildlife, Fish and Wildlands Science and Management"),
    "agronomy": ("01.1102", "Agronomy and Crop Science"),
    "animal science": ("01.0901", "Animal Sciences, General"),
    "horticulture": ("01.1103", "Horticultural Science"),
    "food science": ("01.1001", "Food Science"),
    "agricultural economics": ("01.0103", "Agricultural Economics"),
    # --- Math & statistics (27.xx) ---
    "mathematics": ("27.0101", "Mathematics, General"),
    "applied mathematics": ("27.0301", "Applied Mathematics, General"),
    "statistics": ("27.0501", "Statistics, General"),
    # --- Social sciences (42.xx, 45.xx, 44.xx, 43.xx) ---
    "economics": ("45.0601", "Economics, General"),
    "political science": ("45.1001", "Political Science and Government, General"),
    "sociology": ("45.1101", "Sociology, General"),
    "anthropology": ("45.0201", "Anthropology, General"),
    "international relations": ("45.0901", "International Relations and Affairs"),
    "geography": ("45.0701", "Geography"),
    "psychology": ("42.0101", "Psychology, General"),
    "cognitive science": ("30.2501", "Cognitive Science, General"),
    "criminal justice": ("43.0104", "Criminal Justice/Safety Studies"),
    "social work": ("44.0701", "Social Work"),
    "public policy": ("44.0501", "Public Policy Analysis, General"),
    "human services": ("44.0000", "Human Services, General"),
    "urban planning": ("04.0301", "City/Urban, Community and Regional Planning"),
    # --- Humanities (16.xx, 23.xx, 38.xx, 54.xx) ---
    "english": ("23.0101", "English Language and Literature, General"),
    "creative writing": ("23.1302", "Creative Writing"),
    "history": ("54.0101", "History, General"),
    "philosophy": ("38.0101", "Philosophy"),
    "linguistics": ("16.0102", "Linguistics"),
    "spanish": ("16.0905", "Spanish Language and Literature"),
    "french": ("16.0901", "French Language and Literature"),
    # --- Communication & media (09.xx) ---
    "communication": ("09.0100", "Communication, General"),
    "journalism": ("09.0401", "Journalism"),
    "advertising": ("09.0903", "Advertising"),
    "public relations": ("09.0902", "Public Relations/Image Management"),
    "media studies": ("09.0102", "Mass Communication/Media Studies"),
    # --- Business (52.xx) ---
    "business administration": ("52.0201", "Business Administration and Management, General"),
    "accounting": ("52.0301", "Accounting"),
    "finance": ("52.0801", "Finance, General"),
    "marketing": ("52.1401", "Marketing/Marketing Management, General"),
    "management information systems": ("52.1201", "Management Information Systems, General"),
    "supply chain management": ("52.0203", "Logistics, Materials, and Supply Chain Management"),
    "operations management": ("52.0205", "Operations Management and Supervision"),
    "international business": ("52.1101", "International Business/Trade/Commerce"),
    "entrepreneurship": ("52.0701", "Entrepreneurship/Entrepreneurial Studies"),
    "hospitality management": ("52.0901", "Hospitality Administration/Management, General"),
    "human resources management": ("52.1001", "Human Resources Management/Personnel Administration, General"),
    "business economics": ("52.0601", "Business/Managerial Economics"),
    "actuarial science": ("52.1304", "Actuarial Science"),
    "real estate": ("52.1501", "Real Estate"),
    "organizational leadership": ("52.0213", "Organizational Leadership"),
    "construction management": ("52.2001", "Construction Management, General"),
    # --- Health (51.xx, 31.xx, 30.19) ---
    "nursing": ("51.3801", "Registered Nursing/Registered Nurse"),
    "public health": ("51.2201", "Public Health, General"),
    "kinesiology": ("31.0505", "Exercise Science and Kinesiology"),
    "sport management": ("31.0504", "Sport and Fitness Administration/Management"),
    "nutrition sciences": ("30.1901", "Nutrition Sciences"),
    "dietetics": ("51.3101", "Dietetics/Dietitian"),
    "pharmaceutical sciences": ("51.2010", "Pharmaceutical Sciences"),
    "communication sciences and disorders": ("51.0201", "Communication Sciences and Disorders, General"),
    "medical laboratory science": ("51.1005", "Clinical Laboratory Science/Medical Technology/Technologist"),
    "health sciences": ("51.0000", "Health Services/Allied Health/Health Sciences, General"),
    "parks recreation and leisure studies": ("31.0101", "Parks, Recreation, and Leisure Studies"),
    # --- Education (13.xx) ---
    "elementary education": ("13.1202", "Elementary Education and Teaching"),
    "secondary education": ("13.1205", "Secondary Education and Teaching"),
    "middle school education": ("13.1203", "Junior High/Intermediate/Middle School Education and Teaching"),
    "special education": ("13.1001", "Special Education and Teaching, General"),
    "early childhood education": ("13.1210", "Early Childhood Education and Teaching"),
    "music education": ("13.1312", "Music Teacher Education"),
    "art education": ("13.1302", "Art Teacher Education"),
    "english education": ("13.1305", "English/Language Arts Teacher Education"),
    "social studies education": ("13.1318", "Social Studies Teacher Education"),
    # --- Arts & architecture (50.xx, 04.xx, 10.xx, 19.xx, 49.xx, 05.xx) ---
    "music": ("50.0901", "Music, General"),
    "music performance": ("50.0903", "Music Performance, General"),
    "music theory and composition": ("50.0904", "Music Theory and Composition"),
    "jazz studies": ("50.0910", "Jazz/Jazz Studies"),
    "theatre": ("50.0501", "Drama and Dramatics/Theatre Arts, General"),
    "acting": ("50.0506", "Acting"),
    "musical theatre": ("50.0509", "Musical Theatre"),
    "dance": ("50.0301", "Dance, General"),
    "studio art": ("50.0702", "Fine/Studio Arts, General"),
    "art history": ("50.0703", "Art History, Criticism and Conservation"),
    "graphic design": ("50.0409", "Graphic Design"),
    "industrial design": ("50.0404", "Industrial and Product Design"),
    "interior design": ("50.0408", "Interior Design"),
    "film": ("50.0601", "Film/Cinema/Media Studies"),
    "game design": ("50.0411", "Game and Interactive Media Design"),
    "animation": ("10.0304", "Animation, Interactive Technology, Video Graphics, and Special Effects"),
    "architecture": ("04.0201", "Architecture"),
    "landscape architecture": ("04.0601", "Landscape Architecture"),
    "human development and family studies": ("19.0701", "Human Development and Family Studies, General"),
    "professional flight": ("49.0102", "Airline/Commercial/Professional Pilot and Flight Crew"),
    "aviation management": ("49.0104", "Aviation/Airway Management and Operations"),
}

# Normalized variant -> seed-table key. Kept deliberately generic (name
# variants any school could use), not per-school hacks; school-specific
# program brands are supposed to stay unmatched at this stage.
ALIASES = {
    "accountancy": "accounting",
    "aeronautical and astronautical engineering": "aerospace engineering",
    "agricultural and biological engineering": "agricultural engineering",
    "agricultural and consumer economics": "agricultural economics",
    "animal sciences": "animal science",
    "applied exercise science": "kinesiology",
    "architectural studies": "architecture",
    "art and design": "studio art",
    "atmospheric sciences and meteorology": "atmospheric science",
    "communication and media": "communication",
    "community health": "public health",
    "composition": "music theory and composition",
    "computer and information technology": "information technology",
    "crop science": "agronomy",
    "crop sciences": "agronomy",
    "developmental and family science": "human development and family studies",
    "earth and environmental sciences": "geology",
    "elementary teacher education": "elementary education",
    "english language and literature": "english",
    "exercise science": "kinesiology",
    "game development": "game design",
    "general management": "business administration",
    "geology and geophysics": "geology",
    "hospitality and tourism management": "hospitality management",
    "industrial and operations engineering": "industrial engineering",
    "information": "information science",
    "information sciences": "information science",
    "information systems": "management information systems",
    "integrative biology": "biology",
    "interdisciplinary health sciences": "health sciences",
    "biomedical health sciences": "health sciences",
    "international studies": "international relations",
    "jazz": "jazz studies",
    "jazz performance": "jazz studies",
    "management": "business administration",
    "materials science and engineering": "materials engineering",
    "media": "media studies",
    "media and cinema studies": "film",
    "medical laboratory sciences": "medical laboratory science",
    "middle grades education": "middle school education",
    "molecular and cellular biology": "cell and molecular biology",
    "movement science": "kinesiology",
    "music composition": "music theory and composition",
    "natural resources and environmental science": "natural resources",
    "natural resources and environmental sciences": "natural resources",
    "nuclear engineering and radiological sciences": "nuclear engineering",
    "nuclear plasma and radiological engineering": "nuclear engineering",
    "nutrition": "nutrition sciences",
    "nutrition science": "nutrition sciences",
    "nutrition and dietetics": "dietetics",
    "organizational behavior and human resource management": "human resources management",
    "performance": "music performance",
    "professional flight technology": "professional flight",
    "psychological sciences": "psychology",
    "public health sciences": "public health",
    "quantitative business economics": "business economics",
    "recreation sport and tourism": "parks recreation and leisure studies",
    "secondary teacher education": "secondary education",
    "speech and hearing science": "communication sciences and disorders",
    "speech language and hearing sciences": "communication sciences and disorders",
    "strategy innovation and entrepreneurship": "entrepreneurship",
    "supply chain and operations management": "supply chain management",
    "systems engineering and design": "systems engineering",
    "theatre arts": "theatre",
    "visual communication design": "graphic design",
}

# ---------------------------------------------------------------------------
# Normalization — local copy adapted from
# cloud_functions/profile_manager_v2/major_match.py (normalize_major).
# Do NOT import across services; that module stays the canonical
# implementation for serving-side matching. Deviation here: '&' -> ' and '
# (CIP titles spell it out) while '+' is kept so blended degrees
# (UIUC "CS + X") stay visibly distinct — and honestly unmatched.
# ---------------------------------------------------------------------------
_ABBREVIATIONS = {
    "cs": "computer science",
    "compsci": "computer science",
    "ee": "electrical engineering",
    "ece": "electrical and computer engineering",
    "meche": "mechanical engineering",
    "cheme": "chemical engineering",
    "econ": "economics",
    "bio": "biology",
    "biochem": "biochemistry",
    "bme": "biomedical engineering",
    "polisci": "political science",
    "psych": "psychology",
    "cogsci": "cognitive science",
    "stats": "statistics",
    "math": "mathematics",
    "ir": "international relations",
    "ds": "data science",
    "ai": "artificial intelligence",
}
_SUFFIX_RE = re.compile(
    r"[,\s]*(\(|\b)(b\.?s\.?e?\.?|b\.?a\.?|a\.?b\.?|b\.?f\.?a\.?|b\.?b\.?a\.?|"
    r"bachelor(s)?( of (science|arts))?|major|degree)(\))?\s*$",
    re.IGNORECASE,
)
_PAREN_RE = re.compile(r"\([^)]*\)")
_PUNCT_RE = re.compile(r"[^a-z0-9+ ]+")


def normalize_major(name: str) -> str:
    """Lowercase, strip degree suffixes/punctuation, expand shorthand."""
    if not isinstance(name, str):
        return ""
    s = name.strip().lower().replace("&", " and ")
    prev = None
    while prev != s:
        prev = s
        s = _SUFFIX_RE.sub("", s).strip()
    s = _PUNCT_RE.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if s in _ABBREVIATIONS:
        return _ABBREVIATIONS[s]
    return " ".join(_ABBREVIATIONS.get(t, t) for t in s.split(" "))


def map_major_to_cip(name: str):
    """Resolve one major name -> (cip_code, cip_title, matched_key) or None.

    Ladder (all exact after normalization — no fuzzy auto-binding):
      1. normalized name in seed table / aliases
      2. parenthetical qualifier stripped ("Computer Science (LSA)") then #1
    """
    for candidate in (name, _PAREN_RE.sub(" ", name or "")):
        n = normalize_major(candidate)
        if not n:
            continue
        key = ALIASES.get(n, n)
        if key in CIP_SEED:
            code, title = CIP_SEED[key]
            return code, title, key
    return None


def profile_major_names(profile: dict):
    """All (college, major) names in a profile's academic_structure.

    Mirrors cloud_functions/profile_manager_v2/major_match.kb_major_names,
    plus tolerance for collector-workflow output wrapped as {profile: ...}.
    """
    if "academic_structure" not in (profile or {}) and isinstance((profile or {}).get("profile"), dict):
        profile = profile["profile"]
    names = []
    structure = (profile or {}).get("academic_structure") or {}
    for college in structure.get("colleges") or []:
        if not isinstance(college, dict):
            continue
        for major in college.get("majors") or []:
            if isinstance(major, dict) and major.get("name"):
                names.append(major["name"])
    return names


def run_on_profile(path: Path) -> dict:
    with open(path) as f:
        profile = json.load(f)
    names = profile_major_names(profile)
    seen, matched, unmatched = set(), [], []
    for name in names:
        if name in seen:  # same major listed under two colleges — count once
            continue
        seen.add(name)
        hit = map_major_to_cip(name)
        if hit:
            matched.append((name, *hit))
        else:
            unmatched.append(name)
    return {"school": path.stem, "total": len(seen), "matched": matched, "unmatched": unmatched}


def print_report(result: dict, verbose: bool = False) -> None:
    total, n_matched = result["total"], len(result["matched"])
    pct = (100.0 * n_matched / total) if total else 0.0
    print(f"\n=== {result['school']} ===")
    print(f"  majors: {total} | matched: {n_matched} | unmatched: {len(result['unmatched'])} | coverage: {pct:.1f}%")
    if verbose:
        for name, code, title, key in sorted(result["matched"]):
            print(f"    {name:55s} -> {code}  {title}")
    if result["unmatched"]:
        print("  unmatched:")
        for name in sorted(result["unmatched"]):
            print(f"    - {name}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--file", type=Path, default=None,
                    help="run on one collector profile JSON instead of the 3 verified samples")
    ap.add_argument("--verbose", action="store_true", help="also print every matched mapping")
    args = ap.parse_args()

    if args.file:
        paths = [args.file]
    else:
        paths = sorted(DEFAULT_SAMPLES_DIR.glob("*.json"))
        if not paths:
            print(f"No sample profiles found under {DEFAULT_SAMPLES_DIR}", file=sys.stderr)
            return 1

    grand_total = grand_matched = 0
    for path in paths:
        if not path.exists():
            print(f"Not found: {path}", file=sys.stderr)
            return 1
        result = run_on_profile(path)
        print_report(result, verbose=args.verbose)
        grand_total += result["total"]
        grand_matched += len(result["matched"])

    if len(paths) > 1 and grand_total:
        print(f"\nTOTAL: {grand_matched}/{grand_total} matched "
              f"({100.0 * grand_matched / grand_total:.1f}%) across {len(paths)} schools "
              f"| seed table: {len(CIP_SEED)} majors, {len(ALIASES)} aliases")
    return 0


if __name__ == "__main__":
    sys.exit(main())
