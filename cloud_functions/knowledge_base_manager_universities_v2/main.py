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
def ingest_university(profile: dict) -> dict:
    """Ingest a university profile into Firestore."""
    
    def safe_get(d, *keys, default=None):
        """Safely get nested dictionary values."""
        for key in keys:
            if d is None or not isinstance(d, dict):
                return default
            d = d.get(key)
        return d if d is not None else default
    
    try:
        db = get_db()
        
        university_id = profile.get('_id')
        if not university_id:
            raise ValueError("Profile must have an '_id' field")
        
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
        
        db.save_university(university_id, doc)
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
def get_university(university_id: str) -> dict:
    """Get a specific university profile by ID."""
    try:
        db = get_db()
        data = db.get_university(university_id)
        
        if not data:
            return {"success": False, "error": f"University {university_id} not found"}
        
        return {
            "success": True,
            "university": {
                "university_id": data.get('university_id'),
                "official_name": data.get('official_name'),
                "location": data.get('location'),
                "acceptance_rate": data.get('acceptance_rate'),
                "market_position": data.get('market_position'),
                "profile": data.get('profile'),
                "indexed_at": data.get('indexed_at'),
                "last_updated": data.get('last_updated')
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
        
        system_prompt = f"""You are a helpful university advisor for {university_name}. Answer questions using ONLY the data provided below.

UNIVERSITY DATA:
{university_json}

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
        
        # Call Gemini with JSON response format
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
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
def delete_university(university_id: str) -> dict:
    """Delete a university from the collection."""
    try:
        db = get_db()
        success = db.delete_university(university_id)
        
        if success:
            logger.info(f"Deleted university: {university_id}")
            return {
                "success": True,
                "message": f"Successfully deleted {university_id}"
            }
        else:
            return {
                "success": False,
                "error": f"Failed to delete {university_id}"
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
        
        # GET - List or get specific university
        if req.method == 'GET':
            university_id = req.args.get('id') or req.args.get('university_id')
            if university_id:
                result = get_university(university_id)
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
            
            # Ingest request
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
                            "logo_url": u.get('logo_url') or (u.get('profile', {}).get('logo_url') if u.get('profile') else None)
                        })
                    
                    return add_cors_headers({"success": True, "universities": universities})
                except Exception as e:
                    logger.error(f"Batch get failed: {e}")
                    return add_cors_headers({"success": False, "error": str(e), "universities": []}, 500)
            
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
