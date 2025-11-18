"""
Firestore query tools for intelligent document filtering.
Uses LLM to convert user queries to Firestore search criteria.
"""

import os
import json
from google.cloud import firestore
from google import genai
from typing import List, Dict, Any


# Query schema for LLM to generate Firestore filters
# Aligned with the university metadata schema in document_processor.py
QUERY_FILTER_SCHEMA = {
    "type": "object",
    "properties": {
        "university_name": {
            "type": "string",
            "description": "Specific university name mentioned (e.g., 'Stanford University', 'UC Berkeley'). Leave null for queries about multiple universities."
        },
        "university_type": {
            "type": "string",
            "description": "Type of university if specified (e.g., 'Public', 'Private', 'Public Ivy', 'Land-Grant')"
        },
        "location_filter": {
            "type": "string",
            "description": "Geographic filter if specified (e.g., 'California', 'East Coast', 'Urban')"
        },
        "query_topics": {
            "type": "array",
            "description": "List of topics the query is asking about",
            "items": {
                "type": "string",
                "enum": [
                    "admissions_statistics",
                    "acceptance_rates",
                    "testing_policy",
                    "holistic_review_factors",
                    "academic_programs",
                    "majors_and_minors",
                    "selective_majors",
                    "transfer_policies",
                    "internal_transfers",
                    "financial_aid",
                    "scholarships",
                    "cost_of_attendance",
                    "application_deadlines",
                    "credit_policies",
                    "ap_credit",
                    "dual_enrollment",
                    "general_information"
                ]
            }
        },
        "specific_majors": {
            "type": "array",
            "description": "Specific majors or programs mentioned (e.g., ['Computer Science', 'Business', 'Engineering'])",
            "items": {"type": "string"}
        },
        "major_category": {
            "type": "string",
            "description": "Broader major category if applicable (e.g., 'STEM', 'Business', 'Liberal Arts', 'Engineering', 'Pre-Med')"
        },
        "selectivity_filter": {
            "type": "string",
            "description": "Filter by major selectivity type (e.g., 'Selective', 'Capped', 'Restricted Entry', 'High-Demand')"
        },
        "acceptance_rate_range": {
            "type": "object",
            "description": "Filter by acceptance rate range",
            "properties": {
                "min": {"type": "number", "description": "Minimum acceptance rate (e.g., 5.0 for 5%)"},
                "max": {"type": "number", "description": "Maximum acceptance rate (e.g., 20.0 for 20%)"}
            }
        },
        "testing_policy_filter": {
            "type": "string",
            "description": "Filter by testing policy (e.g., 'Test-Optional', 'Test-Blind', 'Test-Required')"
        },
        "financial_aid_filter": {
            "type": "string",
            "description": "Filter by financial aid policy (e.g., 'Need-Blind', 'Meets Full Need', 'Merit Scholarships Available')"
        },
        "has_specific_feature": {
            "type": "array",
            "description": "Specific features the query is looking for",
            "items": {
                "type": "string",
                "enum": [
                    "has_business_major",
                    "has_engineering_major",
                    "has_cs_major",
                    "has_pre_med_track",
                    "has_merit_scholarships",
                    "allows_internal_transfer",
                    "accepts_ap_credit",
                    "has_early_decision",
                    "has_early_action"
                ]
            }
        }
    },
    "required": ["query_topics"]
}


