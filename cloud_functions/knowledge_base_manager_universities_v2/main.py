"""
Knowledge Base Manager - Universities V2 (Firestore)
Manages university profile documents in Firestore for storage and retrieval.
API-compatible with the Elasticsearch version.
"""
import functions_framework
import json
import os
import logging
from flask import request
from datetime import datetime, timezone
from google import genai
from google.genai import types

from firestore_db import get_db
from versioning import coerce_year, normalize_percentages, validate_profile
from year_history import PROFILE_SECTIONS, build_history, project_profile_sections
from major_facts import extract_major_facts
from request_auth import authenticate
from gemini_fallback import generate_content_with_fallback

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- Soft Fit Category Computation ---
def compute_soft_fit_category(acceptance_rate) -> str:
    """
    Compute soft fit category based purely on acceptance rate.
    This is a preliminary fit category computed at ingest time.
    
    Categories (4 standard categories):
    - SUPER_REACH: < 10% acceptance rate (Ivies, Stanford, MIT, etc.)
    - REACH: 10-25% acceptance rate
    - TARGET: 25-50% acceptance rate
    - SAFETY: > 50% acceptance rate
    """
    if acceptance_rate is None:
        return "UNKNOWN"
    
    try:
        rate = float(acceptance_rate)
    except (TypeError, ValueError):
        return "UNKNOWN"
    
    if rate < 10:
        return "SUPER_REACH"
    elif rate < 25:
        return "REACH"
    elif rate < 50:
        return "TARGET"
    else:
        return "SAFETY"


# --- University Acronym Mappings ---
UNIVERSITY_ACRONYMS = {
    # California Schools
    "ucb": "University of California Berkeley",
    "uc berkeley": "University of California Berkeley",
    "berkeley": "University of California Berkeley",
    "ucla": "University of California Los Angeles",
    "ucsd": "University of California San Diego",
    "uci": "University of California Irvine",
    "ucsb": "University of California Santa Barbara",
    "ucsc": "University of California Santa Cruz",
    "ucr": "University of California Riverside",
    "ucd": "University of California Davis",
    "uc davis": "University of California Davis",
    "usc": "University of Southern California",
    "caltech": "California Institute of Technology",
    "cal tech": "California Institute of Technology",
    "stanford": "Stanford University",
    
    # Ivy League
    "mit": "Massachusetts Institute of Technology",
    "harvard": "Harvard University",
    "yale": "Yale University",
    "princeton": "Princeton University",
    "columbia": "Columbia University",
    "penn": "University of Pennsylvania",
    "upenn": "University of Pennsylvania",
    "brown": "Brown University",
    "dartmouth": "Dartmouth College",
    "cornell": "Cornell University",
    
    # Other Top Schools
    "duke": "Duke University",
    "northwestern": "Northwestern University",
    "nyu": "New York University",
    "stern": "New York University Stern School of Business",
    "nyu stern": "New York University Stern School of Business",
    "umich": "University of Michigan",
    "michigan": "University of Michigan",
    "ut austin": "University of Texas Austin",
    "gtech": "Georgia Institute of Technology",
    "georgia tech": "Georgia Institute of Technology",
    "cmu": "Carnegie Mellon University",
    "carnegie mellon": "Carnegie Mellon University",
}


def expand_acronyms(query: str) -> str:
    """Expand common university acronyms in query to full names."""
    query_lower = query.lower()
    
    # Check for exact matches first (for short acronyms)
    for acronym, full_name in UNIVERSITY_ACRONYMS.items():
        if query_lower == acronym or f" {acronym} " in f" {query_lower} ":
            expanded = query + f" {full_name}"
            logger.info(f"Expanded acronym '{acronym}' to: {expanded}")
            return expanded
    
    return query


# --- Write-path caller gate (#223) ---
# KB reads are public (no PII); writes (ingest / delete) shape what every
# student sees, so they require a credential: a Google OIDC token from a
# trusted service, or the KB_WRITE_TOKEN shared secret used by the ingest
# CLI (scripts/ingest_universities.py). AUTH_MODE off|log|enforce governs
# rollout, same contract as the other backends.
def gate_write(req):
    """Returns (allow: bool, rejection: (body, status)|None) for mutations."""
    mode = (os.getenv('AUTH_MODE') or 'log').strip().lower()
    if mode == 'off':
        return True, None
    admin = os.getenv('KB_WRITE_TOKEN')
    if admin and req.headers.get('X-Admin-Token') == admin:
        return True, None
    identity = authenticate(req)
    if identity['kind'] == 'service':
        return True, None
    detail = identity.get('error') or identity['kind']
    if mode == 'enforce':
        logger.warning(f"[AUTH] REJECT KB write {req.method} {req.path}: {detail}")
        return False, ({'success': False,
                        'error': 'authentication required for KB writes'}, 401)
    logger.warning(f"[AUTH] (log mode) unauthenticated KB write {req.method} {req.path}: {detail}")
    return True, None


