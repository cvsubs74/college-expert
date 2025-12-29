#!/usr/bin/env python3
"""
Script to populate missing locations for universities in Elasticsearch.
Uses known location data for universities.
"""
import json
import os
import requests
from typing import Optional

# Known locations for universities (city, state)
KNOWN_LOCATIONS = {
    "university_of_arkansas": {"city": "Fayetteville", "state": "Arkansas"},
    "kansas_state_university": {"city": "Manhattan", "state": "Kansas"},
    "university_of_missouri": {"city": "Columbia", "state": "Missouri"},
    "oklahoma_state_university": {"city": "Stillwater", "state": "Oklahoma"},
    "university_of_kansas": {"city": "Lawrence", "state": "Kansas"},
    "depaul_university": {"city": "Chicago", "state": "Illinois"},
    "university_of_nebraska_lincoln": {"city": "Lincoln", "state": "Nebraska"},
    "ohio_university": {"city": "Athens", "state": "Ohio"},
    "university_of_cincinnati": {"city": "Cincinnati", "state": "Ohio"},
    "university_of_la_verne": {"city": "La Verne", "state": "California"},
    "university_of_massachusetts_lowell": {"city": "Lowell", "state": "Massachusetts"},
    "seton_hall_university": {"city": "South Orange", "state": "New Jersey"},
    "arizona_state_university": {"city": "Tempe", "state": "Arizona"},
    "saint_louis_university": {"city": "St. Louis", "state": "Missouri"},
    "university_of_dayton": {"city": "Dayton", "state": "Ohio"},
    "university_of_san_francisco": {"city": "San Francisco", "state": "California"},
    "university_of_the_pacific": {"city": "Stockton", "state": "California"},
    "university_of_central_florida": {"city": "Orlando", "state": "Florida"},
    "university_of_hawaii_at_manoa": {"city": "Honolulu", "state": "Hawaii"},
    "university_of_st_thomas_minnesota": {"city": "St. Paul", "state": "Minnesota"},
    "university_of_kentucky": {"city": "Lexington", "state": "Kentucky"},
    "university_of_alabama": {"city": "Tuscaloosa", "state": "Alabama"},
    "colorado_state_university": {"city": "Fort Collins", "state": "Colorado"},
    "clarkson_university": {"city": "Potsdam", "state": "New York"},
    "adelphi_university": {"city": "Garden City", "state": "New York"},
    "rochester_institute_of_technology": {"city": "Rochester", "state": "New York"},
    "the_catholic_university_of_america": {"city": "Washington", "state": "District of Columbia"},
    "university_of_tennessee_knoxville": {"city": "Knoxville", "state": "Tennessee"},
    "university_of_california_merced": {"city": "Merced", "state": "California"},
    "university_of_new_hampshire": {"city": "Durham", "state": "New Hampshire"},
    "university_of_tulsa": {"city": "Tulsa", "state": "Oklahoma"},
    "simmons_university": {"city": "Boston", "state": "Massachusetts"},
    "hofstra_university": {"city": "Hempstead", "state": "New York"},
    "iowa_state_university": {"city": "Ames", "state": "Iowa"},
    "university_of_louisville": {"city": "Louisville", "state": "Kentucky"},
    "missouri_university_of_science_and_technology": {"city": "Rolla", "state": "Missouri"},
    "colorado_school_of_mines": {"city": "Golden", "state": "Colorado"},
    "university_of_rhode_island": {"city": "Kingston", "state": "Rhode Island"},
    "elon_university": {"city": "Elon", "state": "North Carolina"},
    "texas_a_m_university": {"city": "College Station", "state": "Texas"},
    "duquesne_university": {"city": "Pittsburgh", "state": "Pennsylvania"},
    "seattle_university": {"city": "Seattle", "state": "Washington"},
    "clark_university": {"city": "Worcester", "state": "Massachusetts"},
    "loyola_university_chicago": {"city": "Chicago", "state": "Illinois"},
    "new_jersey_institute_of_technology": {"city": "Newark", "state": "New Jersey"},
    "university_of_oklahoma": {"city": "Norman", "state": "Oklahoma"},
    "worcester_polytechnic_institute": {"city": "Worcester", "state": "Massachusetts"},
    "yeshiva_university": {"city": "New York", "state": "New York"},
}

# API endpoint
KB_UNIVERSITIES_URL = os.environ.get(
    "KNOWLEDGE_BASE_UNIVERSITIES_URL",
    "https://knowledge-base-manager-universities-pfnwjfp26a-ue.a.run.app"
)


def get_universities_with_missing_locations() -> list:
    """Fetch all universities that have null/empty locations."""
    response = requests.get(KB_UNIVERSITIES_URL, timeout=60)
    response.raise_for_status()
    data = response.json()
    
    missing = []
    if data.get("success") and data.get("universities"):
        for uni in data["universities"]:
            location = uni.get("location") or {}
            if not location.get("city"):
                missing.append({
                    "university_id": uni.get("university_id"),
                    "official_name": uni.get("official_name"),
                    "current_location": location
                })
    return missing


def update_university_location(university_id: str, location: dict) -> dict:
    """
    Update a university's location in Elasticsearch.
    """
    # First, get the current university data
    response = requests.get(f"{KB_UNIVERSITIES_URL}/get?university_id={university_id}", timeout=30)
    if not response.ok:
        return {"success": False, "error": f"Failed to fetch university: {response.text}"}
    
    uni_data = response.json()
    if not uni_data.get("success"):
        return {"success": False, "error": uni_data.get("error", "Unknown error")}
    
    # Update the location in the profile
    profile = uni_data.get("profile", {})
    
    # Ensure metadata structure exists
    if "metadata" not in profile:
        profile["metadata"] = {}
    
    # Set the location
    profile["metadata"]["location"] = location
    
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
            "location": location
        }
    else:
        return {"success": False, "error": ingest_response.text}


def main():
    print("=" * 60)
    print("Populating Missing University Locations")
    print("=" * 60)
    
    # Get universities with missing locations
    missing = get_universities_with_missing_locations()
    print(f"\nFound {len(missing)} universities with missing locations")
    
    if not missing:
        print("No universities need updating!")
        return
    
    # Update universities with known locations
    updated = 0
    skipped = 0
    failed = 0
    
    for uni in missing:
        uni_id = uni["university_id"]
        
        if uni_id in KNOWN_LOCATIONS:
            location = KNOWN_LOCATIONS[uni_id]
            print(f"\nUpdating {uni_id}: {location['city']}, {location['state']}")
            
            result = update_university_location(uni_id, location)
            
            if result.get("success"):
                print(f"  ✓ Updated location")
                updated += 1
            else:
                print(f"  ✗ Failed: {result.get('error')}")
                failed += 1
        else:
            print(f"  - Skipping {uni_id} (no known location)")
            skipped += 1
    
    print("\n" + "=" * 60)
    print(f"Summary:")
    print(f"  Updated: {updated}")
    print(f"  Skipped (no known location): {skipped}")
    print(f"  Failed: {failed}")
    print("=" * 60)


if __name__ == "__main__":
    main()
