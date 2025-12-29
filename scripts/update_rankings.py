#!/usr/bin/env python3
"""
Update US News 2026 rankings in university research JSON files.
"""

import json
import os
from pathlib import Path

# 2026 US News Rankings scraped from the website
US_NEWS_2026_RANKINGS = [
    {"name": "Princeton University", "rank": 1},
    {"name": "Massachusetts Institute of Technology", "rank": 2},
    {"name": "Harvard University", "rank": 3},
    {"name": "Stanford University", "rank": 4},
    {"name": "Yale University", "rank": 4},
    {"name": "University of Chicago", "rank": 6},
    {"name": "Duke University", "rank": 7},
    {"name": "Johns Hopkins University", "rank": 7},
    {"name": "Northwestern University", "rank": 7},
    {"name": "University of Pennsylvania", "rank": 7},
    {"name": "California Institute of Technology", "rank": 11},
    {"name": "Cornell University", "rank": 12},
    {"name": "Brown University", "rank": 13},
    {"name": "Dartmouth College", "rank": 13},
    {"name": "Columbia University", "rank": 15},
    {"name": "University of California, Berkeley", "rank": 15},
    {"name": "Rice University", "rank": 17},
    {"name": "University of California, Los Angeles", "rank": 17},
    {"name": "Vanderbilt University", "rank": 17},
    {"name": "Carnegie Mellon University", "rank": 20},
    {"name": "University of Michigan--Ann Arbor", "rank": 20},
    {"name": "University of Notre Dame", "rank": 20},
    {"name": "Washington University in St. Louis", "rank": 20},
    {"name": "Emory University", "rank": 24},
    {"name": "University of Southern California", "rank": 28},
    {"name": "University of California San Diego", "rank": 29},
    {"name": "University of Florida", "rank": 30},
    {"name": "The University of Texas--Austin", "rank": 30},
    {"name": "Georgia Institute of Technology", "rank": 32},
    {"name": "New York University", "rank": 32},
    {"name": "The Ohio State University", "rank": 41},
    {"name": "Boston University", "rank": 42},
    {"name": "Rutgers University--New Brunswick", "rank": 42},
    {"name": "University of Maryland, College Park", "rank": 42},
    {"name": "University of Washington", "rank": 42},
    {"name": "Lehigh University", "rank": 46},
    {"name": "Northeastern University", "rank": 46},
    {"name": "Purdue University--Main Campus", "rank": 46},
    {"name": "The Pennsylvania State University--University Park", "rank": 59},
    {"name": "Santa Clara University", "rank": 59},
    {"name": "Stony Brook University--SUNY", "rank": 59},
    {"name": "University of Minnesota--Twin Cities", "rank": 59},
    {"name": "Drexel University", "rank": 80},
    {"name": "New Jersey Institute of Technology", "rank": 80},
    {"name": "Stevens Institute of Technology", "rank": 80},
    {"name": "Pepperdine University", "rank": 84},
    {"name": "University of Illinois Chicago", "rank": 84},
    {"name": "Worcester Polytechnic Institute", "rank": 84},
    {"name": "Yeshiva University", "rank": 84},
    {"name": "Texas Christian University", "rank": 97},
    {"name": "University of Colorado Boulder", "rank": 97},
    {"name": "Auburn University", "rank": 102},
    {"name": "Gonzaga University", "rank": 102},
    {"name": "Loyola Marymount University", "rank": 102},
    {"name": "Brigham Young University", "rank": 110},
    {"name": "Chapman University", "rank": 110},
    {"name": "The University of Oklahoma", "rank": 110},
    {"name": "Creighton University", "rank": 117},
    {"name": "Elon University", "rank": 117},
    {"name": "George Mason University", "rank": 117},
    {"name": "University of Maryland Baltimore County", "rank": 127},
    {"name": "University of South Carolina", "rank": 127},
    {"name": "Clark University", "rank": 132},
    {"name": "CUNY--City College", "rank": 132},
    {"name": "Loyola University Chicago", "rank": 132},
    {"name": "Thomas Jefferson University", "rank": 132},
]

