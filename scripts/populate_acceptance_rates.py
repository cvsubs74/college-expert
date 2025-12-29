#!/usr/bin/env python3
"""
Script to populate missing acceptance rates for universities in Elasticsearch.
Uses known acceptance rates from web scraping/manual research.
"""
import json
import os
import requests
from typing import Optional

# Known acceptance rates for universities missing data (2024-2025 data)
# Source: US News, College Scorecard, University websites
KNOWN_ACCEPTANCE_RATES = {
    "arizona_state_university": 90.2,
    "university_of_hawaii_at_manoa": 88.5,
    "university_of_arkansas": 79.5,
    "kansas_state_university": 94.5,
    "university_of_missouri": 84.0,
    "oklahoma_state_university": 73.8,
    "university_of_kansas": 90.0,
    "depaul_university": 72.0,
    "university_of_nebraska_lincoln": 79.6,
    "ohio_university": 87.5,
    "university_of_cincinnati": 89.0,
    "university_of_la_verne": 53.0,
    "university_of_massachusetts_lowell": 89.0,
    "seton_hall_university": 79.0,
    "saint_louis_university": 58.0,
    "university_of_san_francisco": 69.0,
    "university_of_denver": 74.0,
    "loyola_marymount_university": 47.0,
    "university_of_the_pacific": 75.0,
    "university_of_dayton": 84.0,
    "chapman_university": 57.0,
    "gonzaga_university": 73.0,
    "american_university": 41.0,
    "baylor_university": 63.0,
    "university_of_miami": 19.0,
    "wake_forest_university": 21.0,
    "tufts_university": 10.0,
    "brandeis_university": 34.0,
    "university_of_rochester": 39.0,
    "case_western_reserve_university": 30.0,
    "lehigh_university": 32.0,
    "villanova_university": 23.0,
    "northeastern_university": 6.7,
    "pepperdine_university": 49.0,
    "santa_clara_university": 48.0,
    "university_of_san_diego": 53.5,
    "loyola_university_maryland": 75.0,
    "fordham_university": 46.0,
    "drexel_university": 80.0,
    "temple_university": 80.0,
    "university_of_oregon": 90.0,
    "university_of_colorado_boulder": 79.0,
    "university_of_iowa": 86.0,
    "indiana_university_bloomington": 85.0,
    "purdue_university": 53.0,
    "university_of_utah": 88.5,
    "university_of_vermont": 67.0,
    "stony_brook_university": 49.0,
    "binghamton_university": 44.0,
    "suny_buffalo": 72.0,
    # Additional universities (batch 2)
    "clarkson_university": 74.0,
    "university_of_st_thomas_minnesota": 82.0,
    "colorado_state_university": 90.0,
    "adelphi_university": 77.0,
    "university_of_alabama": 80.0,
    "university_of_central_florida": 41.0,
    "university_of_kentucky": 96.0,
    "the_catholic_university_of_america": 85.0,
    "university_of_california_merced": 89.0,
    "simmons_university": 85.0,
    "duquesne_university": 90.0,
    "university_of_new_hampshire": 91.0,
    "university_of_tennessee_knoxville": 79.0,
    "hofstra_university": 80.0,
    "rochester_institute_of_technology": 73.0,
    "university_of_tulsa": 73.0,
    "university_of_rhode_island": 88.0,
    "texas_a_m_university": 63.0,
    "colorado_school_of_mines": 52.0,
    "missouri_university_of_science_and_technology": 83.0,
    "iowa_state_university": 92.0,
    "university_of_louisville": 74.0,
    "seattle_university": 79.0,
    "clark_university": 60.0,
    "elon_university": 72.0,
    "loyola_university_chicago": 68.0,
    "new_jersey_institute_of_technology": 66.0,
    "university_of_oklahoma": 83.0,
    "worcester_polytechnic_institute": 55.0,
    "yeshiva_university": 52.0,
}

