#!/usr/bin/env python3
"""
University Profile Deep Research CLI

Uses Google Gemini Deep Research API via REST to generate comprehensive university profiles.
The output matches the schema used by the college_counselor application.

Usage:
    python3 deep_research_cli.py "Stanford University"
    python3 deep_research_cli.py "MIT" --output mit.json
    python3 deep_research_cli.py "Duke University" --verbose
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
import requests


# Deep Research agent model name
DEEP_RESEARCH_AGENT = "deep-research-pro-preview-12-2025"

# API endpoint
INTERACTIONS_API_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"

# Poll interval in seconds
POLL_INTERVAL = 15


def get_research_prompt(university_name: str) -> str:
    """Generate the comprehensive research prompt for a university.
    
    This prompt incorporates requirements from all 13 specialized sub-agents:
    1. StrategyAgent -> Metadata + StrategicProfile
    2. AdmissionsCurrentAgent -> CurrentStatus
    3. AdmissionsTrendsAgent -> LongitudinalTrends + WaitlistStats
    4. AdmittedProfileAgent -> GPA, Testing, Demographics, RaceEthnicity
    5. CollegesAgent -> Academic structure, housing, archetypes
    6. MajorsAgent -> Major details with weeder courses, GPA floors
    7. ApplicationAgent -> Deadlines, supplementals, holistic factors
    8. StrategyTacticsAgent -> Gaming tactics
    9. FinancialsAgent -> Cost of attendance
    10. ScholarshipsAgent -> All scholarships
    11. CreditPoliciesAgent -> AP/IB/Transfer policies
    12. StudentInsightsAgent -> Crowdsourced tips
    13. OutcomesAgent -> Career ROI, Retention
    """
    return f'''You are an elite college admissions research analyst. Conduct an EXHAUSTIVE research project on {university_name} to produce a comprehensive university profile for college applicants.

═══════════════════════════════════════════════════════════════════════════════
RESEARCH PHASE 1: STRATEGIC OVERVIEW & RANKINGS
═══════════════════════════════════════════════════════════════════════════════

SEARCH for:
- "US News National Universities ranking 2026 {university_name}"
- "site:usnews.com {university_name} ranking"
- "{university_name} admissions philosophy holistic review"
- "Reddit {university_name} campus social life"
- "{university_name} research opportunities undergraduates"

COLLECT: Executive summary, market position, admissions philosophy, US News rank, campus dynamics (social environment, transportation, research).

═══════════════════════════════════════════════════════════════════════════════
RESEARCH PHASE 2: CURRENT ADMISSIONS STATISTICS
═══════════════════════════════════════════════════════════════════════════════

SEARCH for:
- "{university_name} Common Data Set 2024 Section C"
- "{university_name} acceptance rate 2024"
- "{university_name} early decision acceptance rate"
- "{university_name} test policy"
- "{university_name} transfer acceptance rate"

COLLECT: Overall/in-state/out-of-state/international/transfer acceptance rates, class size, test policy, early admission stats (ED/EA/REA/ED2 rates).

═══════════════════════════════════════════════════════════════════════════════
RESEARCH PHASE 3: HISTORICAL TRENDS & WAITLIST DATA (The "Black Box")
═══════════════════════════════════════════════════════════════════════════════

SEARCH for:
- "{university_name} Common Data Set Section C2 waitlist"
- "{university_name} acceptance rate history 5 years"
- "{university_name} waitlist admit rate"
- "site:reddit.com {university_name} waitlist admitted"

COLLECT for 2021-2025: Applications, admits, enrolled, acceptance rates, yield rates, WAITLIST DETAILS (offered spots, accepted spots, admitted from waitlist, waitlist admit rate, ranked/unranked).

═══════════════════════════════════════════════════════════════════════════════
RESEARCH PHASE 4: ADMITTED STUDENT PROFILE & DEMOGRAPHICS
═══════════════════════════════════════════════════════════════════════════════

SEARCH for:
- "{university_name} Common Data Set GPA SAT ACT"
- "{university_name} Common Data Set Section B2 racial ethnic"
- "{university_name} IPEDS demographics"
- "{university_name} first generation legacy"

COLLECT: GPA (weighted/unweighted middle 50%), SAT/ACT middle 50%, test submission rate, demographics (first-gen %, legacy %, international %, geographic breakdown, gender breakdown, FULL racial breakdown from IPEDS).

═══════════════════════════════════════════════════════════════════════════════
RESEARCH PHASE 5: ACADEMIC STRUCTURE (COLLEGES, MAJORS, CURRICULUM & FACULTY)
═══════════════════════════════════════════════════════════════════════════════

SEARCH for:
- "{university_name} colleges schools list"
- "{university_name} impacted majors capped selective"
- "site:reddit.com transferring into CS at {university_name}"
- "{university_name} change major requirements GPA"
- "{university_name} [Major] curriculum course requirements"
- "{university_name} [Major] faculty professors"
- "site:{university_name}.edu department faculty"
- "{university_name} catalog major requirements"

COLLECT: All colleges/schools with admissions model, housing profile, student archetype. For EACH major: degree type, is_impacted, acceptance rate, prerequisite courses, minimum_gpa_to_declare (GPA floor to switch in), weeder_courses (filter courses), direct_admit_only status, internal transfer rules.

ADDITIONALLY FOR TOP 5 POPULAR MAJORS:
- curriculum: core_courses (required courses list with course codes), electives (popular options), total_units, major_units
- notable_professors: Faculty names with their specialty areas from department websites

═══════════════════════════════════════════════════════════════════════════════
RESEARCH PHASE 6: APPLICATION REQUIREMENTS
═══════════════════════════════════════════════════════════════════════════════

SEARCH for:
- "{university_name} application deadline 2025"
- "{university_name} supplemental essays"
- "{university_name} demonstrated interest"
- "{university_name} interview policy legacy"

COLLECT: Application platforms, all deadlines, supplemental requirements (essays/portfolio/audition), holistic factors (primary/secondary), essay importance, DI policy, interview policy, legacy consideration, first-gen boost.

═══════════════════════════════════════════════════════════════════════════════
RESEARCH PHASE 7: APPLICATION GAMING STRATEGIES
═══════════════════════════════════════════════════════════════════════════════

SEARCH for:
- "site:reddit.com {university_name} easier majors to get into"
- "site:reddit.com {university_name} alternate major strategy"
- "{university_name} undeclared major acceptance"

COLLECT: Major selection tactics (3-5), college ranking tactics, alternate major strategy.

═══════════════════════════════════════════════════════════════════════════════
RESEARCH PHASE 8: FINANCIALS & SCHOLARSHIPS
═══════════════════════════════════════════════════════════════════════════════

SEARCH for:
- "{university_name} cost of attendance 2024-2025"
- "{university_name} merit scholarships"
- "{university_name} Regents Scholarship full ride"
- "{university_name} need-blind meets 100% need"

COLLECT: Tuition model, in-state/out-of-state COA, aid philosophy, average aid amounts, 5-7 scholarships with amounts, benefits, and application methods.

═══════════════════════════════════════════════════════════════════════════════
RESEARCH PHASE 9: CREDIT POLICIES
═══════════════════════════════════════════════════════════════════════════════

SEARCH for:
- "{university_name} AP credit policy"
- "{university_name} IB credit policy"
- "{university_name} transfer articulation ASSIST"

COLLECT: AP/IB policies with score requirements and exceptions, transfer credit tools and restrictions.

═══════════════════════════════════════════════════════════════════════════════
RESEARCH PHASE 10: STUDENT INSIGHTS (CROWDSOURCED)
═══════════════════════════════════════════════════════════════════════════════

SEARCH for:
- "site:niche.com {university_name} reviews"
- "site:reddit.com r/ApplyingToCollege {university_name} accepted"
- "site:reddit.com {university_name} essays that worked"

COLLECT: What it takes (3-5 factors), common activities (5-10), essay tips (3-5), red flags (2-3).

═══════════════════════════════════════════════════════════════════════════════
RESEARCH PHASE 11: OUTCOMES & ROI (MANDATORY)
═══════════════════════════════════════════════════════════════════════════════

SEARCH for:
- "site:collegescorecard.ed.gov {university_name}"
- "{university_name} Common Data Set Section B retention graduation"
- "{university_name} career center top employers"
- "LinkedIn {university_name} alumni companies"

COLLECT: Median earnings 10yr (from College Scorecard ONLY), employment rate, grad school rate, top employers (5-7), loan default rate, freshman retention rate, 4-year and 6-year graduation rates.

═══════════════════════════════════════════════════════════════════════════════
OUTPUT FORMAT - Return ONLY valid JSON matching this structure:
═══════════════════════════════════════════════════════════════════════════════

{{
  "_id": "snake_case_university_name",
  "metadata": {{"official_name": "Full Name", "location": {{"city": "City", "state": "State", "type": "Public/Private"}}, "last_updated": "YYYY-MM-DD", "report_source_files": []}},
  "strategic_profile": {{"executive_summary": "2-3 sentences", "market_position": "Public Ivy/Elite Private/etc", "admissions_philosophy": "Holistic/Numbers-focused", "us_news_rank": integer, "analyst_takeaways": [{{"category": "Selectivity/Financial/Academic/Culture", "insight": "data-driven finding", "implication": "what it means"}}], "campus_dynamics": {{"social_environment": "description", "transportation_impact": "description", "research_impact": "description"}}}},
  "admissions_data": {{
    "current_status": {{"overall_acceptance_rate": float, "in_state_acceptance_rate": float, "out_of_state_acceptance_rate": float, "international_acceptance_rate": float, "transfer_acceptance_rate": float, "admits_class_size": int, "is_test_optional": boolean, "test_policy_details": "policy", "early_admission_stats": [{{"plan_type": "ED/EA", "applications": int, "admits": int, "acceptance_rate": float, "class_fill_percentage": float}}]}},
    "longitudinal_trends": [{{"year": int, "cycle_name": "Class of XXXX", "applications_total": int, "admits_total": int, "enrolled_total": int, "acceptance_rate_overall": float, "acceptance_rate_in_state": float, "acceptance_rate_out_of_state": float, "yield_rate": float, "waitlist_stats": {{"year": int, "offered_spots": int, "accepted_spots": int, "admitted_from_waitlist": int, "waitlist_admit_rate": float, "is_waitlist_ranked": boolean}}, "notes": ""}}],
    "admitted_student_profile": {{"gpa": {{"weighted_middle_50": "X.XX-X.XX", "unweighted_middle_50": "X.XX-X.XX", "average_weighted": float, "notes": ""}}, "testing": {{"sat_composite_middle_50": "XXXX-XXXX", "sat_reading_middle_50": "", "sat_math_middle_50": "", "act_composite_middle_50": "XX-XX", "submission_rate": float, "policy_note": ""}}, "demographics": {{"first_gen_percentage": float, "legacy_percentage": float, "international_percentage": float, "geographic_breakdown": [{{"region": "name", "percentage": float}}], "gender_breakdown": {{"men": {{"applicants": int, "admits": int, "acceptance_rate": float}}, "women": {{"applicants": int, "admits": int, "acceptance_rate": float}}}}, "racial_breakdown": {{"white": float, "black_african_american": float, "hispanic_latino": float, "asian": float, "native_american_alaskan": float, "pacific_islander": float, "two_or_more_races": float, "unknown": float, "non_resident_alien": float}}, "religious_affiliation": null}}}}
  }},
  "academic_structure": {{"structure_type": "Colleges/Schools", "colleges": [{{"name": "College Name", "admissions_model": "Direct Admit/Pre-Major", "acceptance_rate_estimate": float, "is_restricted_or_capped": boolean, "strategic_fit_advice": "who should apply", "housing_profile": "description", "student_archetype": "type", "majors": [{{"name": "Major", "degree_type": "B.S./B.A.", "is_impacted": boolean, "acceptance_rate": "X%", "average_gpa_admitted": float, "prerequisite_courses": [], "minimum_gpa_to_declare": float, "weeder_courses": ["Course Name"], "special_requirements": "", "admissions_pathway": "Direct Admit/Pre-Major", "internal_transfer_allowed": boolean, "direct_admit_only": boolean, "internal_transfer_gpa": float, "curriculum": {{"core_courses": ["CS 101 Intro to Programming"], "electives": ["CS 310 ML"], "total_units": 120, "major_units": 60}}, "notable_professors": ["Dr. Name (Specialty)"], "notes": ""}}]}}], "minors_certificates": []}},
  "application_process": {{"platforms": [], "application_deadlines": [{{"plan_type": "ED/RD", "date": "YYYY-MM-DD", "is_binding": boolean, "notes": ""}}], "supplemental_requirements": [{{"target_program": "All", "requirement_type": "Essays", "deadline": "", "details": ""}}], "holistic_factors": {{"primary_factors": [], "secondary_factors": [], "essay_importance": "Critical/High/Moderate", "demonstrated_interest": "Important/Considered/Not Considered", "interview_policy": "Required/Recommended/Not Offered", "legacy_consideration": "Strong/Moderate/Minimal/None", "first_gen_boost": "Strong/Moderate/Minimal/None", "specific_differentiators": ""}}}},
  "application_strategy": {{"major_selection_tactics": [], "college_ranking_tactics": [], "alternate_major_strategy": ""}},
  "financials": {{"tuition_model": "policy", "cost_of_attendance_breakdown": {{"academic_year": "YYYY-YYYY", "in_state": {{"tuition": float, "total_coa": float, "housing": float}}, "out_of_state": {{"tuition": float, "total_coa": float, "supplemental_tuition": float}}}}, "aid_philosophy": "100% Need Met/Need-Blind", "average_need_based_aid": float, "average_merit_aid": float, "percent_receiving_aid": float, "scholarships": [{{"name": "Name", "type": "Merit/Need", "amount": "$X,XXX", "deadline": "", "benefits": "", "application_method": "Automatic/Separate"}}]}},
  "credit_policies": {{"philosophy": "Generous/Strict", "ap_policy": {{"general_rule": "rule", "exceptions": [], "usage": "how used"}}, "ib_policy": {{"general_rule": "rule", "diploma_bonus": boolean}}, "transfer_articulation": {{"tools": [], "restrictions": ""}}}},
  "student_insights": {{"what_it_takes": [], "common_activities": [], "essay_tips": [], "red_flags": [], "insights": []}},
  "outcomes": {{"median_earnings_10yr": integer, "employment_rate_2yr": float, "grad_school_rate": float, "top_employers": [], "loan_default_rate": float}},
  "student_retention": {{"freshman_retention_rate": float, "graduation_rate_4_year": float, "graduation_rate_6_year": float}}
}}

═══════════════════════════════════════════════════════════════════════════════
ANTI-HALLUCINATION RULES (CRITICAL)
═══════════════════════════════════════════════════════════════════════════════

1. median_earnings_10yr must come from College Scorecard ONLY. If not found, use null.
2. DO NOT invent weeder course names. Only include if explicitly mentioned as "weed-out" or "filter" courses.
3. DO NOT guess minimum_gpa_to_declare. Only include if found on official departmental pages.
4. DO NOT estimate acceptance rates. Use official sources only.
5. For waitlist data, if hidden, note "Waitlist data not publicly disclosed" in notes.
6. Top employers must come from official Career Center or LinkedIn Alumni data.
7. For curriculum, only include REAL course names from the university catalog. DO NOT INVENT COURSES.
8. For notable_professors, only include REAL faculty names from department websites. DO NOT INVENT NAMES.
9. If curriculum or professors are not found for a major, set curriculum: null and notable_professors: [].
10. Use null for ANY value you cannot verify from official sources.

═══════════════════════════════════════════════════════════════════════════════
RESEARCH THE UNIVERSITY: {university_name}
═══════════════════════════════════════════════════════════════════════════════
'''


def create_slug(university_name: str) -> str:
    """Create a URL-safe slug from university name."""
    slug = university_name.lower()
    slug = slug.replace(" ", "_")
    slug = slug.replace(",", "")
    slug = slug.replace("-", "_")
    slug = "".join(c for c in slug if c.isalnum() or c == "_")
    slug = "_".join(filter(None, slug.split("_")))
    return slug


def extract_json_from_response(text: str, output_path: Path = None) -> dict:
    """Extract JSON from response text, handling markdown code blocks.
    
    If extraction fails, saves raw response to a debug file.
    """
    # Try direct JSON parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Try to extract from markdown code block (```json)
    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        if end > start:
            json_text = text[start:end].strip()
            try:
                return json.loads(json_text)
            except json.JSONDecodeError:
                pass
    
    # Try to find all code blocks and check each for JSON
    import re
    code_blocks = re.findall(r'```(?:\w*)\n?(.*?)```', text, re.DOTALL)
    for block in code_blocks:
        block = block.strip()
        if block.startswith('{'):
            try:
                return json.loads(block)
            except json.JSONDecodeError:
                continue
    
    # Try to find JSON object in text (find matching braces)
    start = text.find("{")
    if start >= 0:
        # Find matching closing brace
        brace_count = 0
        in_string = False
        escape_next = False
        
        for i, char in enumerate(text[start:], start):
            if escape_next:
                escape_next = False
                continue
            if char == '\\':
                escape_next = True
                continue
            if char == '"' and not escape_next:
                in_string = not in_string
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_text = text[start:i+1]
                        try:
                            return json.loads(json_text)
                        except json.JSONDecodeError:
                            break
    
    # Last resort: try rfind for simple case
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass
    
    # Save raw response for debugging
    if output_path:
        raw_path = output_path.with_suffix('.raw.txt')
        with open(raw_path, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"\n⚠️  Raw response saved to: {raw_path}")
        print(f"   Response length: {len(text)} characters")
        print(f"   First 500 chars: {text[:500]}...")
    
    raise ValueError("Could not extract valid JSON from response. Check the .raw.txt file.")


def start_research(api_key: str, prompt: str, verbose: bool = False) -> str:
    """Start a Deep Research task and return the interaction ID."""
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }
    
    payload = {
        "input": prompt,
        "agent": DEEP_RESEARCH_AGENT,
        "background": True
    }
    
    if verbose:
        print(f"📡 Starting research with agent: {DEEP_RESEARCH_AGENT}")
    
    response = requests.post(INTERACTIONS_API_URL, headers=headers, json=payload, timeout=60)
    
    if response.status_code != 200:
        error_detail = response.text[:500] if response.text else "No details"
        raise RuntimeError(f"API error {response.status_code}: {error_detail}")
    
    result = response.json()
    interaction_id = result.get("id") or result.get("name", "").split("/")[-1]
    
    if not interaction_id:
        raise RuntimeError(f"No interaction ID in response: {result}")
    
    return interaction_id


def poll_research(api_key: str, interaction_id: str, verbose: bool = False) -> dict:
    """Poll for research results until complete."""
    headers = {
        "x-goog-api-key": api_key
    }
    
    url = f"{INTERACTIONS_API_URL}/{interaction_id}"
    start_time = time.time()
    dots = 0
    
    while True:
        response = requests.get(url, headers=headers, timeout=60)
        
        if response.status_code != 200:
            error_detail = response.text[:500] if response.text else "No details"
            raise RuntimeError(f"Poll error {response.status_code}: {error_detail}")
        
        result = response.json()
        status = result.get("status", "unknown")
        
        if status == "completed":
            elapsed = time.time() - start_time
            if verbose:
                print(f"\n✅ Research completed in {elapsed:.1f} seconds")
            
            # Extract text from outputs
            outputs = result.get("outputs", [])
            if outputs:
                return outputs[-1].get("text", "")
            else:
                raise ValueError("No outputs in completed interaction")
                
        elif status == "failed":
            error_msg = result.get("error", "Unknown error")
            raise RuntimeError(f"Research failed: {error_msg}")
        
        # Show progress
        if verbose:
            dots = (dots + 1) % 4
            elapsed = time.time() - start_time
            print(f"\r⏳ Researching{'.' * dots}{' ' * (3 - dots)} ({elapsed:.0f}s, status: {status})", end="", flush=True)
        
        time.sleep(POLL_INTERVAL)


def run_deep_research(university_name: str, api_key: str, output_path: Path = None, verbose: bool = False) -> dict:
    """
    Run Deep Research API to generate university profile.
    
    Args:
        university_name: Name of the university to research
        api_key: Gemini API key
        output_path: Path where output will be saved (for debug file on failure)
        verbose: Whether to print progress updates
    
    Returns:
        Dictionary containing the university profile
    """
    prompt = get_research_prompt(university_name)
    
    if verbose:
        print(f"\n🔬 Starting Deep Research for: {university_name}")
        print("-" * 50)
    
    # Start research
    interaction_id = start_research(api_key, prompt, verbose)
    
    if verbose:
        print(f"✅ Research started with ID: {interaction_id}")
        print(f"⏳ This may take 2-5 minutes...")
    
    # Poll for results
    raw_text = poll_research(api_key, interaction_id, verbose)
    
    # Extract JSON (pass output_path for debug file if extraction fails)
    result = extract_json_from_response(raw_text, output_path)
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Generate university profiles using Google Gemini Deep Research API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 deep_research_cli.py "Stanford University"
    python3 deep_research_cli.py "MIT" --output mit.json
    python3 deep_research_cli.py "Duke University" --verbose
    
Environment:
    GEMINI_API_KEY must be set (use: export GEMINI_API_KEY="your-key")
        """
    )
    
    parser.add_argument(
        "university",
        help="Name of the university to research (e.g., 'Stanford University', 'MIT')"
    )
    
    parser.add_argument(
        "--output", "-o",
        help="Output JSON file path (default: research/{slug}.json)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show progress updates"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print prompt without running research"
    )
    
    args = parser.parse_args()
    
    # Check for API key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY environment variable not set")
        print("   Set it with: export GEMINI_API_KEY='your-api-key'")
        print("   Or fetch from Secret Manager:")
        print("   export GEMINI_API_KEY=$(gcloud secrets versions access latest --secret=gemini-api-key)")
        sys.exit(1)
    
    # Determine output path
    slug = create_slug(args.university)
    if args.output:
        output_path = Path(args.output)
    else:
        output_dir = Path(__file__).parent / "research"
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f"{slug}.json"
    
    # Dry run mode
    if args.dry_run:
        print("=" * 60)
        print("DRY RUN - Prompt that would be sent:")
        print("=" * 60)
        print(get_research_prompt(args.university))
        print("=" * 60)
        print(f"Output would be saved to: {output_path}")
        return
    
    try:
        # Run research
        print(f"\n🎓 University Profile Deep Research")
        print(f"   University: {args.university}")
        print(f"   Output: {output_path}")
        
        result = run_deep_research(args.university, api_key, output_path=output_path, verbose=args.verbose)
        
        # Ensure _id is set
        if "_id" not in result or not result["_id"]:
            result["_id"] = slug
        
        # Save result
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Profile saved to: {output_path}")
        
        # Print summary
        if "metadata" in result:
            name = result["metadata"].get("official_name", args.university)
            print(f"\n📋 Summary for {name}:")
            if "strategic_profile" in result:
                sp = result["strategic_profile"]
                if sp.get("us_news_rank"):
                    print(f"   📊 US News Rank: #{sp['us_news_rank']}")
                if sp.get("market_position"):
                    print(f"   🏛️  Market Position: {sp['market_position']}")
            if "admissions_data" in result:
                ad = result["admissions_data"].get("current_status", {})
                if ad.get("overall_acceptance_rate"):
                    print(f"   📈 Acceptance Rate: {ad['overall_acceptance_rate']}%")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Research cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