# --- CORS Headers ---
def add_cors_headers(response, status_code=200):
    """Add CORS headers to response."""
    from flask import jsonify, make_response
    resp = make_response(json.dumps(response), status_code)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, DELETE, OPTIONS'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    resp.headers['Content-Type'] = 'application/json'
    return resp


# --- Text Extraction ---
def get_acronyms_for_university(official_name: str) -> list:
    """Get common acronyms/nicknames for a university based on its official name."""
    acronyms = []
    name_lower = official_name.lower()
    
    for acronym, full_name in UNIVERSITY_ACRONYMS.items():
        if full_name.lower() == name_lower:
            acronyms.append(acronym)
    
    return acronyms


def create_university_summary(profile: dict) -> str:
    """Create a concise summary of the university for display."""
    parts = []
    
    metadata = profile.get('metadata', {}) or {}
    strategic = profile.get('strategic_profile', {}) or {}
    admissions = profile.get('admissions_data', {}) or {}
    
    # Name and location
    official_name = metadata.get('official_name', '')
    location = metadata.get('location', {})
    if isinstance(location, dict):
        city = location.get('city', '')
        state = location.get('state', '')
        if city and state:
            parts.append(f"{official_name} is a {location.get('type', 'university').lower()} located in {city}, {state}.")
    
    # Executive summary from strategic profile
    exec_summary = strategic.get('executive_summary', '')
    if exec_summary:
        parts.append(exec_summary)
    
    # Admission stats
    current_status = admissions.get('current_status', {}) or {}
    acceptance_rate = current_status.get('overall_acceptance_rate')
    if acceptance_rate:
        parts.append(f"Acceptance rate: {acceptance_rate}%.")
    
    # Rankings
    us_news_rank = strategic.get('us_news_rank')
    if us_news_rank:
        parts.append(f"US News National Universities rank: #{us_news_rank}.")
    
    return ' '.join(parts)


def create_searchable_text(profile: dict) -> str:
    """Create a text representation of the profile for indexing."""
    texts = []
    
    # Helper to safely extract text
    def add_text(value):
        if isinstance(value, str):
            texts.append(value)
        elif isinstance(value, list):
            for item in value:
                add_text(item)
        elif isinstance(value, dict):
            for v in value.values():
                add_text(v)
    
    # Extract key fields
    metadata = profile.get('metadata', {}) or {}
    texts.append(metadata.get('official_name', ''))
    
    location = metadata.get('location', {})
    if isinstance(location, dict):
        texts.append(location.get('city', ''))
        texts.append(location.get('state', ''))
        texts.append(location.get('type', ''))
    
    strategic = profile.get('strategic_profile', {}) or {}
    texts.append(strategic.get('executive_summary', ''))
    texts.append(strategic.get('market_position', ''))
    texts.append(strategic.get('admissions_philosophy', ''))
    
    # Academic programs
    academics = profile.get('academics', {}) or {}
    signature_programs = academics.get('signature_programs', []) or []
    for prog in signature_programs:
        if isinstance(prog, dict):
            texts.append(prog.get('name', ''))
            texts.append(prog.get('description', ''))
    
    # Add acronyms for searchability
    official_name = metadata.get('official_name', '')
    if official_name:
        acronyms = get_acronyms_for_university(official_name)
        texts.extend(acronyms)
    
    return ' '.join(filter(None, texts))


def extract_keywords(profile: dict) -> list:
    """Extract keywords from profile for search indexing."""
    keywords = []
    
    metadata = profile.get('metadata', {}) or {}
    official_name = metadata.get('official_name', '')
    if official_name:
        keywords.extend(official_name.lower().split())
        keywords.extend(get_acronyms_for_university(official_name))
    
    location = metadata.get('location', {})
    if isinstance(location, dict):
        if location.get('city'):
            keywords.append(location['city'].lower())
        if location.get('state'):
            keywords.append(location['state'].lower())
        if location.get('type'):
            keywords.append(location['type'].lower())
    
    strategic = profile.get('strategic_profile', {}) or {}
    if strategic.get('market_position'):
        keywords.extend(strategic['market_position'].lower().split())
    
    # Deduplicate
    return list(set(keywords))


