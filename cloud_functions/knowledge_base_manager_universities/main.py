"""
Knowledge Base Manager - Universities
Manages university profile documents in Elasticsearch with semantic_text support.
Uses Elasticsearch's built-in ELSER model for semantic search via semantic_text field.
"""
import functions_framework
import json
import os
import logging
from flask import request
from elasticsearch import Elasticsearch
from datetime import datetime, timezone
from google import genai
from google.genai import types

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
        # Match if query IS the acronym or contains the acronym as whole word
        if query_lower == acronym or f" {acronym} " in f" {query_lower} ":
            # Add full name to query to improve search relevance
            expanded = query + f" {full_name}"
            logger.info(f"Expanded acronym '{acronym}' to: {expanded}")
            return expanded
    
    return query


# --- Configuration ---
ES_CLOUD_ID = os.environ.get('ES_CLOUD_ID')
ES_API_KEY = os.environ.get('ES_API_KEY')
ES_INDEX_NAME = os.environ.get('ES_INDEX_NAME', 'knowledgebase_universities')


# --- CORS Headers ---
def add_cors_headers(response, status_code=200):
    """Add CORS headers to response."""
    if isinstance(response, dict):
        return (json.dumps(response), status_code, {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, X-User-Email',
            'Access-Control-Max-Age': '3600'
        })
    return response


# --- Client Initialization ---
def get_elasticsearch_client():
    """Initialize Elasticsearch client with extended timeout for ELSER inference."""
    if not ES_CLOUD_ID or not ES_API_KEY:
        raise ValueError("Elasticsearch credentials not configured")
    # Increase timeout for ELSER inference processing (cold starts can take 30-60s)
    return Elasticsearch(
        cloud_id=ES_CLOUD_ID, 
        api_key=ES_API_KEY,
        request_timeout=180,
        retry_on_timeout=True,
        max_retries=5
    )


# --- Elasticsearch Index Management ---
def ensure_index_exists(es_client):
    """Ensure Elasticsearch index exists with semantic_text mapping."""
    if not es_client.indices.exists(index=ES_INDEX_NAME):
        logger.info(f"Creating index: {ES_INDEX_NAME}")
        mapping = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 1,
                "analysis": {
                    "analyzer": {
                        "university_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "asciifolding"]
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "university_id": {"type": "keyword"},
                    "official_name": {
                        "type": "text",
                        "analyzer": "university_analyzer",
                        "fields": {"keyword": {"type": "keyword"}}
                    },
                    "location": {
                        "properties": {
                            "city": {"type": "keyword"},
                            "state": {"type": "keyword"},
                            "type": {"type": "keyword"}
                        }
                    },
                    # Semantic text field - auto-generates embeddings using ELSER
                    "semantic_content": {
                        "type": "semantic_text",
                        "inference_id": ".elser-2-elasticsearch"
                    },
                    "searchable_text": {
                        "type": "text",
                        "analyzer": "university_analyzer"
                    },
                    "acceptance_rate": {"type": "float"},
                    "test_policy": {"type": "keyword"},
                    "market_position": {"type": "keyword"},
                    "median_earnings_10yr": {"type": "float"},
                    "us_news_rank": {"type": "integer"},  # For sorting by ranking
                    "soft_fit_category": {"type": "keyword"},  # Pre-computed fit category based on acceptance rate
                    "summary": {"type": "text"},  # Pre-computed summary for details view
                    "profile": {"type": "object", "enabled": False},
                    "indexed_at": {"type": "date"},
                    "last_updated": {"type": "date"}
                }
            }
        }
        es_client.indices.create(index=ES_INDEX_NAME, body=mapping)
        logger.info(f"Index {ES_INDEX_NAME} created with semantic_text mapping")