# Mapping from various name forms to JSON file names (snake_case)
# This helps match scraped names to file names
NAME_TO_FILE_MAPPING = {
    "princeton university": "princeton_university",
    "massachusetts institute of technology": "massachusetts_institute_of_technology",
    "harvard university": "harvard_university",
    "stanford university": "stanford_university",
    "yale university": "yale_university",
    "university of chicago": "university_of_chicago",
    "duke university": "duke_university",
    "johns hopkins university": "johns_hopkins_university",
    "northwestern university": "northwestern_university",
    "university of pennsylvania": "university_of_pennsylvania",
    "california institute of technology": "california_institute_of_technology",
    "cornell university": "cornell_university",
    "brown university": "brown_university",
    "dartmouth college": "dartmouth_college",
    "columbia university": "columbia_university",
    "university of california, berkeley": "university_of_california_berkeley",
    "rice university": "rice_university",
    "university of california, los angeles": "university_of_california_los_angeles",
    "vanderbilt university": "vanderbilt_university",
    "carnegie mellon university": "carnegie_mellon_university",
    "university of michigan--ann arbor": "university_of_michigan_ann_arbor",
    "university of notre dame": "university_of_notre_dame",
    "washington university in st. louis": "washington_university_in_st_louis",
    "emory university": "emory_university",
    "university of southern california": "university_of_southern_california",
    "university of california san diego": "university_of_california_san_diego",
    "university of florida": "university_of_florida",
    "the university of texas--austin": "university_of_texas_austin",
    "georgia institute of technology": "georgia_institute_of_technology",
    "new york university": "new_york_university",
    "the ohio state university": "ohio_state_university",
    "boston university": "boston_university",
    "rutgers university--new brunswick": "rutgers_university_new_brunswick",
    "university of maryland, college park": "university_of_maryland_college_park",
    "university of washington": "university_of_washington",
    "lehigh university": "lehigh_university",
    "northeastern university": "northeastern_university",
    "purdue university--main campus": "purdue_university",
    "the pennsylvania state university--university park": "pennsylvania_state_university",
    "santa clara university": "santa_clara_university",
    "stony brook university--suny": "stony_brook_university",
    "university of minnesota--twin cities": "university_of_minnesota_twin_cities",
    "drexel university": "drexel_university",
    "new jersey institute of technology": "new_jersey_institute_of_technology",
    "stevens institute of technology": "stevens_institute_of_technology",
    "pepperdine university": "pepperdine_university",
    "university of illinois chicago": "university_of_illinois_chicago",
    "worcester polytechnic institute": "worcester_polytechnic_institute",
    "yeshiva university": "yeshiva_university",
    "texas christian university": "texas_christian_university",
    "university of colorado boulder": "university_of_colorado_boulder",
    "auburn university": "auburn_university",
    "gonzaga university": "gonzaga_university",
    "loyola marymount university": "loyola_marymount_university",
    "brigham young university": "brigham_young_university",
    "chapman university": "chapman_university",
    "the university of oklahoma": "university_of_oklahoma",
    "creighton university": "creighton_university",
    "elon university": "elon_university",
    "george mason university": "george_mason_university",
    "university of maryland baltimore county": "university_of_maryland_baltimore_county",
    "university of south carolina": "university_of_south_carolina",
    "clark university": "clark_university",
    "cuny--city college": "cuny_city_college",
    "loyola university chicago": "loyola_university_chicago",
    "thomas jefferson university": "thomas_jefferson_university",
}


def normalize_name(name: str) -> str:
    """Normalize a university name for matching."""
    return name.lower().strip()


def find_json_file(research_dir: Path, file_base: str) -> Path | None:
    """Find the JSON file for a university."""
    json_path = research_dir / f"{file_base}.json"
    if json_path.exists():
        return json_path
    return None


def update_ranking(json_path: Path, new_rank: int) -> dict:
    """
    Update the us_news_rank in a JSON file.
    
    Handles different JSON structures:
    - Root-level: strategic_profile.us_news_rank
    - Nested: university_profile.strategic_profile.us_news_rank
    - Nested: profile.strategic_profile.us_news_rank (legacy)
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    old_rank = None
    
    # Determine the correct location for strategic_profile
    if 'university_profile' in data:
        # Nested structure: university_profile.strategic_profile
        profile = data['university_profile']
        if 'strategic_profile' not in profile:
            profile['strategic_profile'] = {}
        old_rank = profile['strategic_profile'].get('us_news_rank')
        profile['strategic_profile']['us_news_rank'] = new_rank
    elif 'profile' in data:
        # Legacy structure: profile.strategic_profile
        profile = data['profile']
        if 'strategic_profile' not in profile:
            profile['strategic_profile'] = {}
        old_rank = profile['strategic_profile'].get('us_news_rank')
        profile['strategic_profile']['us_news_rank'] = new_rank
    else:
        # Root-level structure (most common)
        if 'strategic_profile' not in data:
            data['strategic_profile'] = {}
        old_rank = data['strategic_profile'].get('us_news_rank')
        data['strategic_profile']['us_news_rank'] = new_rank
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    return {
        'file': json_path.name,
        'old_rank': old_rank,
        'new_rank': new_rank,
        'changed': old_rank != new_rank
    }


def main():
    # Path to research directory
    research_dir = Path(__file__).parent.parent / "agents" / "university_profile_collector" / "research"
    
    if not research_dir.exists():
        print(f"Error: Research directory not found: {research_dir}")
        return
    
    print(f"Research directory: {research_dir}")
    print(f"Processing {len(US_NEWS_2026_RANKINGS)} universities with 2026 rankings...")
    print("-" * 60)
    
    updated = []
    not_found = []
    unchanged = []
    
    for entry in US_NEWS_2026_RANKINGS:
        name = entry['name']
        rank = entry['rank']
        normalized = normalize_name(name)
        
        # Look up the file name
        file_base = NAME_TO_FILE_MAPPING.get(normalized)
        
        if not file_base:
            # Try to guess the file name
            file_base = normalized.replace(' ', '_').replace(',', '').replace('--', '_').replace('-', '_').replace('.', '')
            file_base = file_base.replace('the_', '').replace('__', '_')
        
        json_path = find_json_file(research_dir, file_base)
        
        if json_path:
            result = update_ranking(json_path, rank)
            if result['changed']:
                updated.append(result)
                print(f"✓ Updated {result['file']}: {result['old_rank']} → {result['new_rank']}")
            else:
                unchanged.append(result)
                print(f"= Unchanged {result['file']}: rank {result['new_rank']}")
        else:
            not_found.append({'name': name, 'rank': rank, 'tried': file_base})
            print(f"✗ Not found: {name} (tried {file_base}.json)")
    
    print("-" * 60)
    print(f"\nSummary:")
    print(f"  Updated: {len(updated)}")
    print(f"  Unchanged: {len(unchanged)}")
    print(f"  Not found: {len(not_found)}")
    
    if not_found:
        print(f"\nUniversities not found ({len(not_found)}):")
        for nf in not_found:
            print(f"  - {nf['name']} (rank {nf['rank']})")


if __name__ == "__main__":
    main()
