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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    # Increase timeout for ELSER inference processing
    return Elasticsearch(
        cloud_id=ES_CLOUD_ID, 
        api_key=ES_API_KEY,
        request_timeout=120,
        retry_on_timeout=True,
        max_retries=3
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
            for college in acs['colleges']:
                for major in college.get('majors', []):
                    if major.get('name'):
                        all_majors.append(major['name'])
            if all_majors:
                parts.append(f"Majors offered: {', '.join(all_majors[:20])}")
    
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
        
        doc = {
            "university_id": university_id,
            "official_name": official_name,
            "location": location,
            "semantic_content": searchable_text,  # ELSER auto-embeds this
            "searchable_text": searchable_text,
            "acceptance_rate": acceptance_rate,
            "test_policy": test_policy,
            "market_position": market_position,
            "median_earnings_10yr": median_earnings,
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
def search_universities(query: str, limit: int = 10, filters: dict = None, search_type: str = "semantic") -> dict:
    """
    Search universities using semantic_text field.
    
    With semantic_text, we can use simple match queries for semantic search.
    The ELSER model handles embedding generation automatically at query time.
    
    Args:
        query: Search query text
        limit: Maximum results to return
        filters: Optional filters (e.g., {"state": "CA", "acceptance_rate_max": 30})
        search_type: "semantic" (default), "keyword", or "hybrid"
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
        
        if search_type == "keyword":
            # BM25 text search only on searchable_text field
            search_body = {
                "size": limit,
                "query": {
                    "bool": {
                        "must": [
                            {"match": {"searchable_text": expanded_query}}
                        ],
                        "filter": filter_clauses
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
                        "filter": filter_clauses
                    }
                }
            }
        
        logger.info(f"Executing {search_type} search for: {query} (expanded: {expanded_query})")
        
        # Retry logic for Elasticsearch cold starts (408 timeout errors)
        max_retries = 5
        retry_delay = 2  # seconds
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
                "market_position": source.get('market_position'),
                "median_earnings_10yr": source.get('median_earnings_10yr'),
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
                "_source": ["university_id", "official_name", "location", "acceptance_rate", 
                           "market_position", "indexed_at", "last_updated"]
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
                "market_position": source.get('market_position'),
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
                result = search_universities(query, limit, filters, search_type)
                return add_cors_headers(result)
            
            # Ingest request (expects a profile object)
            elif 'profile' in data or '_id' in data:
                profile = data.get('profile', data)
                result = ingest_university(profile)
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