# --- Text Extraction ---
def get_acronyms_for_university(official_name: str) -> list:
    """Get common acronyms/nicknames for a university based on its official name."""
    name_lower = official_name.lower()
    acronyms = []
    
    # Check for matches in our acronym mapping (reverse lookup)
    for acronym, full_name in UNIVERSITY_ACRONYMS.items():
        if full_name.lower() in name_lower or name_lower in full_name.lower():
            acronyms.append(acronym.upper())
    
    # Also add common patterns
    if "california" in name_lower and "berkeley" in name_lower:
        acronyms.extend(["UCB", "UC Berkeley", "Cal", "Berkeley"])
    elif "california" in name_lower and "los angeles" in name_lower:
        acronyms.extend(["UCLA", "UC Los Angeles"])
    elif "california" in name_lower and "san diego" in name_lower:
        acronyms.extend(["UCSD", "UC San Diego"])
    elif "california" in name_lower and "irvine" in name_lower:
        acronyms.extend(["UCI", "UC Irvine"])
    elif "california" in name_lower and "davis" in name_lower:
        acronyms.extend(["UCD", "UC Davis"])
    elif "california" in name_lower and "santa barbara" in name_lower:
        acronyms.extend(["UCSB", "UC Santa Barbara"])
    elif "massachusetts institute" in name_lower:
        acronyms.extend(["MIT"])
    elif "southern california" in name_lower:
        acronyms.extend(["USC", "Trojans"])
    elif "stanford" in name_lower:
        acronyms.extend(["Stanford", "Cardinal"])
    elif "georgia" in name_lower and "technology" in name_lower:
        acronyms.extend(["Georgia Tech", "GT", "GaTech"])
    elif "carnegie" in name_lower:
        acronyms.extend(["CMU", "Carnegie Mellon"])
    elif "new york university" in name_lower:
        acronyms.extend(["NYU"])
    
    return list(set(acronyms))  # Remove duplicates


def create_university_summary(profile: dict) -> str:
    """Create a concise summary of the university for display in details view."""
    parts = []
    
    # Basic info
    meta = profile.get('metadata', {})
    official_name = meta.get('official_name', 'This university')
    location = meta.get('location', {})
    city = location.get('city', '')
    state = location.get('state', '')
    uni_type = location.get('type', 'university')
    
    # Admissions data
    admissions = profile.get('admissions_data', {})
    current_status = admissions.get('current_status', {})
    acceptance_rate = current_status.get('overall_acceptance_rate')
    test_policy = current_status.get('test_policy_details', 'standard testing')
    
    # Rankings
    strategic = profile.get('strategic_profile', {})
    market_position = strategic.get('market_position', '')
    # First check for the new simple us_news_rank field
    us_news_rank = strategic.get('us_news_rank')
    
    # Fallback to extracting from rankings array if not present
    if us_news_rank is None:
        for ranking in strategic.get('rankings', []):
            if ranking.get('source') == 'US News' and ranking.get('rank_category') == 'National Universities':
                us_news_rank = ranking.get('rank_overall') or ranking.get('rank_in_category')
                break
    
    # Build overview paragraph
    overview = f"**{official_name}** is a {uni_type.lower()} university"
    if city and state:
        overview += f" located in {city}, {state}"
    if us_news_rank:
        overview += f", ranked #{us_news_rank} in US News National Universities"
    if acceptance_rate:
        overview += f" with a {acceptance_rate}% acceptance rate"
    if test_policy:
        overview += f" and a {test_policy.lower()} testing policy"
    overview += "."
    parts.append(overview)
    
    # Admissions paragraph
    admitted = admissions.get('admitted_student_profile', {})
    testing = admitted.get('testing', {})
    gpa_data = admitted.get('gpa', {})
    
    admissions_parts = []
    if testing.get('sat_composite_middle_50'):
        admissions_parts.append(f"SAT middle 50%: {testing['sat_composite_middle_50']}")
    if testing.get('act_composite_middle_50'):
        admissions_parts.append(f"ACT middle 50%: {testing['act_composite_middle_50']}")
    if gpa_data.get('weighted_middle_50'):
        admissions_parts.append(f"GPA middle 50%: {gpa_data['weighted_middle_50']}")
    
    early = current_status.get('early_admission_stats', [])
    if early:
        early_info = early[0]
        admissions_parts.append(f"{early_info.get('plan_type', 'Early')} acceptance rate: {early_info.get('acceptance_rate')}%")
    
    if admissions_parts:
        parts.append("**Admissions:** " + ". ".join(admissions_parts) + ".")
    
    # Academics paragraph
    academic = profile.get('academic_structure', {})
    colleges = academic.get('colleges', [])
    if colleges:
        college_names = [c.get('name', '') for c in colleges[:4] if c.get('name')]
        if college_names:
            academics_text = f"**Academics:** The university comprises {len(colleges)} colleges/schools"
            if college_names:
                academics_text += f" including {', '.join(college_names)}"
            if market_position:
                academics_text += f". {market_position}"
            parts.append(academics_text + ".")
    
    # Outcomes paragraph  
    outcomes = profile.get('outcomes', {})
    outcomes_parts = []
    if outcomes.get('median_earnings_10yr'):
        outcomes_parts.append(f"median earnings of ${outcomes['median_earnings_10yr']:,} ten years after graduation")
    if outcomes.get('employment_rate_2yr'):
        outcomes_parts.append(f"{outcomes['employment_rate_2yr']}% employment rate within 2 years")
    if outcomes.get('grad_school_rate'):
        outcomes_parts.append(f"{outcomes['grad_school_rate']}% pursue graduate studies")
    if outcomes.get('top_employers'):
        employers = outcomes['top_employers'][:3]
        outcomes_parts.append(f"top employers include {', '.join(employers)}")
    
    if outcomes_parts:
        parts.append("**Outcomes:** Graduates have " + ", ".join(outcomes_parts) + ".")
    
    return "\n\n".join(parts)