# --- Ingest University Profile ---
def ingest_university(profile: dict, year: int = None) -> dict:
    """Ingest a university profile into Firestore as a cycle-year snapshot.

    `year` is the admission cycle year (ADR 0002); when omitted it defaults
    to the current cycle. The snapshot always lands in versions/{year}; the
    main serving doc is overwritten only when this is the newest year.
    """
    try:
        db = get_db()

        year = coerce_year(year)
        fixed = normalize_percentages(profile)
        if fixed:
            logger.info(f"[ingest:{profile.get('_id')}] normalized {fixed} fraction-style percent fields")
        errors, warnings = validate_profile(profile, year)
        if errors:
            return {
                "success": False,
                "error": "Profile failed validation: " + "; ".join(errors),
                "validation_errors": errors,
                "validation_warnings": warnings,
            }
        for w in warnings:
            logger.warning(f"[ingest:{profile.get('_id')}] {w}")

        university_id = profile.get('_id')
        
        metadata = profile.get('metadata') or {}
        official_name = metadata.get('official_name', university_id) if isinstance(metadata, dict) else university_id
        
        # Handle location
        location_raw = metadata.get('location') if isinstance(metadata, dict) else {}
        location = {}
        if isinstance(location_raw, dict):
            location = location_raw
        
        location_display = ""
        if isinstance(location_raw, dict):
            city = location_raw.get('city', '')
            state = location_raw.get('state', '')
            if city and state:
                location_display = f"{city}, {state}"
        elif isinstance(location_raw, str):
            location_display = location_raw
        
        # Create searchable content
        searchable_text = create_searchable_text(profile)
        keywords = extract_keywords(profile)
        
        # Extract admission stats
        admissions_data = profile.get('admissions_data') or {}
        current_status = admissions_data.get('current_status', {}) if isinstance(admissions_data, dict) else {}
        acceptance_rate = current_status.get('overall_acceptance_rate') if isinstance(current_status, dict) else None
        test_policy = current_status.get('test_policy_details', '') if isinstance(current_status, dict) else ''
        
        # Strategic profile
        strategic_profile = profile.get('strategic_profile') or {}
        market_position = strategic_profile.get('market_position', '') if isinstance(strategic_profile, dict) else ''
        
        # Outcomes
        outcomes = profile.get('outcomes') or {}
        median_earnings = outcomes.get('median_earnings_10yr') if isinstance(outcomes, dict) else None
        
        # US News rank
        us_news_rank = strategic_profile.get('us_news_rank') if isinstance(strategic_profile, dict) else None
        
        # Fallback to extracting from rankings array
        if us_news_rank is None and isinstance(strategic_profile, dict):
            rankings = strategic_profile.get('rankings', []) or []
            for ranking in rankings:
                if isinstance(ranking, dict):
                    if ranking.get('source') == 'US News' and ranking.get('rank_category') == 'National Universities':
                        us_news_rank = ranking.get('rank_overall') or ranking.get('rank_in_category')
                        break
        
        # Generate summary
        university_summary = create_university_summary(profile)
        
        # Compute soft fit category
        soft_fit_category = compute_soft_fit_category(acceptance_rate)
        logger.info(f"Soft fit category for {official_name}: {soft_fit_category} (acceptance rate: {acceptance_rate}%)")
        
        # Extract media
        media = profile.get('media')
        
        doc = {
            "university_id": university_id,
            "official_name": official_name,
            "location": location,
            "location_display": location_display,
            "searchable_text": searchable_text,
            "keywords": keywords,
            "summary": university_summary,
            "acceptance_rate": acceptance_rate,
            "soft_fit_category": soft_fit_category,
            "test_policy": test_policy,
            "market_position": market_position,
            "median_earnings_10yr": median_earnings,
            "us_news_rank": us_news_rank,
            "media": media,
            "profile": profile,
            "indexed_at": datetime.now(timezone.utc).isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

        save_result = db.save_university(university_id, doc, year=year)
        if not save_result.get("saved"):
            return {
                "success": False,
                "error": f"Failed to save {official_name} (year {year})",
            }
        logger.info(f"Indexed university: {official_name} (year {year})")

        return {
            "success": True,
            "university_id": university_id,
            "official_name": official_name,
            "year": year,
            "promoted_to_current": save_result.get("promoted", False),
            "available_years": save_result.get("available_years", []),
            "validation_warnings": warnings,
            "message": f"Successfully indexed {official_name} for cycle {year}"
        }

    except Exception as e:
        logger.error(f"Ingest failed: {e}", exc_info=True)
        raise


# --- Search Universities ---
def search_universities(query: str, limit: int = 10, filters: dict = None, search_type: str = "keyword", exclude_ids: list = None, sort_by: str = "relevance") -> dict:
    """
    Search universities using text matching.
    
    Args:
        query: Search query text
        limit: Maximum results to return
        filters: Optional filters (e.g., {"state": "CA", "acceptance_rate_max": 30})
        search_type: "keyword" or "hybrid" (both use same logic in Firestore)
        exclude_ids: List of university_ids to exclude from results
        sort_by: Sort order - "relevance", "rank", "selectivity", "acceptance_rate"
    """
    try:
        db = get_db()
        
        # Expand acronyms in query
        expanded_query = expand_acronyms(query)
        
        logger.info(f"Executing search for: {query} (expanded: {expanded_query})")
        
        results = db.search_universities(
            query=expanded_query,
            limit=limit,
            filters=filters,
            exclude_ids=exclude_ids,
            sort_by=sort_by
        )
        
        # Format results to match ES version
        formatted_results = []
        for r in results:
            formatted_results.append({
                "university_id": r.get('university_id'),
                "official_name": r.get('official_name'),
                "location": r.get('location'),
                "acceptance_rate": r.get('acceptance_rate'),
                "soft_fit_category": r.get('soft_fit_category'),
                "market_position": r.get('market_position'),
                "median_earnings_10yr": r.get('median_earnings_10yr'),
                "us_news_rank": r.get('us_news_rank'),
                "summary": r.get('summary'),
                "media": r.get('media'),
                "score": r.get('score', 0),
                "profile": r.get('profile')
            })
        
        logger.info(f"Search '{query}' returned {len(formatted_results)} results")
        
        return {
            "success": True,
            "query": query,
            "search_type": search_type,
            "filters": filters,
            "total": len(formatted_results),
            "results": formatted_results
        }
        
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "results": []
        }


