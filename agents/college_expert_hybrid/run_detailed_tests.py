import os
import json
import re
import requests
import time
import glob
from datetime import datetime
from typing import Dict, List, Any, Optional

# Configuration
AGENT_URL = "https://college-expert-hybrid-agent-808989169388.us-east1.run.app"
APP_NAME = "college_expert_hybrid"
TEST_USER_EMAIL = "cvsubs@gmail.com"
RESEARCH_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../university_profile_collector/research"))
QUERIES_FILE = os.path.join(os.path.dirname(__file__), "test_queries.md")
REPORT_FILE = "detailed_test_report.md"

# Map common names to file IDs for ground truth lookup
UNI_MAPPING = {
    "UCLA": "ucla", 
    "UC Los Angeles": "ucla",
    "UC Berkeley": "ucb", 
    "Berkeley": "ucb",
    "USC": "usc", 
    "University of Southern California": "usc",
    "UCSD": "ucsd", 
    "UC San Diego": "ucsd",
    "UCI": "uci", 
    "UC Irvine": "uci",
    "UCD": "ucd",
    "UC Davis": "ucd",
    "UIUC": "uiuc",
    "University of Illinois": "uiuc",
    "UCSB": "ucsb",
    "UC Santa Barbara": "ucsb"
}

def load_ground_truth() -> Dict[str, Any]:
    """Loads all university JSON profiles from the research directory."""
    data = {}
    json_files = glob.glob(os.path.join(RESEARCH_DIR, "*.json"))
    print(f"Loading {len(json_files)} ground truth profiles from {RESEARCH_DIR}...")
    
    for fpath in json_files:
        fname = os.path.basename(fpath).replace(".json", "")
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data[fname] = json.load(f)
        except Exception as e:
            print(f"Error loading {fname}: {e}")
    return data