def create_searchable_text(profile: dict) -> str:
    """Create a rich text representation of the profile for semantic search."""
    parts = []
    
    # University name and basic info
    if 'metadata' in profile:
        meta = profile['metadata']
        official_name = meta.get('official_name', '')
        parts.append(f"University: {official_name}")
        
        # Add known acronyms/nicknames for better searchability
        acronyms = get_acronyms_for_university(official_name)
        if acronyms:
            parts.append(f"Also known as: {', '.join(acronyms)}")
        
        if 'location' in meta:
            loc = meta['location']
            parts.append(f"Location: {loc.get('city', '')}, {loc.get('state', '')} ({loc.get('type', '')})")
    
    # Strategic profile - executive summary and philosophy
    if 'strategic_profile' in profile:
        sp = profile['strategic_profile']
        if sp.get('executive_summary'):
            parts.append(f"Summary: {sp['executive_summary']}")
        if sp.get('admissions_philosophy'):
            parts.append(f"Admissions Philosophy: {sp['admissions_philosophy']}")
        if sp.get('market_position'):
            parts.append(f"Market Position: {sp['market_position']}")
    
    # Admissions data
    if 'admissions_data' in profile:
        ad = profile['admissions_data']
        if 'current_status' in ad:
            cs = ad['current_status']
            if cs.get('overall_acceptance_rate'):
                parts.append(f"Acceptance Rate: {cs['overall_acceptance_rate']}% overall")
            if cs.get('transfer_acceptance_rate'):
                parts.append(f"Transfer Acceptance Rate: {cs['transfer_acceptance_rate']}%")
            if cs.get('test_policy_details'):
                parts.append(f"Test Policy: {cs['test_policy_details']}")
            if cs.get('is_test_optional'):
                parts.append("This university is test-optional.")
        
        if 'admitted_student_profile' in ad:
            asp = ad['admitted_student_profile']
            if 'testing' in asp:
                testing = asp['testing']
                if testing.get('sat_composite_middle_50'):
                    parts.append(f"SAT Score Middle 50%: {testing['sat_composite_middle_50']}")
                if testing.get('act_composite_middle_50'):
                    parts.append(f"ACT Score Middle 50%: {testing['act_composite_middle_50']}")
            if 'gpa' in asp:
                gpa = asp['gpa']
                if gpa.get('weighted_middle_50'):
                    parts.append(f"Weighted GPA Middle 50%: {gpa['weighted_middle_50']}")
    
    # Academic structure
    if 'academic_structure' in profile:
        acs = profile['academic_structure']
        if 'colleges' in acs:
            college_names = [c.get('name', '') for c in acs['colleges'] if c.get('name')]
            if college_names:
                parts.append(f"Colleges: {', '.join(college_names[:10])}")
            all_majors = []
            all_courses = []
            all_professors = []
            for college in acs['colleges']:
                for major in college.get('majors', []):
                    if major.get('name'):
                        all_majors.append(major['name'])
                    # Extract curriculum courses
                    curriculum = major.get('curriculum')
                    if curriculum:
                        core_courses = curriculum.get('core_courses', [])
                        electives = curriculum.get('electives', [])
                        for course in core_courses[:5]:  # Limit per major
                            if course and course not in all_courses:
                                all_courses.append(course)
                        for course in electives[:3]:
                            if course and course not in all_courses:
                                all_courses.append(course)
                    # Extract notable professors
                    professors = major.get('notable_professors', [])
                    for prof in professors:
                        if prof and prof not in all_professors:
                            all_professors.append(prof)
            if all_majors:
                parts.append(f"Majors offered: {', '.join(all_majors[:20])}")
            if all_courses:
                parts.append(f"Courses: {', '.join(all_courses[:30])}")
            if all_professors:
                parts.append(f"Notable Professors: {', '.join(all_professors[:15])}")
    
    # Outcomes
    if 'outcomes' in profile:
        out = profile['outcomes']
        if out.get('median_earnings_10yr'):
            parts.append(f"Median Earnings 10 Years After Graduation: ${out['median_earnings_10yr']:,}")
        if out.get('top_employers'):
            employers = out['top_employers'][:5]
            parts.append(f"Top Employers: {', '.join(employers)}")
    
    # Financials
    if 'financials' in profile:
        fin = profile['financials']
        if fin.get('aid_philosophy'):
            parts.append(f"Financial Aid Philosophy: {fin['aid_philosophy']}")
        if fin.get('average_need_based_aid'):
            parts.append(f"Average Need-Based Aid: ${fin['average_need_based_aid']:,}")
    
    return "\n".join(parts)


