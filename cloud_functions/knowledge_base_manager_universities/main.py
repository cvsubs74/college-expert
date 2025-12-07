"""
Knowledge Base Manager - Universities
Manages university profile documents in Elasticsearch with hybrid search support.
Provides endpoints for ingesting, searching, listing, and deleting university profiles.
"""
import functions_framework
import json
import os
import logging
from flask import request
import google.generativeai as genai
from elasticsearch import Elasticsearch
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---
ES_CLOUD_ID = os.environ.get('ES_CLOUD_ID')
ES_API_KEY = os.environ.get('ES_API_KEY')
ES_INDEX_NAME = os.environ.get('ES_INDEX_NAME', 'knowledgebase_universities')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# Embedding dimension for Gemini text-embedding-004
EMBEDDING_DIM = 768


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
    """Initialize Elasticsearch client."""
    if not ES_CLOUD_ID or not ES_API_KEY:
        raise ValueError("Elasticsearch credentials not configured")
    return Elasticsearch(cloud_id=ES_CLOUD_ID, api_key=ES_API_KEY)


def init_gemini():
    """Initialize Gemini API."""
    if not GEMINI_API_KEY:
        raise ValueError("Gemini API key not configured")
    genai.configure(api_key=GEMINI_API_KEY)


# --- Elasticsearch Index Management ---
def ensure_index_exists(es_client):
    """Ensure Elasticsearch index exists with correct mappings for hybrid search."""
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
                    "searchable_text": {
                        "type": "text",
                        "analyzer": "university_analyzer"
                    },
                    "embedding": {
                        "type": "dense_vector",
                        "dims": EMBEDDING_DIM,
                        "index": True,
                        "similarity": "cosine"
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
        logger.info(f"Index {ES_INDEX_NAME} created with hybrid search mapping")


# --- Embedding Generation ---
def generate_embedding(text: str) -> list:
    """Generate embedding vector using Gemini text-embedding-004."""
    try:
        max_chars = 25000
        if len(text) > max_chars:
            text = text[:max_chars]
        
        result = genai.embed_content(
            model='models/text-embedding-004',
            content=text,
            task_type="retrieval_document"
        )
        return result['embedding']
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise


def generate_query_embedding(text: str) -> list:
    """Generate embedding for search query."""
    try:
        result = genai.embed_content(
            model='models/text-embedding-004',
            content=text,
            task_type="retrieval_query"
        )
        return result['embedding']
    except Exception as e:
        logger.error(f"Query embedding failed: {e}")
        raise


# --- Text Extraction ---
def create_searchable_text(profile: dict) -> str:
    """Create a rich text representation of the profile for embedding."""
    parts = []
    
    # University name and basic info
    if 'metadata' in profile:
        meta = profile['metadata']
        parts.append(f"University: {meta.get('official_name', '')}")
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
    
    # Admissions data - comprehensive natural language
    if 'admissions_data' in profile:
        ad = profile['admissions_data']
        
        # Current status
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
        
        # Admitted student profile - SAT, ACT, GPA
        if 'admitted_student_profile' in ad:
            asp = ad['admitted_student_profile']
            
            # Testing - SAT and ACT scores
            if 'testing' in asp:
                testing = asp['testing']
                if testing.get('sat_composite_middle_50'):
                    parts.append(f"SAT Score Middle 50%: {testing['sat_composite_middle_50']}")
                    parts.append(f"Admitted students typically score between {testing['sat_composite_middle_50']} on the SAT.")
                if testing.get('sat_math_middle_50'):
                    parts.append(f"SAT Math Middle 50%: {testing['sat_math_middle_50']}")
                if testing.get('sat_reading_middle_50'):
                    parts.append(f"SAT Reading Middle 50%: {testing['sat_reading_middle_50']}")
                if testing.get('act_composite_middle_50'):
                    parts.append(f"ACT Score Middle 50%: {testing['act_composite_middle_50']}")
                    parts.append(f"Admitted students typically score between {testing['act_composite_middle_50']} on the ACT.")
                if testing.get('submission_rate'):
                    parts.append(f"Test Submission Rate: {testing['submission_rate']}% of admitted students submitted test scores.")
                if testing.get('policy_note'):
                    parts.append(f"Testing Policy Note: {testing['policy_note']}")
            
            # GPA
            if 'gpa' in asp:
                gpa = asp['gpa']
                if gpa.get('weighted_middle_50'):
                    parts.append(f"Weighted GPA Middle 50%: {gpa['weighted_middle_50']}")
                    parts.append(f"Admitted students typically have a weighted GPA between {gpa['weighted_middle_50']}.")
                if gpa.get('unweighted_middle_50'):
                    parts.append(f"Unweighted GPA Middle 50%: {gpa['unweighted_middle_50']}")
                if gpa.get('average_weighted'):
                    parts.append(f"Average Weighted GPA: {gpa['average_weighted']}")
                if gpa.get('notes'):
                    parts.append(f"GPA Notes: {gpa['notes']}")
            
            # Demographics
            if 'demographics' in asp:
                demo = asp['demographics']
                if demo.get('first_gen_percentage'):
                    parts.append(f"First-Generation Students: {demo['first_gen_percentage']}%")
                if demo.get('legacy_percentage'):
                    parts.append(f"Legacy Students: {demo['legacy_percentage']}%")
                if demo.get('international_percentage'):
                    parts.append(f"International Students: {demo['international_percentage']}%")
    
    # Academic structure - colleges and majors
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
    
    # Application strategy
    if 'application_strategy' in profile:
        strat = profile['application_strategy']
        if strat.get('alternate_major_strategy'):
            parts.append(f"Application Strategy: {strat['alternate_major_strategy']}")
    
    # Student insights
    if 'student_insights' in profile:
        si = profile['student_insights']
        if si.get('what_it_takes'):
            parts.append(f"What It Takes to Get In: {'; '.join(si['what_it_takes'][:5])}")
        if si.get('essay_tips'):
            parts.append(f"Essay Tips: {'; '.join(si['essay_tips'][:3])}")
    
    # Outcomes - earnings and career
    if 'outcomes' in profile:
        out = profile['outcomes']
        if out.get('median_earnings_10yr'):
            parts.append(f"Median Earnings 10 Years After Graduation: ${out['median_earnings_10yr']:,}")
            parts.append(f"Graduates earn a median of ${out['median_earnings_10yr']:,} ten years after completing their degree.")
        if out.get('employment_rate_2yr'):
            parts.append(f"Employment Rate 2 Years After Graduation: {out['employment_rate_2yr']}%")
        if out.get('grad_school_rate'):
            parts.append(f"Graduate School Rate: {out['grad_school_rate']}% of graduates attend graduate school.")
        if out.get('top_employers'):
            employers = out['top_employers'][:5]
            parts.append(f"Top Employers: {', '.join(employers)}")
            parts.append(f"Graduates commonly work at {', '.join(employers)}.")
        if out.get('loan_default_rate'):
            parts.append(f"Loan Default Rate: {out['loan_default_rate']}%")
    
    # Financials
    if 'financials' in profile:
        fin = profile['financials']
        if fin.get('aid_philosophy'):
            parts.append(f"Financial Aid Philosophy: {fin['aid_philosophy']}")
        if fin.get('average_need_based_aid'):
            parts.append(f"Average Need-Based Aid: ${fin['average_need_based_aid']:,}")
        if fin.get('percent_receiving_aid'):
            parts.append(f"Percent Receiving Aid: {fin['percent_receiving_aid']}%")
    
    return "\n".join(parts)


# --- Ingest University Profile ---
def ingest_university(profile: dict) -> dict:
    """Ingest a university profile into Elasticsearch."""
    try:
        init_gemini()
        es_client = get_elasticsearch_client()
        ensure_index_exists(es_client)
        
        university_id = profile.get('_id')
        if not university_id:
            raise ValueError("Profile must have an '_id' field")
        
        official_name = profile.get('metadata', {}).get('official_name', university_id)
        location = profile.get('metadata', {}).get('location', {})
        
        searchable_text = create_searchable_text(profile)
        embedding = generate_embedding(searchable_text)
        
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
            "searchable_text": searchable_text,
            "embedding": embedding,
            "acceptance_rate": acceptance_rate,
            "test_policy": test_policy,
            "market_position": market_position,
            "median_earnings_10yr": median_earnings,
            "profile": profile,
            "indexed_at": datetime.utcnow().isoformat(),
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
def search_universities(query: str, limit: int = 10, filters: dict = None, search_type: str = "hybrid") -> dict:
    """
    Search universities using hybrid search (BM25 + vector).
    
    Args:
        query: Search query text
        limit: Maximum results to return
        filters: Optional filters (e.g., {"state": "CA", "acceptance_rate_max": 30})
        search_type: "hybrid", "semantic", or "keyword"
    """
    try:
        init_gemini()
        es_client = get_elasticsearch_client()
        
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
            # BM25 text search only
            search_body = {
                "size": limit,
                "query": {
                    "bool": {
                        "must": [
                            {"match": {"searchable_text": query}}
                        ],
                        "filter": filter_clauses
                    }
                }
            }
        elif search_type == "semantic":
            # Vector search only
            query_embedding = generate_query_embedding(query)
            search_body = {
                "size": limit,
                "query": {
                    "bool": {
                        "must": [
                            {
                                "script_score": {
                                    "query": {"match_all": {}},
                                    "script": {
                                        "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                                        "params": {"query_vector": query_embedding}
                                    }
                                }
                            }
                        ],
                        "filter": filter_clauses
                    }
                }
            }
        else:
            # Hybrid search (default): combine BM25 and vector scores
            query_embedding = generate_query_embedding(query)
            search_body = {
                "size": limit,
                "query": {
                    "bool": {
                        "should": [
                            # BM25 component
                            {"match": {"searchable_text": {"query": query, "boost": 1.0}}},
                            {"match": {"official_name": {"query": query, "boost": 2.0}}},
                            # Vector component
                            {
                                "script_score": {
                                    "query": {"match_all": {}},
                                    "script": {
                                        "source": "(cosineSimilarity(params.query_vector, 'embedding') + 1.0) * 2",
                                        "params": {"query_vector": query_embedding}
                                    }
                                }
                            }
                        ],
                        "filter": filter_clauses,
                        "minimum_should_match": 1
                    }
                }
            }
        
        response = es_client.search(index=ES_INDEX_NAME, body=search_body)
        
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
                "size": 100,
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
    status = {"elasticsearch": False, "gemini": False}
    
    try:
        es_client = get_elasticsearch_client()
        es_client.info()
        status["elasticsearch"] = True
    except Exception as e:
        status["elasticsearch_error"] = str(e)
    
    try:
        init_gemini()
        status["gemini"] = True
    except Exception as e:
        status["gemini_error"] = str(e)
    
    return {
        "success": all([status["elasticsearch"], status["gemini"]]),
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
                search_type = data.get('search_type', 'hybrid')
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