def parse_test_queries() -> List[Dict[str, str]]:
    """Parses the test_queries.md file to extract queries and expectations."""
    queries = []
    current_query = {}
    
    with open(QUERIES_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    for line in lines:
        # Match query line: "1. **"Query text"**"
        match = re.search(r'^\d+\.\s*\*\*"(.+)"\*\*', line.strip())
        if match:
            if current_query:
                queries.append(current_query)
            current_query = {"query": match.group(1), "expected": "", "should": ""}
            continue
            
        # Match expected line
        if line.strip().startswith("- Expected:"):
            current_query["expected"] = line.strip().replace("- Expected:", "").strip()
            
        # Match should line
        if line.strip().startswith("- Should"):
            current_query["should"] = line.strip().replace("- Should", "").strip()
            
    if current_query:
        queries.append(current_query)
        
    print(f"Parsed {len(queries)} queries.")
    return queries

def create_session() -> str:
    """Creates a session with the agent and returns the session ID."""
    url = f"{AGENT_URL}/apps/{APP_NAME}/users/user/sessions"
    try:
        resp = requests.post(url, json={"user_input": "Hello"}, timeout=30)
        resp.raise_for_status()
        return resp.json()["id"]
    except Exception as e:
        print(f"Error creating session: {e}")
        return ""

def send_message(session_id: str, message: str) -> str:
    """Sends a message to the agent and returns the text response."""
    url = f"{AGENT_URL}/run"
    payload = {
        "app_name": APP_NAME,
        "user_id": "user",
        "session_id": session_id,
        "new_message": {
            "parts": [{"text": message}]
        }
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=60) # Longer timeout for detailed queries
        resp.raise_for_status()
        
        # Parse response to get text
        data = resp.json()
        # The API returns a list of events or a dict with events
        events = data if isinstance(data, list) else data.get("events", [])
        
        last_text = ""
        for event in events:
            # We want the last 'model' turn usually, or we aggregate specific parts
            # But let's look for the final response.
            # Assuming standard Google Agent response format.
            if "content" in event and "parts" in event["content"]:
                for part in event["content"]["parts"]:
                    if "text" in part:
                        last_text = part["text"] # Keep updating to get the last one
                        
        return last_text
    except Exception as e:
        print(f"Error sending message: {e}")
        return f"ERROR: {str(e)}"

def verify_response(query: Dict, response: str, ground_truth: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verifies the response against ground truth data.
    Returns a dict with 'status' (PASS/FAIL/WARN) and 'reason'.
    """
    q_text = query["query"].lower()
    resp_text = response.lower()
    
    uni_matches = [k for k in UNI_MAPPING.keys() if k.lower() in q_text]
    target_uni_ids = set(UNI_MAPPING[m] for m in uni_matches)
    
    status = "PASS"
    reason = "Response seems relevant."
    
    # 1. Hallucination Check for non-existent universities
    if "stanford" in q_text or "harvard" in q_text:
        if "not in" in resp_text or "unavailable" in resp_text or "do not have" in resp_text:
            return {"status": "PASS", "reason": "Correctly handled missing university."}
        else:
            return {"status": "FAIL", "reason": "Did not explicitly state university is missing from KB."}

    # 2. Check for empty response
    if not response or len(response) < 20:
        return {"status": "FAIL", "reason": "Response was empty or too short."}
        
    # 3. Ground Truth Verification
    missing_facts = []
    
    for uni_id in target_uni_ids:
        if uni_id not in ground_truth:
            continue
            
        gt = ground_truth[uni_id]
        
        # Acceptance Rate Check
        if "acceptance rate" in q_text:
            # Look for rate in current_status or admitted_profile
            rate = gt.get("current_status", {}).get("overall_acceptance_rate")
            if rate is not None:
                # Check directly for the number (e.g. 9 or 9.0)
                # handle percentages like 0.09 or 9
                if str(rate) not in resp_text and f"{rate}%" not in resp_text:
                     missing_facts.append(f"Missing acceptance rate: {rate}%")
        
        # Tuition Check
        if "tuition" in q_text or "cost" in q_text:
             cost = gt.get("financials", {}).get("cost_of_attendance_breakdown", {}).get("in_state", {}).get("tuition")
             if cost and str(cost) not in response.replace(",", ""): # Remove commas from response for matching
                 missing_facts.append(f"Missing tuition info: {cost}")

        # Employers Check
        if "employers" in q_text or "career" in q_text:
             employers = gt.get("outcomes", {}).get("top_employers", [])
             found_emp = False
             for emp in employers:
                 if emp.lower() in resp_text:
                     found_emp = True
                     break
             if not found_emp and employers:
                 missing_facts.append(f"Did not mention any top employers from list: {employers[:3]}...")

    if missing_facts:
        status = "FAIL"
        reason = f"Verification Failed. {'; '.join(missing_facts)}"
        
    return {"status": status, "reason": reason}

def run_tests():
    ground_truth = load_ground_truth()
    queries = parse_test_queries()
    session_id = create_session()
    
    if not session_id:
        print("Aborting tests due to session creation failure.")
        return

    print(f"Session created: {session_id}")
    
    results = []
    
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"# Detailed Hybrid Agent Verification Report\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Session ID:** `{session_id}`\n\n")
        
        f.write("| ID | Query | Status | Verification Reason |\n")
        f.write("|---|---|---|---|\n")
        
        for i, q in enumerate(queries):
            idx = i + 1
            print(f"Running Test {idx}: {q['query']}")
            
            # Prepare query with email if needed
            msg = q['query']
            if "my" in msg.lower() or " i " in msg.lower().replace("?", " ? "):
                msg += f" [USER_EMAIL: {TEST_USER_EMAIL}]"
                
            response = send_message(session_id, msg)
            verification = verify_response(q, response, ground_truth)
            
            status_icon = "✅" if verification["status"] == "PASS" else "❌"
            
            # Write summary row
            f.write(f"| {idx} | {q['query']} | {status_icon} {verification['status']} | {verification['reason']} |\n")
            
            # Store detail
            results.append({
                "id": idx,
                "query": q['query'],
                "expected": q['expected'],
                "response": response,
                "verification": verification
            })
            
            # Add small delay
            time.sleep(1)
            
        # Append Detailed Section
        f.write("\n\n## Detailed Trace\n")
        for res in results:
            f.write(f"\n### Test {res['id']}: {res['query']}\n")
            f.write(f"**Expected:** {res['expected']}\n\n")
            f.write(f"**Status:** {res['verification']['status']} - {res['verification']['reason']}\n\n")
            f.write(f"**Agent Response:**\n\n> {res['response'].replace(chr(10), '\n> ')}\n")
            f.write("\n---\n")

    print(f"Tests complete. Report generated at {REPORT_FILE}")

if __name__ == "__main__":
    run_tests()