# --- Ingest University Profile ---
def ingest_university(profile: dict) -> dict:
    """Ingest a university profile into Elasticsearch."""
    try:
        es_client = get_elasticsearch_client()
        ensure_index_exists(es_client)
        
        university_id = profile.get('_id')
        if not university_id:
            raise ValueError("Profile must have an '_id' field")
        
        official_name = profile.get('metadata', {}).get('official_name', university_id)
        location = profile.get('metadata', {}).get('location', {})
        
        searchable_text = create_searchable_text(profile)
        
        current_status = profile.get('admissions_data', {}).get('current_status', {})
        acceptance_rate = current_status.get('overall_acceptance_rate')
        test_policy = current_status.get('test_policy_details', '')
        market_position = profile.get('strategic_profile', {}).get('market_position', '')
        median_earnings = profile.get('outcomes', {}).get('median_earnings_10yr')
        last_updated = profile.get('metadata', {}).get('last_updated')
        
        # Extract US News National Universities rank
        # First check for the new simple us_news_rank field
        strategic = profile.get('strategic_profile', {})
        us_news_rank = strategic.get('us_news_rank')
        
        # Fallback to extracting from rankings array if not present
        if us_news_rank is None:
            rankings = strategic.get('rankings', [])
            for ranking in rankings:
                if ranking.get('source') == 'US News' and ranking.get('rank_category') == 'National Universities':
                    us_news_rank = ranking.get('rank_overall') or ranking.get('rank_in_category')
                    break
        
        # Generate pre-computed summary for details view
        university_summary = create_university_summary(profile)
        
        # Compute soft fit category based on acceptance rate (for lazy fit computation)
        soft_fit_category = compute_soft_fit_category(acceptance_rate)
        logger.info(f"Soft fit category for {official_name}: {soft_fit_category} (acceptance rate: {acceptance_rate}%)")
        
        # Extract media field for easy access (infographics, slides, videos)
        media = profile.get('media')
        
        doc = {
            "university_id": university_id,
            "official_name": official_name,
            "location": location,
            "semantic_content": searchable_text,  # ELSER auto-embeds this
            "searchable_text": searchable_text,
            "summary": university_summary,  # Pre-computed summary for details
            "acceptance_rate": acceptance_rate,
            "soft_fit_category": soft_fit_category,  # Pre-computed fit category
            "test_policy": test_policy,
            "market_position": market_position,
            "median_earnings_10yr": median_earnings,
            "us_news_rank": us_news_rank,  # For sorting by rank
            "media": media,  # Visual content (infographics, slides, videos)
            "profile": profile,
            "indexed_at": datetime.now(timezone.utc).isoformat(),
            "last_updated": last_updated
        }

        
        es_client.index(index=ES_INDEX_NAME, id=university_id, document=doc)
        logger.info(f"Indexed university: {official_name}")
        
        return {
            "success": True,
            "university_id": university_id,
            "official_name": official_name,
            "message": f"Successfully indexed {official_name}"
        }
        
    except Exception as e:
        logger.error(f"Ingest failed: {e}", exc_info=True)
        raise