# API endpoint
KB_UNIVERSITIES_URL = os.environ.get(
    "KNOWLEDGE_BASE_UNIVERSITIES_URL",
    "https://knowledge-base-manager-universities-pfnwjfp26a-ue.a.run.app"
)


def get_universities_with_missing_rates() -> list:
    """Fetch all universities that have null acceptance rates."""
    response = requests.get(KB_UNIVERSITIES_URL, timeout=60)
    response.raise_for_status()
    data = response.json()
    
    missing = []
    if data.get("success") and data.get("universities"):
        for uni in data["universities"]:
            if uni.get("acceptance_rate") is None or uni.get("soft_fit_category") == "UNKNOWN":
                missing.append({
                    "university_id": uni.get("university_id"),
                    "official_name": uni.get("official_name"),
                    "current_rate": uni.get("acceptance_rate"),
                    "current_category": uni.get("soft_fit_category")
                })
    return missing


def update_university_acceptance_rate(university_id: str, acceptance_rate: float) -> dict:
    """
    Update a university's acceptance rate in Elasticsearch.
    This requires re-ingesting the university with the updated data.
    """
    # First, get the current university data
    response = requests.get(f"{KB_UNIVERSITIES_URL}/get?university_id={university_id}", timeout=30)
    if not response.ok:
        return {"success": False, "error": f"Failed to fetch university: {response.text}"}
    
    uni_data = response.json()
    if not uni_data.get("success"):
        return {"success": False, "error": uni_data.get("error", "Unknown error")}
    
    # Update the acceptance rate in the profile
    profile = uni_data.get("profile", {})
    
    # Ensure admissions_data structure exists
    if "admissions_data" not in profile:
        profile["admissions_data"] = {}
    if "current_status" not in profile["admissions_data"]:
        profile["admissions_data"]["current_status"] = {}
    
    # Set the acceptance rate
    profile["admissions_data"]["current_status"]["overall_acceptance_rate"] = acceptance_rate
    
    # Add the _id field for re-ingestion
    profile["_id"] = university_id
    
    # Re-ingest the university
    ingest_response = requests.post(
        KB_UNIVERSITIES_URL,
        json=profile,
        timeout=120,
        headers={"Content-Type": "application/json"}
    )
    
    if ingest_response.ok:
        result = ingest_response.json()
        return {
            "success": True,
            "university_id": university_id,
            "acceptance_rate": acceptance_rate,
            "new_category": result.get("soft_fit_category")
        }
    else:
        return {"success": False, "error": ingest_response.text}


def main():
    print("=" * 60)
    print("Populating Missing Acceptance Rates")
    print("=" * 60)
    
    # Get universities with missing rates
    missing = get_universities_with_missing_rates()
    print(f"\nFound {len(missing)} universities with missing/null acceptance rates")
    
    if not missing:
        print("No universities need updating!")
        return
    
    # Update universities with known rates
    updated = 0
    skipped = 0
    failed = 0
    
    for uni in missing:
        uni_id = uni["university_id"]
        
        if uni_id in KNOWN_ACCEPTANCE_RATES:
            rate = KNOWN_ACCEPTANCE_RATES[uni_id]
            print(f"\nUpdating {uni_id}: {rate}%")
            
            result = update_university_acceptance_rate(uni_id, rate)
            
            if result.get("success"):
                print(f"  ✓ Updated to {rate}% -> {result.get('new_category')}")
                updated += 1
            else:
                print(f"  ✗ Failed: {result.get('error')}")
                failed += 1
        else:
            print(f"  - Skipping {uni_id} (no known rate)")
            skipped += 1
    
    print("\n" + "=" * 60)
    print(f"Summary:")
    print(f"  Updated: {updated}")
    print(f"  Skipped (no known rate): {skipped}")
    print(f"  Failed: {failed}")
    print("=" * 60)
    
    if skipped > 0:
        print("\nUniversities still needing rates:")
        for uni in missing:
            if uni["university_id"] not in KNOWN_ACCEPTANCE_RATES:
                print(f"  - {uni['university_id']}: {uni['official_name']}")


if __name__ == "__main__":
    main()