# --- List Universities ---
def list_universities(
    limit: int = 30, 
    offset: int = 0, 
    sort_by: str = "us_news_rank", 
    search_term: str = None,
    state: str = None,
    max_acceptance_rate: float = None,
    soft_fit_category: str = None,
    university_type: str = None
) -> dict:
    """
    List indexed universities with pagination, search, and filter support.
    
    Args:
        limit: Number of results per page (default 30)
        offset: Number of results to skip (for pagination)
        sort_by: Sort field (us_news_rank, acceptance_rate, official_name)
        search_term: Optional search string to filter by university name
        state: Optional 2-letter state code to filter by (e.g., 'CA')
        max_acceptance_rate: Optional maximum acceptance rate
        soft_fit_category: Optional fit category ('Safety', 'Target', 'Reach')
        university_type: Optional type ('Public' or 'Private')
    """
    try:
        db = get_db()
        result = db.list_universities(
            limit=limit, 
            offset=offset, 
            sort_by=sort_by, 
            search_term=search_term,
            state=state,
            max_acceptance_rate=max_acceptance_rate,
            soft_fit_category=soft_fit_category,
            university_type=university_type
        )
        
        universities_raw = result.get("universities", [])
        total = result.get("total", 0)
        
        universities = []
        for u in universities_raw:
            universities.append({
                "university_id": u.get('university_id'),
                "official_name": u.get('official_name'),
                "location": u.get('location'),
                "acceptance_rate": u.get('acceptance_rate'),
                "soft_fit_category": u.get('soft_fit_category'),
                "market_position": u.get('market_position'),
                "us_news_rank": u.get('us_news_rank'),
                "summary": u.get('summary'),
                "media": u.get('media'),
                "indexed_at": u.get('indexed_at'),
                "last_updated": u.get('last_updated')
            })
        
        return {
            "success": True,
            "universities": universities,
            "total": total,
            "limit": limit,
            "offset": offset,
            "page": (offset // limit) + 1 if limit > 0 else 1,
            "total_pages": (total + limit - 1) // limit if limit > 0 else 1
        }
        
    except Exception as e:
        logger.error(f"List failed: {e}")
        return {"success": False, "error": str(e), "universities": [], "total": 0}


# --- Get University ---
def get_university(university_id: str, year: int = None, sections: list = None) -> dict:
    """Get a university profile by ID — current data, or a specific cycle year.

    `sections` (list of top-level profile section names) projects the profile
    down to just those sections; the envelope is unchanged. A request whose
    section names are ALL typos is an error (marked `invalid_sections` for
    the HTTP layer to 400); valid-but-absent sections are simply omitted and
    visible via `sections_returned`.
    """
    try:
        db = get_db()

        if sections is not None and not any(s in PROFILE_SECTIONS for s in sections):
            return {
                "success": False,
                "invalid_sections": True,
                "error": (f"No valid section names in {sections}; "
                          f"valid sections: {list(PROFILE_SECTIONS)}"),
            }

        data = db.get_university(university_id, year=year)

        if not data:
            if year is not None:
                available = db.get_available_years(university_id)
                if available:
                    return {
                        "success": False,
                        "error": (f"University {university_id} has no data for cycle "
                                  f"year {year}; available years: {available}"),
                        "available_years": available,
                    }
                return {
                    "success": False,
                    "error": f"University {university_id} has no data for cycle year {year}"
                }
            return {"success": False, "error": f"University {university_id} not found"}

        # Snapshot docs don't carry available_years (main-doc-only field) —
        # backfill it with a cheap field-mask read so year reads self-describe.
        available_years = data.get('available_years')
        if year is not None and available_years is None:
            available_years = db.get_available_years(university_id) or None

        profile = data.get('profile')
        extra = {}
        if sections is not None:
            projected, returned, unknown = project_profile_sections(profile, sections)
            extra['sections_returned'] = returned
            extra['sections_available'] = sorted(
                k for k in (profile or {}) if k in PROFILE_SECTIONS
            )
            if unknown:
                extra['unknown_sections'] = unknown
            profile = projected

        university = {
            "university_id": data.get('university_id'),
            "official_name": data.get('official_name'),
            "location": data.get('location'),
            "acceptance_rate": data.get('acceptance_rate'),
            "soft_fit_category": data.get('soft_fit_category'),
            "us_news_rank": data.get('us_news_rank'),
            "market_position": data.get('market_position'),
            "profile": profile,
            "data_year": data.get('data_year'),
            "available_years": available_years,
            "indexed_at": data.get('indexed_at'),
            "last_updated": data.get('last_updated')
        }
        university.update(extra)
        return {"success": True, "university": university}

    except Exception as e:
        logger.error(f"Get university failed: {e}")
        return {"success": False, "error": str(e)}


# --- University History (two-axis year view) ---
def get_university_history(university_id: str, sections: list = None, years: list = None) -> dict:
    """Per-year view of one university (see year_history.build_history).

    Compact mode returns `snapshots` (KB versions, cycle-year axis) and
    `reported_trends` (school-reported rows from the current profile,
    entering-class axis, verified:false) as separate structures.
    """
    try:
        db = get_db()

        if sections is not None and not any(s in PROFILE_SECTIONS for s in sections):
            return {
                "success": False,
                "invalid_sections": True,
                "error": (f"No valid section names in {sections}; "
                          f"valid sections: {list(PROFILE_SECTIONS)}"),
            }

        main_doc = db.get_university(university_id)
        version_docs = db.list_version_docs(university_id)
        if not main_doc and not version_docs:
            return {"success": False, "error": f"University {university_id} not found"}

        available_years = (main_doc or {}).get('available_years')
        if available_years is None:
            found = sorted(d.get('data_year') for d in version_docs
                           if d.get('data_year') is not None)
            available_years = found or None

        result = build_history(main_doc, version_docs, years=years, sections=sections)
        result.update({
            "success": True,
            "university_id": university_id,
            "official_name": (main_doc or (version_docs[0] if version_docs else {})).get('official_name'),
            "available_years": available_years,
        })
        return result

    except Exception as e:
        logger.error(f"Get university history failed: {e}")
        return {"success": False, "error": str(e)}


# --- University Majors (trust-labeled extract) ---
def get_university_majors(university_id: str, year: int = None,
                          college: str = None, query: str = None) -> dict:
    """Deterministic trust-labeled per-major facts (see major_facts.py).
    Optional `year` reads a cycle snapshot; `college`/`query` filter by
    college or major-name substring."""
    try:
        db = get_db()
        data = db.get_university(university_id, year=year)
        if not data:
            if year is not None:
                available = db.get_available_years(university_id)
                return {"success": False,
                        "error": (f"University {university_id} has no data for cycle "
                                  f"year {year}"
                                  + (f"; available years: {available}" if available else "")),
                        **({"available_years": available} if available else {})}
            return {"success": False, "error": f"University {university_id} not found"}

        facts = extract_major_facts(data.get('profile'), college=college, query=query)
        facts.update({
            "success": True,
            "university_id": university_id,
            "official_name": data.get('official_name'),
            "data_year": data.get('data_year'),
        })
        return facts
    except Exception as e:
        logger.error(f"Get university majors failed: {e}")
        return {"success": False, "error": str(e)}


# --- List University Versions ---
def list_university_versions(university_id: str) -> dict:
    """List the cycle-year snapshots stored for a university."""
    try:
        db = get_db()
        versions = db.list_university_versions(university_id)
        if not versions and not db.get_university(university_id):
            return {"success": False, "error": f"University {university_id} not found"}
        return {
            "success": True,
            "university_id": university_id,
            "versions": versions,
        }
    except Exception as e:
        logger.error(f"List versions failed: {e}")
        return {"success": False, "error": str(e)}


# --- University Chat with Context Injection ---
def _strip_null_values(row: dict) -> dict:
    """Drop null-valued and empty-container keys from a history row so the
    chat prompt stays lean. False survives — it's meaningful data here
    (is_test_optional, vintage_estimated, verified)."""
    return {k: v for k, v in row.items() if v is not None and v != [] and v != {}}


def _build_chat_history_block(university_id: str) -> str:
    """Compact two-axis year-history context for university_chat (#286).

    Returns '' unless snapshots + reported_trends total at least 2 rows —
    a single row is a stat, not a history. Rows are null-stripped compact
    JSON. Callers must wrap this in try/except: a bad snapshot must never
    break chat.
    """
    history = get_university_history(university_id)
    if not history.get('success'):
        return ""
    snapshots = [_strip_null_values(r) for r in history.get('snapshots') or []]
    trends = [_strip_null_values(r) for r in history.get('reported_trends') or []]
    if len(snapshots) + len(trends) < 2:
        return ""
    compact = dict(separators=(',', ':'), default=str)
    # A zero-version legacy school degrades to a single source:'kb_current'
    # row — the current serving doc, NOT a verified cycle snapshot. Label it
    # honestly instead of letting "authoritative" cover it (#293 review).
    has_current_only = any(r.get('source') == 'kb_current' for r in snapshots)
    snapshot_label = (
        "- Current KB serving doc (source 'kb_current': collection year "
        "unknown — NOT a verified cycle snapshot; treat like the profile data "
        "above): "
        if has_current_only else
        "- Stratia KB snapshots (authoritative; keyed by application-cycle "
        "year; rows marked vintage_estimated were auto-archived from "
        "pre-versioning data — both their year AND contents are unverified): "
    )
    notes = [n for n in (history.get('notes') or []) if isinstance(n, str)]
    notes_line = ("\nData notes: " + " | ".join(notes)) if notes else ""
    return (
        "\n\nYEARLY ADMISSIONS HISTORY:\n"
        f"{snapshot_label}{json.dumps(snapshots, **compact)}\n"
        "- School-reported trend series (UNVERIFIED, entering-class year axis "
        "— attribute as 'the school reports', never present as verified): "
        f"{json.dumps(trends, **compact)}\n"
        "When the two disagree, prefer verified KB snapshots over "
        "school-reported rows. These use two different year conventions — "
        f"never merge them into one timeline.{notes_line}"
    )


def university_chat(university_id: str, question: str, conversation_history: list = None) -> dict:
    """
    Chat about a specific university using its full profile as context.
    Uses gemini-2.5-flash-lite with context injection.
    
    Args:
        university_id: The university ID to chat about
        question: User's question
        conversation_history: List of {role, content} dicts for context
    
    Returns:
        dict with answer, suggested_questions, and updated conversation history
    """
    try:
        if conversation_history is None:
            conversation_history = []
        
        # Load university data
        university_result = get_university(university_id)
        if not university_result.get("success") or not university_result.get("university"):
            return {
                "success": False,
                "error": f"University {university_id} not found"
            }
        
        university = university_result["university"]
        university_name = university.get("official_name", university_id)
        
        # Build context with university profile
        profile_data = university.get("profile", {})
        if not profile_data:
            profile_data = {
                "name": university_name,
                "location": university.get("location"),
                "acceptance_rate": university.get("acceptance_rate"),
                "us_news_rank": university.get("us_news_rank"),
                "summary": university.get("summary"),
                "market_position": university.get("market_position"),
                "median_earnings_10yr": university.get("median_earnings_10yr"),
            }
        
        university_json = json.dumps(profile_data, indent=2, default=str)

        # Two-axis year history (#286): assembled once per request; a bad
        # snapshot must never break chat, so any failure just drops the block.
        history_block = ""
        try:
            history_block = _build_chat_history_block(university_id)
        except Exception as history_err:
            logger.warning(
                f"Skipping history block in chat for {university_id}: {history_err}")

        system_prompt = f"""You are a helpful university advisor for {university_name}. Answer questions using ONLY the data provided below.

UNIVERSITY DATA:
{university_json}{history_block}

RULES:
- Only answer based on the data above
- If information is not in the data, say "I don't have that specific information about {university_name}"
- Be concise and direct
- Format responses in markdown when helpful
- Be friendly and helpful

RESPONSE FORMAT:
You MUST respond with valid JSON in this exact format:
{{
  "answer": "Your helpful response here using markdown formatting",
  "suggested_questions": ["Question 1?", "Question 2?", "Question 3?"]
}}

The suggested_questions should be 3 relevant follow-up questions the user might want to ask about {university_name} based on the conversation context. Make them specific and helpful.
"""
        
        # Build conversation for Gemini
        contents = []
        
        # Add system context as first user message
        contents.append(types.Content(
            role="user",
            parts=[types.Part(text=system_prompt)]
        ))
        contents.append(types.Content(
            role="model",
            parts=[types.Part(text='{"answer": "I\'m ready to answer questions about ' + university_name + '. What would you like to know?", "suggested_questions": ["What is the acceptance rate?", "What majors are offered?", "Tell me about campus life"]}')]
        ))
        
        # Add conversation history
        for msg in conversation_history:
            role = "user" if msg.get("role") == "user" else "model"
            contents.append(types.Content(
                role=role,
                parts=[types.Part(text=msg.get("content", ""))]
            ))
        
        # Add current question
        contents.append(types.Content(
            role="user",
            parts=[types.Part(text=question)]
        ))
        
        # Call Gemini with JSON response format (auto-falls back to another model
        # if the primary is overloaded, so a 503 doesn't kill the chat).
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        response = generate_content_with_fallback(
            client,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=1024,
                response_mime_type="application/json"
            )
        )
        
        response_text = response.text
        
        # Parse JSON response
        suggested_questions = []
        try:
            parsed = json.loads(response_text)
            answer = parsed.get("answer", response_text)
            suggested_questions = parsed.get("suggested_questions", [])
            # Ensure we have at max 3 questions
            suggested_questions = suggested_questions[:3]
        except json.JSONDecodeError:
            # Fallback: use raw response as answer
            answer = response_text
            logger.warning(f"Failed to parse JSON from university_chat response, using raw text")
        
        # Update history (store just the answer portion, not the JSON)
        updated_history = conversation_history + [
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer}
        ]
        
        logger.info(f"University chat for {university_id}: question='{question[:50]}...', answer_length={len(answer)}, suggestions={len(suggested_questions)}")
        
        return {
            "success": True,
            "answer": answer,
            "suggested_questions": suggested_questions,
            "conversation_history": updated_history,
            "university_name": university_name,
            "university_id": university_id
        }
        
    except Exception as e:
        logger.error(f"University chat failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


# --- Delete University ---
def delete_university(university_id: str, year: int = None) -> dict:
    """Delete a university (all years), or a single cycle-year snapshot."""
    try:
        db = get_db()
        success = db.delete_university(university_id, year=year)

        scope = f"{university_id} (cycle {year})" if year is not None else university_id
        if success:
            logger.info(f"Deleted university: {scope}")
            return {
                "success": True,
                "message": f"Successfully deleted {scope}"
            }
        else:
            return {
                "success": False,
                "error": f"Failed to delete {scope}"
            }

    except Exception as e:
        logger.error(f"Delete failed: {e}")
        raise


# --- Health Check ---
def health_check() -> dict:
    """Check service health."""
    try:
        db = get_db()
        result = db.health_check()
        return {
            "success": result.get("success", False),
            "status": result
        }
    except Exception as e:
        return {
            "success": False,
            "status": {"firestore": False, "error": str(e)}
        }


# --- HTTP Entry Point ---
@functions_framework.http
def knowledge_base_manager_universities_v2_http_entry(req):
    """HTTP Cloud Function entry point."""
    
    # Handle CORS preflight
    if req.method == 'OPTIONS':
        return add_cors_headers({}, 204)
    
    try:
        path = req.path.rstrip('/')
        
        # Health check
        if path == '/health' or (req.method == 'GET' and req.args.get('action') == 'health'):
            result = health_check()
            return add_cors_headers(result)
        
        # GET - List or get specific university (optionally a cycle-year
        # snapshot via ?year=, the stored years via ?action=versions, or a
        # per-year view via ?action=history; ?sections=a,b projects the
        # profile down to those top-level sections)
        if req.method == 'GET':
            university_id = req.args.get('id') or req.args.get('university_id')
            action = req.args.get('action')
            raw_sections = req.args.get('sections')
            sections = ([s.strip() for s in raw_sections.split(',') if s.strip()]
                        if raw_sections else None)
            if university_id:
                if action == 'versions':
                    result = list_university_versions(university_id)
                elif action == 'majors':
                    raw_year = req.args.get('year')
                    year = None
                    if raw_year:
                        try:
                            year = coerce_year(raw_year)
                        except ValueError as e:
                            return add_cors_headers({"success": False, "error": f"Invalid year: {e}"}, 400)
                    result = get_university_majors(
                        university_id, year=year,
                        college=req.args.get('college'),
                        query=req.args.get('q') or req.args.get('query'))
                elif action == 'history':
                    # `years` filters snapshots; a lone `year` is accepted as
                    # an alias so it isn't silently ignored.
                    raw_years = req.args.get('years') or req.args.get('year')
                    years = None
                    if raw_years:
                        try:
                            years = [coerce_year(y) for y in str(raw_years).split(',') if y.strip()]
                        except ValueError as e:
                            return add_cors_headers({"success": False, "error": f"Invalid year: {e}"}, 400)
                    result = get_university_history(university_id, sections=sections, years=years)
                    if result.pop('invalid_sections', False):
                        return add_cors_headers(result, 400)
                else:
                    raw_year = req.args.get('year')
                    year = None
                    if raw_year:
                        try:
                            year = coerce_year(raw_year)
                        except ValueError as e:
                            return add_cors_headers({"success": False, "error": f"Invalid year: {e}"}, 400)
                    result = get_university(university_id, year=year, sections=sections)
                    if result.pop('invalid_sections', False):
                        return add_cors_headers(result, 400)
            elif action in ('history', 'majors'):
                return add_cors_headers(
                    {"success": False, "error": f"action={action} requires an 'id' parameter"}, 400)
            else:
                # Parse pagination and search parameters
                limit = int(req.args.get('limit', 30))
                offset = int(req.args.get('offset', 0))
                page = req.args.get('page')
                sort_by = req.args.get('sort_by', 'us_news_rank')
                search = req.args.get('search', '').strip() or None
                
                # If page is provided, calculate offset
                if page:
                    page_num = int(page)
                    offset = (page_num - 1) * limit
                
                # Parse filter parameters
                state = req.args.get('state', '').strip() or None
                max_acceptance = req.args.get('max_acceptance')
                max_acceptance_rate = float(max_acceptance) if max_acceptance else None
                fit_category = req.args.get('fit_category', '').strip() or None
                university_type = req.args.get('type', '').strip() or None
                
                result = list_universities(
                    limit=limit, 
                    offset=offset, 
                    sort_by=sort_by, 
                    search_term=search,
                    state=state,
                    max_acceptance_rate=max_acceptance_rate,
                    soft_fit_category=fit_category,
                    university_type=university_type
                )
            return add_cors_headers(result)
        
        # POST - Ingest or Search
        elif req.method == 'POST':
            data = req.get_json() if req.is_json else {}
            
            # Search request
            if 'query' in data:
                query = data.get('query', '')
                limit = data.get('limit', 10)
                filters = data.get('filters', {})
                search_type = data.get('search_type', 'semantic')
                exclude_ids = data.get('exclude_ids', [])
                sort_by = data.get('sort_by', 'relevance')
                result = search_universities(query, limit, filters, search_type, exclude_ids, sort_by)
                return add_cors_headers(result)
            
            # Ingest request — optional 'year' files the snapshot under that
            # admission cycle (defaults to the current cycle, ADR 0002).
            # 'year' is an envelope field: a bare-profile POST (no 'profile'
            # wrapper) can't carry one and gets the current cycle.
            elif 'profile' in data or '_id' in data:
                allow, rejection = gate_write(req)
                if not allow:
                    return add_cors_headers(*rejection)
                profile = data.get('profile', data)
                try:
                    year = coerce_year(data.get('year')) if 'profile' in data else coerce_year(None)
                except ValueError as e:
                    return add_cors_headers({"success": False, "error": f"Invalid year: {e}"}, 400)
                result = ingest_university(profile, year=year)
                if result.get("success"):
                    status = 200
                elif result.get("validation_errors"):
                    status = 400  # caller sent a bad profile
                else:
                    status = 500  # storage failure — not the caller's fault
                return add_cors_headers(result, status)
            
            # Chat request
            elif 'action' in data and data['action'] == 'chat':
                university_id = data.get('university_id')
                question = data.get('question', '')
                history = data.get('conversation_history', [])
                
                if not university_id or not question:
                    return add_cors_headers({"error": "university_id and question required for chat"}, 400)
                
                result = university_chat(university_id, question, history)
                return add_cors_headers(result)
            
            # Batch get request - get multiple universities by IDs
            elif 'university_ids' in data:
                university_ids = data.get('university_ids', [])
                if not university_ids:
                    return add_cors_headers({"success": True, "universities": []})
                
                try:
                    db = get_db()
                    universities_raw = db.batch_get_universities(university_ids)
                    
                    universities = []
                    for u in universities_raw:
                        universities.append({
                            "university_id": u.get('university_id'),
                            "official_name": u.get('official_name'),
                            "location": u.get('location'),
                            "acceptance_rate": u.get('acceptance_rate'),
                            "soft_fit_category": u.get('soft_fit_category'),
                            "us_news_rank": u.get('us_news_rank'),
                            "summary": u.get('summary'),
                            "media": u.get('media'),
                            "profile": u.get('profile'),
                            "data_year": u.get('data_year'),
                            "last_updated": u.get('last_updated'),
                            "logo_url": u.get('logo_url') or (u.get('profile', {}).get('logo_url') if u.get('profile') else None)
                        })
                    
                    return add_cors_headers({"success": True, "universities": universities})
                except Exception as e:
                    logger.error(f"Batch get failed: {e}")
                    return add_cors_headers({"success": False, "error": str(e), "universities": []}, 500)
            
            else:
                return add_cors_headers({"error": "Invalid request. Provide 'query' for search or 'profile' for ingest."}, 400)
        
        # DELETE - Delete university (all years) or one cycle-year snapshot
        elif req.method == 'DELETE':
            allow, rejection = gate_write(req)
            if not allow:
                return add_cors_headers(*rejection)
            data = req.get_json() if req.is_json else {}
            university_id = data.get('id') or data.get('university_id') or req.args.get('id')

            if not university_id:
                return add_cors_headers({"error": "University ID required"}, 400)

            raw_year = data.get('year') or req.args.get('year')
            year = None
            if raw_year:
                try:
                    year = coerce_year(raw_year)
                except ValueError as e:
                    return add_cors_headers({"success": False, "error": f"Invalid year: {e}"}, 400)

            result = delete_university(university_id, year=year)
            return add_cors_headers(result)
        
        else:
            return add_cors_headers({"error": "Method not allowed"}, 405)
            
    except Exception as e:
        logger.error(f"Request failed: {e}", exc_info=True)
        return add_cors_headers({
            "success": False,
            "error": str(e)
        }, 500)