# --- Search Universities ---
def search_universities(query: str, limit: int = 10, filters: dict = None, search_type: str = "semantic", exclude_ids: list = None, sort_by: str = "relevance") -> dict:
    """
    Search universities using semantic_text field.
    
    With semantic_text, we can use simple match queries for semantic search.
    The ELSER model handles embedding generation automatically at query time.
    
    Args:
        query: Search query text
        limit: Maximum results to return
        filters: Optional filters (e.g., {"state": "CA", "acceptance_rate_max": 30})
        search_type: "semantic" (default), "keyword", or "hybrid"
        exclude_ids: List of university_ids to exclude from results (for avoiding duplicates)
        sort_by: Sort order - "relevance" (default), "selectivity" (by acceptance_rate ASC), 
                 "acceptance_rate" (same as selectivity)
    """

    try:
        es_client = get_elasticsearch_client()
        
        # Expand acronyms in query (MIT -> MIT Massachusetts Institute of Technology)
        expanded_query = expand_acronyms(query)
        
        # Build filter clauses
        filter_clauses = []
        if filters:
            if filters.get('state'):
                filter_clauses.append({"term": {"location.state": filters['state']}})
            if filters.get('type'):
                filter_clauses.append({"term": {"location.type": filters['type']}})
            if filters.get('acceptance_rate_max'):
                filter_clauses.append({"range": {"acceptance_rate": {"lte": filters['acceptance_rate_max']}}})
            if filters.get('acceptance_rate_min'):
                filter_clauses.append({"range": {"acceptance_rate": {"gte": filters['acceptance_rate_min']}}})
            if filters.get('market_position'):
                filter_clauses.append({"term": {"market_position": filters['market_position']}})
        
        # Exclude specific university IDs (for avoiding duplicates in recommendations)
        must_not_clauses = []
        if exclude_ids and len(exclude_ids) > 0:
            must_not_clauses.append({"terms": {"university_id": exclude_ids}})
            logger.info(f"Excluding {len(exclude_ids)} universities from search: {exclude_ids[:5]}...")
        
        if search_type == "keyword":
            # BM25 text search only on searchable_text field
            search_body = {
                "size": limit,
                "query": {
                    "bool": {
                        "must": [
                            {"match": {"searchable_text": expanded_query}}
                        ],
                        "filter": filter_clauses,
                        "must_not": must_not_clauses
                    }
                }
            }
        elif search_type == "hybrid":
            # Combine semantic_text match with BM25 on searchable_text and official_name
            search_body = {
                "size": limit,
                "query": {
                    "bool": {
                        "should": [
                            # Semantic search on semantic_content (using ELSER)
                            {"match": {"semantic_content": {"query": expanded_query, "boost": 2.0}}},
                            # BM25 on searchable_text
                            {"match": {"searchable_text": {"query": expanded_query, "boost": 1.0}}},
                            # Boost exact name matches
                            {"match": {"official_name": {"query": expanded_query, "boost": 3.0}}}
                        ],
                        "filter": filter_clauses,
                        "must_not": must_not_clauses,
                        "minimum_should_match": 1
                    }
                }
            }
        else:
            # Semantic search only (default) - uses ELSER via semantic_text field
            # Simple match query on semantic_text field triggers semantic search
            search_body = {
                "size": limit,
                "query": {
                    "bool": {
                        "must": [
                            {"match": {"semantic_content": expanded_query}}
                        ],
                        "filter": filter_clauses,
                        "must_not": must_not_clauses
                    }
                }
            }
        
        # Add sorting by US News rank if requested (lower rank = better)
        if sort_by in ["rank", "us_news_rank", "selectivity"]:
            search_body["sort"] = [
                {"us_news_rank": {"order": "asc", "missing": "_last"}},  # Nulls last
                {"_score": {"order": "desc"}}  # Secondary sort by relevance
            ]
            logger.info(f"Sorting by US News rank (ascending)")
        
        logger.info(f"Executing {search_type} search for: {query} (expanded: {expanded_query})")

        
        # Retry logic for Elasticsearch cold starts (408 timeout errors)
        # ELSER model can take 30-60s to warm up on first request
        max_retries = 5
        retry_delay = 5  # seconds (base delay, exponentially increases)
        last_error = None
        
        for attempt in range(max_retries):
            try:
                response = es_client.search(index=ES_INDEX_NAME, body=search_body)
                break  # Success, exit retry loop
            except Exception as e:
                last_error = e
                if "408" in str(e) or "timeout" in str(e).lower():
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)  # Exponential backoff: 2s, 4s, 8s, 16s, 32s
                        logger.warning(f"ES cold start timeout (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s...")
                        import time
                        time.sleep(wait_time)
                    else:
                        logger.error(f"ES timeout after {max_retries} attempts: {e}")
                        raise
                else:
                    # Non-timeout error, don't retry
                    raise
        
        results = []
        for hit in response['hits']['hits']:
            source = hit['_source']
            results.append({
                "university_id": source.get('university_id'),
                "official_name": source.get('official_name'),
                "location": source.get('location'),
                "acceptance_rate": source.get('acceptance_rate'),
                "soft_fit_category": source.get('soft_fit_category'),  # Include soft fit
                "market_position": source.get('market_position'),
                "median_earnings_10yr": source.get('median_earnings_10yr'),
                "us_news_rank": source.get('us_news_rank'),
                "summary": source.get('summary'),
                "media": source.get('media'),  # Visual content
                "score": hit['_score'],
                "profile": source.get('profile')
            })
        
        logger.info(f"Search '{query}' returned {len(results)} results")
        
        return {
            "success": True,
            "query": query,
            "search_type": search_type,
            "filters": filters,
            "total": len(results),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "results": []
        }