def convert_query_to_filters(query: str, gemini_api_key: str) -> Dict[str, Any]:
    """
    Use LLM to convert natural language query to structured search criteria.
    
    Args:
        query: User's natural language query
        gemini_api_key: Gemini API key
        
    Returns:
        Dictionary with search criteria
    """
    client = genai.Client(
        api_key=gemini_api_key,
        http_options={'api_version': 'v1alpha'}
    )
    
    prompt = f"""
    You are a query analyzer. Convert the following user query into structured search criteria.
    
    **USER QUERY:**
    {query}
    
    **YOUR TASK:**
    Extract the following information from the query:
    1. University name (if mentioned)
    2. Topics the user is asking about (admissions, programs, financial aid, etc.)
    3. Specific major or program (if mentioned)
    
    **EXAMPLES:**
    
    Query: "What are Stanford's computer science admission requirements?"
    Output: {{
        "university_name": "Stanford University",
        "query_topics": ["admissions_statistics", "selective_majors", "academic_programs"],
        "specific_majors": ["Computer Science"],
        "major_category": "STEM"
    }}
    
    Query: "Show me all universities that have a business undergraduate or related major"
    Output: {{
        "university_name": null,
        "query_topics": ["academic_programs", "majors_and_minors"],
        "specific_majors": ["Business", "Business Administration", "Economics", "Finance"],
        "major_category": "Business",
        "has_specific_feature": ["has_business_major"]
    }}
    
    Query: "Compare UC Berkeley and UCLA financial aid policies"
    Output: {{
        "university_name": "UC Berkeley",
        "query_topics": ["financial_aid", "scholarships"],
        "location_filter": "California"
    }}
    
    Query: "What test-optional schools have acceptance rates under 15%?"
    Output: {{
        "university_name": null,
        "query_topics": ["admissions_statistics", "acceptance_rates", "testing_policy"],
        "testing_policy_filter": "Test-Optional",
        "acceptance_rate_range": {{"min": 0, "max": 15.0}}
    }}
    
    Query: "Which private universities offer merit scholarships for engineering?"
    Output: {{
        "university_name": null,
        "university_type": "Private",
        "query_topics": ["financial_aid", "scholarships", "academic_programs"],
        "specific_majors": ["Engineering"],
        "major_category": "Engineering",
        "has_specific_feature": ["has_merit_scholarships", "has_engineering_major"]
    }}
    
    **OUTPUT:**
    Return structured JSON with the extracted criteria.
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
                response_schema=QUERY_FILTER_SCHEMA
            )
        )
        
        filters = json.loads(response.text)
        return filters
        
    except Exception as e:
        print(f"[QUERY FILTER ERROR] Failed to convert query to filters: {str(e)}")
        # Return default filters on error
        return {
            "query_topics": ["general_information"]
        }


def query_firestore_for_relevant_documents(
    filters: Dict[str, Any],
    firestore_collection: str = "university_metadata",
    max_documents: int = 10,
    gemini_api_key: str = None
) -> List[Dict[str, Any]]:
    """
    Query Firestore and use pure semantic matching with LLM.
    
    Simple approach:
    1. Retrieve ALL university metadata from Firestore
    2. Give entire dataset to LLM
    3. LLM analyzes and returns relevant documents
    
    Args:
        filters: Search criteria from convert_query_to_filters (not used directly)
        firestore_collection: Firestore collection name
        max_documents: Maximum number of documents to return
        gemini_api_key: Gemini API key for semantic matching
        
    Returns:
        List of relevant document metadata sorted by relevance
    """
    db = firestore.Client()
    collection_ref = db.collection(firestore_collection)
    
    try:
        # Step 1: Get ALL documents from Firestore
        print(f"[FIRESTORE] Retrieving all documents from {firestore_collection}")
        all_docs = collection_ref.stream()
        
        all_documents = []
        for doc in all_docs:
            doc_data = doc.to_dict()
            all_documents.append({
                "document_id": doc.id,
                "filename": doc_data.get("_document_metadata", {}).get("filename", "Unknown"),
                "university_name": doc_data.get("university_identity", {}).get("name", "Unknown"),
                "university_type": doc_data.get("university_identity", {}).get("type", "Unknown"),
                "metadata": doc_data
            })
        
        print(f"[FIRESTORE] Retrieved {len(all_documents)} total documents")
        
        # Step 2: Use LLM for pure semantic matching
        if gemini_api_key and len(all_documents) > 0:
            print(f"[FIRESTORE] Performing semantic matching with LLM on all documents")
            filtered_docs = semantic_filter_all_documents(all_documents, filters, gemini_api_key, max_documents)
        else:
            print(f"[FIRESTORE WARNING] No API key provided, returning all documents")
            filtered_docs = all_documents[:max_documents]
        
        print(f"[FIRESTORE] Returning {len(filtered_docs)} relevant documents")
        
        return filtered_docs
        
    except Exception as e:
        print(f"[FIRESTORE QUERY ERROR] Failed to query Firestore: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


def matches_basic_filters(doc_data: Dict[str, Any], filters: Dict[str, Any]) -> bool:
    """
    Check if document matches BASIC filters (exact match only).
    Does NOT check majors, features, or other complex criteria.
    
    Args:
        doc_data: Document metadata from Firestore
        filters: Search criteria
        
    Returns:
        True if document matches basic filters
    """
    # Filter by university name (exact match or partial match)
    if filters.get("university_name"):
        doc_name = doc_data.get("university_identity", {}).get("name", "").lower()
        filter_name = filters["university_name"].lower()
        if filter_name not in doc_name and doc_name not in filter_name:
            return False
    
    # Filter by university type
    if filters.get("university_type"):
        doc_type = doc_data.get("university_identity", {}).get("type", "").lower()
        filter_type = filters["university_type"].lower()
        if filter_type not in doc_type:
            return False
    
    # Filter by location
    if filters.get("location_filter"):
        doc_location = doc_data.get("university_identity", {}).get("location", "").lower()
        filter_location = filters["location_filter"].lower()
        if filter_location not in doc_location:
            return False
    
    # Filter by testing policy
    if filters.get("testing_policy_filter"):
        doc_policy = doc_data.get("admissions_overview", {}).get("testing_policy", "").lower()
        filter_policy = filters["testing_policy_filter"].lower()
        if filter_policy not in doc_policy:
            return False
    
    # Filter by acceptance rate range
    if filters.get("acceptance_rate_range"):
        rate_str = doc_data.get("admissions_overview", {}).get("overall_acceptance_rate_recent", "")
        try:
            rate = float(rate_str.replace("%", "").strip())
            min_rate = filters["acceptance_rate_range"].get("min", 0)
            max_rate = filters["acceptance_rate_range"].get("max", 100)
            if not (min_rate <= rate <= max_rate):
                return False
        except (ValueError, AttributeError):
            pass
    
    return True


def semantic_filter_all_documents(
    all_documents: List[Dict[str, Any]], 
    filters: Dict[str, Any],
    gemini_api_key: str,
    max_documents: int = 10
) -> List[Dict[str, Any]]:
    """
    Use LLM to perform pure semantic matching on ALL documents.
    LLM reads complete metadata and intelligently selects relevant universities.
    
    Args:
        all_documents: ALL documents from Firestore
        filters: Search criteria from query analysis
        gemini_api_key: Gemini API key
        max_documents: Maximum number of documents to return
        
    Returns:
        Filtered and ranked list of most relevant documents
    """
    client = genai.Client(
        api_key=gemini_api_key,
        http_options={'api_version': 'v1alpha'}
    )
    
    # Build comprehensive summary of all universities
    docs_summary = []
    for i, doc in enumerate(all_documents):
        metadata = doc["metadata"]
        
        # Extract key information for LLM analysis
        university_identity = metadata.get("university_identity", {})
        admissions_overview = metadata.get("admissions_overview", {})
        academic_structure = metadata.get("academic_structure", {})
        financial_aid = metadata.get("financial_aid_and_cost", {})
        
        majors = academic_structure.get("majors_inventory", [])
        selective_majors = metadata.get("major_capacity_management_policies", [])
        selective_major_names = [p.get("major_name", "") for p in selective_majors]
        
        docs_summary.append({
            "index": i,
            "filename": doc["filename"],
            "university_name": university_identity.get("name", "Unknown"),
            "university_type": university_identity.get("type", ""),
            "location": university_identity.get("location", ""),
            "acceptance_rate": admissions_overview.get("overall_acceptance_rate_recent", ""),
            "testing_policy": admissions_overview.get("testing_policy", ""),
            "majors_inventory": majors,  # Include ALL majors
            "selective_majors": selective_major_names,
            "merit_aid_policy": financial_aid.get("merit_aid_policy", ""),
            "has_scholarships": len(financial_aid.get("flagship_scholarship_programs", [])) > 0
        })
    
    prompt = f"""
    You are an expert university matching system. Analyze ALL universities and return the most relevant ones.
    
    **USER QUERY CRITERIA:**
    {json.dumps(filters, indent=2)}
    
    **ALL UNIVERSITIES ({len(docs_summary)} total):**
    {json.dumps(docs_summary, indent=2)}
    
    **YOUR TASK:**
    Analyze each university's complete metadata and determine relevance to the user's query.
    
    **MATCHING RULES:**
    
    1. **University-Specific Queries:**
       - If university_name is specified, prioritize that university
       - Also include similar/related universities if relevant
    
    2. **Major/Program Matching:**
       - Use SEMANTIC matching for majors (e.g., "Business" includes Business Admin, Commerce, Economics, Finance)
       - If specific_majors specified: Match exact or semantically similar majors
       - If major_category specified: Match any related major in that category
       - Check BOTH majors_inventory AND selective_majors
    
    3. **University Attributes:**
       - Match university_type (Public, Private, etc.)
       - Match location (state, region, urban/rural)
       - Match testing_policy (Test-Optional, Test-Blind, Required)
       - Match acceptance_rate_range if specified
    
    4. **Features:**
       - has_business_major: Look for business, commerce, economics, finance, accounting, marketing
       - has_engineering_major: Look for any engineering programs
       - has_cs_major: Look for computer science, CS, computing, informatics, software engineering
       - has_merit_scholarships: Check merit_aid_policy and has_scholarships
    
    5. **Ranking:**
       - Rank by relevance (best matches first)
       - Consider completeness of match
       - Return up to {max_documents} most relevant universities
    
    **OUTPUT FORMAT:**
    Return JSON object with:
    {{
        "matching_indices": [array of indices of matching universities, ranked by relevance],
        "reasoning": "Brief explanation of matching logic"
    }}
    
    **IMPORTANT:**
    - Be inclusive with semantic matching (e.g., Economics IS business-related)
    - Prioritize universities that match multiple criteria
    - Return empty array if no universities match
    - Maximum {max_documents} universities in result
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                temperature=0.2,  # Slightly higher for better reasoning
                response_mime_type="application/json"
            )
        )
        
        result = json.loads(response.text)
        matching_indices = result.get("matching_indices", [])
        reasoning = result.get("reasoning", "No reasoning provided")
        
        print(f"[SEMANTIC FILTER] LLM Reasoning: {reasoning}")
        print(f"[SEMANTIC FILTER] Matched {len(matching_indices)} of {len(all_documents)} universities")
        
        # Return only matching documents in order of relevance
        filtered = []
        for i in matching_indices:
            if i < len(all_documents):
                doc = all_documents[i]
                doc["relevance_score"] = 100 - (len(filtered) * 10)  # Decreasing score by rank
                filtered.append(doc)
        
        return filtered[:max_documents]
        
    except Exception as e:
        print(f"[SEMANTIC FILTER ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        # On error, return top N documents by default
        return all_documents[:max_documents]


def matches_filters(doc_data: Dict[str, Any], filters: Dict[str, Any]) -> bool:
    """
    Check if a document matches the query filters.
    
    Args:
        doc_data: Document metadata from Firestore
        filters: Search criteria
        
    Returns:
        True if document matches all filters, False otherwise
    """
    # Filter by university name (exact match or partial match)
    if filters.get("university_name"):
        doc_name = doc_data.get("university_identity", {}).get("name", "").lower()
        filter_name = filters["university_name"].lower()
        if filter_name not in doc_name and doc_name not in filter_name:
            return False
    
    # Filter by university type
    if filters.get("university_type"):
        doc_type = doc_data.get("university_identity", {}).get("type", "").lower()
        filter_type = filters["university_type"].lower()
        if filter_type not in doc_type:
            return False
    
    # Filter by location
    if filters.get("location_filter"):
        doc_location = doc_data.get("university_identity", {}).get("location", "").lower()
        filter_location = filters["location_filter"].lower()
        if filter_location not in doc_location:
            return False
    
    # Filter by testing policy
    if filters.get("testing_policy_filter"):
        doc_policy = doc_data.get("admissions_overview", {}).get("testing_policy", "").lower()
        filter_policy = filters["testing_policy_filter"].lower()
        if filter_policy not in doc_policy:
            return False
    
    # Filter by acceptance rate range
    if filters.get("acceptance_rate_range"):
        rate_str = doc_data.get("admissions_overview", {}).get("overall_acceptance_rate_recent", "")
        try:
            # Extract numeric value from string like "15.6%"
            rate = float(rate_str.replace("%", "").strip())
            min_rate = filters["acceptance_rate_range"].get("min", 0)
            max_rate = filters["acceptance_rate_range"].get("max", 100)
            if not (min_rate <= rate <= max_rate):
                return False
        except (ValueError, AttributeError):
            # If we can't parse the rate, don't filter it out
            pass
    
    # Filter by specific majors
    if filters.get("specific_majors"):
        majors_list = doc_data.get("academic_structure", {}).get("majors_inventory", [])
        selective_majors = doc_data.get("major_capacity_management_policies", [])
        
        # Check if any of the requested majors exist in the document
        has_major = False
        for requested_major in filters["specific_majors"]:
            requested_lower = requested_major.lower()
            
            # Check majors inventory
            if any(requested_lower in major.lower() for major in majors_list):
                has_major = True
                break
            
            # Check selective majors
            if any(requested_lower in policy.get("major_name", "").lower() for policy in selective_majors):
                has_major = True
                break
        
        if not has_major:
            return False
    
    # Filter by specific features
    if filters.get("has_specific_feature"):
        for feature in filters["has_specific_feature"]:
            if not has_feature(doc_data, feature):
                return False
    
    return True


def has_feature(doc_data: Dict[str, Any], feature: str) -> bool:
    """Check if document has a specific feature."""
    
    if feature == "has_business_major":
        majors = doc_data.get("academic_structure", {}).get("majors_inventory", [])
        return any("business" in major.lower() or "commerce" in major.lower() or "economics" in major.lower() 
                   for major in majors)
    
    elif feature == "has_engineering_major":
        majors = doc_data.get("academic_structure", {}).get("majors_inventory", [])
        return any("engineering" in major.lower() for major in majors)
    
    elif feature == "has_cs_major":
        majors = doc_data.get("academic_structure", {}).get("majors_inventory", [])
        return any("computer science" in major.lower() or "cs" in major.lower() for major in majors)
    
    elif feature == "has_pre_med_track":
        majors = doc_data.get("academic_structure", {}).get("majors_inventory", [])
        return any("biology" in major.lower() or "pre-med" in major.lower() or "biochemistry" in major.lower() 
                   for major in majors)
    
    elif feature == "has_merit_scholarships":
        merit_policy = doc_data.get("financial_aid_and_cost", {}).get("merit_aid_policy", "").lower()
        scholarships = doc_data.get("financial_aid_and_cost", {}).get("flagship_scholarship_programs", [])
        return "merit" in merit_policy or len(scholarships) > 0
    
    elif feature == "allows_internal_transfer":
        policies = doc_data.get("major_capacity_management_policies", [])
        for policy in policies:
            transfer_policy = policy.get("internal_transfer_policy", {})
            pathway = transfer_policy.get("pathway_existence", "").lower()
            if "exists" in pathway or "available" in pathway:
                return True
        return False
    
    elif feature == "accepts_ap_credit":
        ap_notes = doc_data.get("credit_articulation_policies", {}).get("ap_credit_articulations_notes", "").lower()
        return "credit" in ap_notes and "no credit" not in ap_notes
    
    elif feature == "has_early_decision":
        deadlines = doc_data.get("application_deadlines", [])
        return any("ed" in deadline.get("plan_type", "").lower() or 
                   "early decision" in deadline.get("plan_type", "").lower() 
                   for deadline in deadlines)
    
    elif feature == "has_early_action":
        deadlines = doc_data.get("application_deadlines", [])
        return any("ea" in deadline.get("plan_type", "").lower() or 
                   "early action" in deadline.get("plan_type", "").lower() 
                   for deadline in deadlines)
    
    return False


def calculate_relevance_score(document_metadata: Dict[str, Any], filters: Dict[str, Any]) -> float:
    """
    Calculate relevance score for a document based on query filters.
    
    Args:
        document_metadata: Document metadata from Firestore
        filters: Search criteria
        
    Returns:
        Relevance score (0-100)
    """
    score = 0.0
    query_topics = filters.get("query_topics", [])
    specific_major = filters.get("specific_major")
    
    # Check if document has relevant data for each query topic
    topic_weights = {
        "admissions_statistics": ("admissions_overview", 20),
        "acceptance_rates": ("admissions_overview", 20),
        "testing_policy": ("admissions_overview", 15),
        "academic_programs": ("academic_structure", 15),
        "majors_and_minors": ("academic_structure", 15),
        "selective_majors": ("major_capacity_management_policies", 25),
        "transfer_policies": ("major_capacity_management_policies", 20),
        "financial_aid": ("financial_aid_and_cost", 20),
        "scholarships": ("financial_aid_and_cost", 15),
        "application_deadlines": ("application_deadlines", 10),
        "credit_policies": ("credit_articulation_policies", 10),
        "general_information": ("university_identity", 5)
    }
    
    for topic in query_topics:
        if topic in topic_weights:
            field_name, weight = topic_weights[topic]
            # Check if document has data for this field
            if document_metadata.get(field_name):
                score += weight
    
    # Bonus points if specific major is mentioned and found in document
    if specific_major:
        majors_list = document_metadata.get("academic_structure", {}).get("majors_inventory", [])
        if any(specific_major.lower() in major.lower() for major in majors_list):
            score += 30
        
        # Check selective majors
        selective_majors = document_metadata.get("major_capacity_management_policies", [])
        if any(specific_major.lower() in policy.get("major_name", "").lower() for policy in selective_majors):
            score += 40
    
    return min(score, 100.0)  # Cap at 100


def filter_documents_for_query(query: str, gemini_api_key: str, max_documents: int = 10) -> List[str]:
    """
    Complete pipeline: convert query to filters and return relevant document filenames.
    Uses two-phase approach with semantic matching for accurate results.
    
    Args:
        query: User's natural language query
        gemini_api_key: Gemini API key
        max_documents: Maximum number of documents to return
        
    Returns:
        List of relevant document filenames
    """
    # Step 1: Convert query to filters using LLM
    filters = convert_query_to_filters(query, gemini_api_key)
    print(f"[DOCUMENT FILTER] Query filters: {filters}")
    
    # Step 2: Query Firestore for relevant documents (with semantic matching)
    relevant_docs = query_firestore_for_relevant_documents(
        filters, 
        max_documents=max_documents,
        gemini_api_key=gemini_api_key  # Pass API key for semantic matching
    )
    print(f"[DOCUMENT FILTER] Found {len(relevant_docs)} relevant documents")
    
    # Step 3: Return list of filenames
    filenames = [doc["filename"] for doc in relevant_docs]
    
    # Log relevance scores
    for doc in relevant_docs:
        print(f"[DOCUMENT FILTER]   - {doc['filename']} (score: {doc['relevance_score']})")
    
    return filenames


# Tool function for agent use
def get_relevant_documents(query: str) -> Dict[str, Any]:
    """
    Agent tool: Get list of relevant documents for a query using Firestore filtering.
    
    Args:
        query: User's natural language query
        
    Returns:
        Dictionary with relevant document filenames and metadata
    """
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    
    try:
        filenames = filter_documents_for_query(query, gemini_api_key, max_documents=5)
        
        return {
            "success": True,
            "relevant_documents": filenames,
            "count": len(filenames),
            "message": f"Found {len(filenames)} relevant documents for your query"
        }
    except Exception as e:
        print(f"[GET RELEVANT DOCS ERROR] {str(e)}")
        return {
            "success": False,
            "relevant_documents": [],
            "count": 0,
            "error": str(e),
            "message": "Failed to filter documents, will search all documents"
        }
