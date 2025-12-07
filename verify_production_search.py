
import os
import sys
import json
import requests

# Production URL for Knowledge Base Manager Universities
KNOWLEDGE_BASE_UNIVERSITIES_URL = 'https://knowledge-base-manager-universities-pfnwjfp26a-ue.a.run.app'

def search_universities(query, search_type="hybrid", filters=None, limit=5):
    """
    Directly call the cloud function to test search.
    """
    url = KNOWLEDGE_BASE_UNIVERSITIES_URL
    headers = {"Content-Type": "application/json"}
    data = {"query": query, "search_type": search_type, "limit": limit}
    if filters:
        data["filters"] = filters
    
    # filters are passed as top-level params in tools.py but search_universities payload structure 
    # in Cloud Function expects 'filters' inside the body?
    # Let's check main.py... Yes, main.py extracts 'filters' from data.
    
    print(f"\n🔍 Searching: '{query}'")
    if filters:
        print(f"   Filters: {filters}")
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        if result.get("success"):
            print(f"✅ Success! Found {result.get('total')} results.")
            for i, item in enumerate(result.get("results", [])):
                print(f"   {i+1}. {item.get('official_name')} (Score: {item.get('score'):.4f})")
                
                # Check for evidence in profile
                profile = item.get("profile", {})
                admissions = profile.get("admissions_data", {})
                sat = admissions.get("admitted_student_profile", {}).get("testing", {}).get("sat_composite_middle_50")
                if sat:
                    print(f"      SAT: {sat}")
                
                loc = item.get("location", {})
                print(f"      Location: {loc.get('city')}, {loc.get('state')}")
                print(f"      Acceptance Rate: {item.get('acceptance_rate')}%")
        else:
            print(f"❌ Failed: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    print("🎓 Verifying Production Search Capabilities")
    print("="*60)
    
    # 1. Natural Language Search for Metrics (Testing improved searchable_text)
    search_universities("What are the SAT requirements for Yale?", search_type="hybrid")
    
    # 2. Filter Search (Testing filters)
    search_universities("universities", filters={"state": "CA", "type": "Public"})
    
    # 3. Hybrid Search + Filters (Testing Agentic RAG capabilities)
    search_universities(
        "engineering programs", 
        search_type="hybrid", 
        filters={"state": "CA", "acceptance_rate_max": 20}
    )
    
    # 4. Another Metric Search
    search_universities("median earnings after graduation", limit=3)

if __name__ == "__main__":
    main()