# --- List Universities ---
def list_universities() -> dict:
    """List all indexed universities."""
    try:
        es_client = get_elasticsearch_client()
        
        if not es_client.indices.exists(index=ES_INDEX_NAME):
            return {"success": True, "universities": [], "total": 0}
        
        response = es_client.search(
            index=ES_INDEX_NAME,
            body={
                "size": 200,
                "query": {"match_all": {}},
            "_source": ["university_id", "official_name", "location", "acceptance_rate", "soft_fit_category",
                       "market_position", "us_news_rank", "summary", "media", "indexed_at", "last_updated"]
            }
        )
        
        universities = []
        for hit in response['hits']['hits']:
            source = hit['_source']
            universities.append({
                "university_id": source.get('university_id'),
                "official_name": source.get('official_name'),
                "location": source.get('location'),
                "acceptance_rate": source.get('acceptance_rate'),
                "soft_fit_category": source.get('soft_fit_category'),  # Include soft fit
                "market_position": source.get('market_position'),
                "us_news_rank": source.get('us_news_rank'),
                "summary": source.get('summary'),
                "media": source.get('media'),  # Visual content
                "indexed_at": source.get('indexed_at'),
                "last_updated": source.get('last_updated')
            })
        
        return {
            "success": True,
            "universities": universities,
            "total": len(universities)
        }
        
    except Exception as e:
        logger.error(f"List failed: {e}")
        return {"success": False, "error": str(e), "universities": []}


# --- Get University ---
def get_university(university_id: str) -> dict:
    """Get a specific university profile by ID."""
    try:
        es_client = get_elasticsearch_client()
        
        response = es_client.get(index=ES_INDEX_NAME, id=university_id)
        source = response['_source']
        
        return {
            "success": True,
            "university": {
                "university_id": source.get('university_id'),
                "official_name": source.get('official_name'),
                "location": source.get('location'),
                "acceptance_rate": source.get('acceptance_rate'),
                "market_position": source.get('market_position'),
                "profile": source.get('profile'),
                "indexed_at": source.get('indexed_at'),
                "last_updated": source.get('last_updated')
            }
        }
        
    except Exception as e:
        logger.error(f"Get university failed: {e}")
        return {"success": False, "error": str(e)}


