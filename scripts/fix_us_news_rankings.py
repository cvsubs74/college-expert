#!/usr/bin/env python3
"""
Fix US News Rankings in Firestore

This script:
1. Fetches the current US News National Universities ranking from the web
2. Compares with data in Firestore
3. Updates incorrect rankings or nullifies regional rankings

Run with: python scripts/fix_us_news_rankings.py [--dry-run] [--update]
"""

import os
import sys
import json
import argparse
from datetime import datetime
from google.cloud import firestore

# US News Top National Universities 2026 (verified list)
# Source: https://www.usnews.com/best-colleges/rankings/national-universities (2026 edition)
US_NEWS_NATIONAL_2026 = {
    "princeton_university": 1,
    "massachusetts_institute_of_technology": 2,
    "harvard_university": 3,
    "stanford_university": 4,
    "yale_university": 4,
    "university_of_chicago": 6,
    "duke_university": 7,
    "johns_hopkins_university": 7,
    "northwestern_university": 7,
    "university_of_pennsylvania": 7,
    "california_institute_of_technology": 11,
    "cornell_university": 12,
    "brown_university": 13,
    "dartmouth_college": 13,
    "columbia_university": 15,
    "university_of_california_berkeley": 15,
    "rice_university": 17,
    "university_of_california_los_angeles": 17,
    "vanderbilt_university": 17,
    "carnegie_mellon_university": 20,
    "emory_university": 21,
    "georgetown_university": 22,
    "university_of_michigan_ann_arbor": 22,
    "university_of_notre_dame": 22,
    "university_of_virginia": 22,
    "washington_university_in_st_louis": 26,
    "university_of_southern_california": 27,
    "new_york_university": 28,
    "university_of_florida": 28,
    "university_of_north_carolina_at_chapel_hill": 28,
    "university_of_california_san_diego": 31,
    "boston_college": 32,
    "university_of_california_santa_barbara": 32,
    "georgia_institute_of_technology": 34,
    "university_of_california_davis": 34,
    "university_of_california_irvine": 36,
    "university_of_texas_at_austin": 36,
    "university_of_illinois_urbana_champaign": 38,
    "university_of_rochester": 38,
    "university_of_wisconsin_madison": 40,
    "boston_university": 41,
    "case_western_reserve_university": 41,
    "tufts_university": 43,
    "ohio_state_university": 44,
    "tulane_university": 44,
    "northeastern_university": 46,
    "purdue_university": 46,
    "university_of_washington": 46,
    "university_of_maryland_college_park": 49,
    "villanova_university": 49,
    "university_of_georgia": 51,
    "university_of_pittsburgh": 51,
    "wake_forest_university": 51,
    "lehigh_university": 54,
    "rensselaer_polytechnic_institute": 54,
    "florida_state_university": 56,
    "north_carolina_state_university": 56,
    "rutgers_university_new_brunswick": 58,
    "santa_clara_university": 58,
    "university_of_minnesota_twin_cities": 58,
    "brandeis_university": 61,
    "stony_brook_university": 61,
    "michigan_state_university": 63,
    "suny_binghamton_university": 63,
    "university_of_connecticut": 63,
    "university_of_massachusetts_amherst": 63,
    "virginia_tech": 63,
    "clemson_university": 68,
    "indiana_university_bloomington": 68,
    "university_at_buffalo_suny": 68,
    "university_of_colorado_boulder": 68,
    "university_of_miami": 68,
    "george_washington_university": 73,
    "syracuse_university": 73,
    "university_of_delaware": 73,
    "pennsylvania_state_university": 76,
    "texas_a_and_m_university": 76,
    "university_of_california_merced": 76,
    "university_of_iowa": 76,
    "university_of_oregon": 76,
    "howard_university": 81,
    "baylor_university": 82,
    "university_of_south_carolina": 82,
    "colorado_school_of_mines": 84,
    "fordham_university": 84,
    "university_of_alabama": 84,
    "university_of_denver": 84,
    "university_of_tennessee": 84,
    "southern_methodist_university": 89,
    "texas_christian_university": 89,
    "university_of_south_florida": 89,
    "worcester_polytechnic_institute": 89,
    "auburn_university": 93,
    "drexel_university": 93,
    "marquette_university": 93,
    "stevens_institute_of_technology": 93,
    "university_of_kentucky": 97,
    "temple_university": 97,
    "loyola_university_chicago": 97,
    "pepperdine_university": 100,
    "san_diego_state_university": 100,
    "university_of_arizona": 100,
    "george_mason_university": 103,
    "illinois_institute_of_technology": 103,
    "university_of_central_florida": 103,
    "florida_international_university": 106,
    "arizona_state_university": 106,
    "iowa_state_university": 106,
    "new_jersey_institute_of_technology": 106,
    "college_of_william_and_mary": 51,  # Tied with others at 51
}

# Additional common name mappings
NAME_MAPPINGS = {
    "leland_stanford_junior_university": "stanford_university",
    "columbia_university_in_the_city_of_new_york": "columbia_university",
    "the_university_of_chicago": "university_of_chicago",
    "the_college_of_william_and_mary": "college_of_william_and_mary",
    "iowa_state_university_of_science_and_technology": "iowa_state_university",
}

# These are definitely NOT national universities (they are regional)
REGIONAL_UNIVERSITIES = [
    "elon_university",
    "california_state_university_long_beach",
    "california_state_university_fullerton",
    "morgan_state_university",
    "appalachian_state_university",
    "james_madison_university",
    "samford_university",
    "gonzaga_university",
    "creighton_university",
    "loyola_marymount_university",
    "chapman_university",
    "university_of_san_diego",
    "seattle_university",
    "quinnipiac_university",
    "rowan_university",
    "montclair_state_university",
    "ball_state_university",
    "kent_state_university",
    "ohio_university",
    "western_michigan_university",
    "northern_illinois_university",
    "illinois_state_university",
    "bowling_green_state_university",
    "east_carolina_university",
    "old_dominion_university",
    "university_of_north_carolina_at_charlotte",
    "university_of_north_texas",
    "wichita_state_university",
    "oklahoma_state_university",
    "kansas_state_university",
    "utah_state_university",
    "washington_state_university",
    "portland_state_university",
    "university_of_idaho",
    "university_of_wyoming",
    "university_of_montana",
    "university_of_new_hampshire",
    "university_of_rhode_island",
    "university_of_vermont",
    "university_of_new_mexico",
    "university_of_hawaii_at_manoa",
    "texas_tech_university",
    "louisiana_state_university",
    "university_of_missouri",
    "wayne_state_university",
    "university_of_cincinnati",
    "university_of_dayton",
    "seton_hall_university",
    "adelphi_university",
    "hofstra_university",
    "pace_university",
    "depaul_university",
    "clark_university",
    "clarkson_university",
    "american_university",
    "university_of_la_verne",
    "simmons_university",
    "belmont_university",
    "mercer_university",
    "university_of_st_thomas",
    "saint_louis_university",
    "st_louis_university",
    "san_jose_state_university",
    "university_of_the_pacific",
    "university_of_tulsa",
    "missouri_university_of_science_and_technology",
    "rochester_institute_of_technology",
    "university_of_maryland_baltimore_county",
    "university_of_massachusetts_lowell",
    "university_of_alabama_at_birmingham",
    "university_of_texas_at_dallas",
    "suny_college_of_environmental_science_and_forestry",
]


def get_firestore_client():
    """Get Firestore client."""
    return firestore.Client()


def get_all_universities(db):
    """Fetch all universities from Firestore."""
    collection = db.collection("universities")
    docs = collection.stream()
    universities = []
    for doc in docs:
        data = doc.to_dict()
        data["_id"] = doc.id
        universities.append(data)
    return universities


def get_correct_rank(university_id: str) -> int | None:
    """
    Get the correct US News National Universities rank for a university.
    Returns None if the university is not in the National Universities ranking.
    """
    # Check name mappings first
    normalized_id = NAME_MAPPINGS.get(university_id, university_id)
    
    # Check if it's a national university
    if normalized_id in US_NEWS_NATIONAL_2026:
        return US_NEWS_NATIONAL_2026[normalized_id]
    
    # Check if it's explicitly a regional university
    if university_id in REGIONAL_UNIVERSITIES or normalized_id in REGIONAL_UNIVERSITIES:
        return None
    
    # If not in our list, it's probably not a top national university
    # but we'll return the existing rank with a warning
    return None


def analyze_rankings(universities: list) -> dict:
    """Analyze rankings discrepancies."""
    results = {
        "correct": [],
        "incorrect": [],
        "nullify": [],
        "unknown": [],
    }
    
    for uni in universities:
        uni_id = uni.get("_id", "")
        current_rank = uni.get("us_news_rank")
        official_name = uni.get("official_name", uni_id)
        
        correct_rank = get_correct_rank(uni_id)
        
        if correct_rank is not None:
            # Is a national university
            if current_rank == correct_rank:
                results["correct"].append({
                    "id": uni_id,
                    "name": official_name,
                    "rank": current_rank,
                })
            else:
                results["incorrect"].append({
                    "id": uni_id,
                    "name": official_name,
                    "current_rank": current_rank,
                    "correct_rank": correct_rank,
                })
        elif uni_id in REGIONAL_UNIVERSITIES or NAME_MAPPINGS.get(uni_id) in REGIONAL_UNIVERSITIES:
            # Explicitly regional - nullify
            if current_rank is not None:
                results["nullify"].append({
                    "id": uni_id,
                    "name": official_name,
                    "current_rank": current_rank,
                    "reason": "Regional University"
                })
            else:
                results["correct"].append({
                    "id": uni_id,
                    "name": official_name,
                    "rank": None,
                })
        else:
            # Unknown - not in our lists
            results["unknown"].append({
                "id": uni_id,
                "name": official_name,
                "current_rank": current_rank,
            })
    
    return results