# --- University Chat with Context Injection ---
def university_chat(university_id: str, question: str, conversation_history: list = None) -> dict:
    """
    Chat about a specific university using its full profile as context.
    Uses gemini-2.5-flash-lite with context injection.
    
    Args:
        university_id: The university ID to chat about
        question: User's question
        conversation_history: List of {role, content} dicts for context
    
    Returns:
        dict with answer and updated conversation history
    """
    try:
        if conversation_history is None:
            conversation_history = []
        
        # Load university data from ES
        university_result = get_university(university_id)
        if not university_result.get("success") or not university_result.get("university"):
            return {
                "success": False,
                "error": f"University {university_id} not found"
            }
        
        university = university_result["university"]
        university_name = university.get("official_name", university_id)
        
        # Build context with university profile (use profile if available, else use summary)
        profile_data = university.get("profile", {})
        if not profile_data:
            # Fallback to summary and other fields
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
        
        system_prompt = f"""You are a helpful university advisor for {university_name}. Answer questions using ONLY the data provided below.

UNIVERSITY DATA:
{university_json}

RULES:
- Only answer based on the data above
- If information is not in the data, say "I don't have that specific information about {university_name}"
- Be concise and direct
- Format responses in markdown when helpful
- Be friendly and helpful
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
            parts=[types.Part(text=f"I'm ready to answer questions about {university_name}. What would you like to know?")]
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
        
        # Call Gemini
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=1024
            )
        )
        
        answer = response.text
        
        # Update history
        updated_history = conversation_history + [
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer}
        ]
        
        logger.info(f"University chat for {university_id}: question='{question[:50]}...', answer_length={len(answer)}")
        
        return {
            "success": True,
            "answer": answer,
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
def delete_university(university_id: str) -> dict:
    """Delete a university from the index."""
    try:
        es_client = get_elasticsearch_client()
        es_client.delete(index=ES_INDEX_NAME, id=university_id)
        
        logger.info(f"Deleted university: {university_id}")
        
        return {
            "success": True,
            "message": f"Successfully deleted {university_id}"
        }
        
    except Exception as e:
        logger.error(f"Delete failed: {e}")
        raise


# --- Health Check ---
def health_check() -> dict:
    """Check service health."""
    status = {"elasticsearch": False}
    
    try:
        es_client = get_elasticsearch_client()
        info = es_client.info()
        status["elasticsearch"] = True
        status["cluster_name"] = info.get('cluster_name')
        status["version"] = info.get('version', {}).get('number')
    except Exception as e:
        status["elasticsearch_error"] = str(e)
    
    return {
        "success": status["elasticsearch"],
        "status": status
    }


# --- HTTP Entry Point ---
@functions_framework.http
def knowledge_base_manager_universities_http_entry(req):
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
        
        # GET - List or get specific university
        if req.method == 'GET':
            university_id = req.args.get('id') or req.args.get('university_id')
            if university_id:
                result = get_university(university_id)
            else:
                result = list_universities()
            return add_cors_headers(result)
        
        # POST - Ingest or Search
        elif req.method == 'POST':
            data = req.get_json() if req.is_json else {}
            
            # Search request
            if 'query' in data:
                query = data.get('query', '')
                limit = data.get('limit', 10)
                filters = data.get('filters', {})
                search_type = data.get('search_type', 'semantic')  # Default to semantic
                exclude_ids = data.get('exclude_ids', [])  # List of university_ids to exclude
                sort_by = data.get('sort_by', 'relevance')  # "relevance", "rank", "selectivity"
                result = search_universities(query, limit, filters, search_type, exclude_ids, sort_by)
                return add_cors_headers(result)
            
            # Ingest request (expects a profile object)
            elif 'profile' in data or '_id' in data:
                profile = data.get('profile', data)
                result = ingest_university(profile)
                return add_cors_headers(result)
            
            # Chat request
            elif 'action' in data and data['action'] == 'chat':
                university_id = data.get('university_id')
                question = data.get('question', '')
                history = data.get('conversation_history', [])
                
                if not university_id or not question:
                    return add_cors_headers({"error": "university_id and question required for chat"}, 400)
                
                result = university_chat(university_id, question, history)
                return add_cors_headers(result)
            
            else:
                return add_cors_headers({"error": "Invalid request. Provide 'query' for search or 'profile' for ingest."}, 400)
        
        # DELETE - Delete university
        elif req.method == 'DELETE':
            data = req.get_json() if req.is_json else {}
            university_id = data.get('id') or data.get('university_id') or req.args.get('id')
            
            if not university_id:
                return add_cors_headers({"error": "University ID required"}, 400)
            
            result = delete_university(university_id)
            return add_cors_headers(result)
        
        else:
            return add_cors_headers({"error": "Method not allowed"}, 405)
            
    except Exception as e:
        logger.error(f"Request failed: {e}", exc_info=True)
        return add_cors_headers({
            "success": False,
            "error": str(e)
        }, 500)