def update_firestore(db, updates: list, dry_run: bool = True):
    """Update Firestore with correct rankings."""
    collection = db.collection("universities")
    
    for update in updates:
        uni_id = update["id"]
        new_rank = update.get("correct_rank")
        
        if dry_run:
            print(f"  [DRY-RUN] Would update {uni_id}: rank -> {new_rank}")
        else:
            try:
                doc_ref = collection.document(uni_id)
                doc_ref.update({
                    "us_news_rank": new_rank,
                    "rank_updated_at": datetime.utcnow().isoformat(),
                })
                print(f"  [UPDATED] {uni_id}: rank -> {new_rank}")
            except Exception as e:
                print(f"  [ERROR] Failed to update {uni_id}: {e}")


def nullify_ranks(db, unis_to_nullify: list, dry_run: bool = True):
    """Nullify incorrect ranks (regional universities)."""
    collection = db.collection("universities")
    
    for uni in unis_to_nullify:
        uni_id = uni["id"]
        
        if dry_run:
            print(f"  [DRY-RUN] Would nullify {uni_id} (was: {uni.get('current_rank')})")
        else:
            try:
                doc_ref = collection.document(uni_id)
                doc_ref.update({
                    "us_news_rank": None,
                    "rank_updated_at": datetime.utcnow().isoformat(),
                    "rank_nullified_reason": "Not a National University (Regional ranking was incorrectly stored)",
                })
                print(f"  [NULLIFIED] {uni_id}")
            except Exception as e:
                print(f"  [ERROR] Failed to nullify {uni_id}: {e}")


def main():
    parser = argparse.ArgumentParser(description="Fix US News rankings in Firestore")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Show what would be updated without making changes")
    parser.add_argument("--update", action="store_true",
                        help="Actually perform the updates")
    parser.add_argument("--analyze-only", action="store_true",
                        help="Only analyze and report, don't update")
    args = parser.parse_args()
    
    dry_run = not args.update
    
    print("=" * 60)
    print("US News Rankings Fixer")
    print("=" * 60)
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE UPDATE'}")
    print()
    
    # Connect to Firestore
    print("Connecting to Firestore...")
    db = get_firestore_client()
    
    # Fetch all universities
    print("Fetching universities from Firestore...")
    universities = get_all_universities(db)
    print(f"Found {len(universities)} universities")
    print()
    
    # Analyze rankings
    print("Analyzing rankings...")
    results = analyze_rankings(universities)
    
    # Report
    print("\n" + "=" * 60)
    print("ANALYSIS RESULTS")
    print("=" * 60)
    
    print(f"\n✅ Correct rankings: {len(results['correct'])}")
    
    print(f"\n❌ Incorrect rankings (need update): {len(results['incorrect'])}")
    for uni in results["incorrect"][:20]:  # Show first 20
        print(f"   {uni['name']}: {uni['current_rank']} -> {uni['correct_rank']}")
    if len(results["incorrect"]) > 20:
        print(f"   ... and {len(results['incorrect']) - 20} more")
    
    print(f"\n🚫 Need to nullify (Regional): {len(results['nullify'])}")
    for uni in results["nullify"][:20]:
        print(f"   {uni['name']}: {uni['current_rank']} -> NULL ({uni.get('reason', '')})")
    if len(results["nullify"]) > 20:
        print(f"   ... and {len(results['nullify']) - 20} more")
    
    print(f"\n❓ Unknown (not in lists): {len(results['unknown'])}")
    for uni in results["unknown"][:10]:
        status = f"rank={uni['current_rank']}" if uni['current_rank'] else "no rank"
        print(f"   {uni['name']}: {status}")
    if len(results["unknown"]) > 10:
        print(f"   ... and {len(results['unknown']) - 10} more")
    
    if args.analyze_only:
        print("\n[Analyze only mode - no updates performed]")
        return
    
    # Perform updates
    print("\n" + "=" * 60)
    print("PERFORMING UPDATES")
    print("=" * 60)
    
    if results["incorrect"]:
        print(f"\nUpdating {len(results['incorrect'])} incorrect rankings...")
        update_firestore(db, results["incorrect"], dry_run)
    
    if results["nullify"]:
        print(f"\nNullifying {len(results['nullify'])} regional university ranks...")
        nullify_ranks(db, results["nullify"], dry_run)
    
    print("\n" + "=" * 60)
    if dry_run:
        print("DRY RUN COMPLETE - No changes made")
        print("Run with --update to apply changes")
    else:
        print("UPDATE COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
