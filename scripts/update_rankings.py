#!/usr/bin/env python3
"""
Update all university JSON files with correct US News 2026 rankings.
- Set us_news_rank field directly in strategic_profile
- Remove the rankings array
"""
import json
import glob
import os

# US News 2026 National Universities Rankings (verified from web sources)
US_NEWS_2026_RANKINGS = {
    # Top 10
    "princeton_university": 1,
    "massachusetts_institute_of_technology": 2,
    "harvard_university": 3,
    "stanford_university": 4,
    "yale_university": 4,
    "university_of_chicago": 6,
    "duke_university": 7,
    "northwestern_university": 7,
    "university_of_pennsylvania": 7,
    "johns_hopkins_university": 7,
    
    # 11-20
    "california_institute_of_technology": 11,
    "cornell_university": 12,
    "brown_university": 13,
    "columbia_university": 13,
    "dartmouth_college": 13,
    "university_of_california_berkeley": 15,
    "rice_university": 17,
    "university_of_california_los_angeles": 17,
    "vanderbilt_university": 17,
    "carnegie_mellon_university": 20,
    "university_of_michigan_ann_arbor": 20,
    "university_of_notre_dame": 20,
    "washington_university_in_st_louis": 20,
    
    # 21-30
    "emory_university": 24,
    "georgetown_university": 24,
    "university_of_north_carolina_at_chapel_hill": 26,
    "university_of_virginia": 26,
    "university_of_southern_california": 28,
    "university_of_california_san_diego": 29,
    "new_york_university": 30,
    "university_of_florida": 30,
    "university_of_texas_at_austin": 30,
    
    # 31-40
    "georgia_institute_of_technology": 33,
    "university_of_california_davis": 33,
    "university_of_california_irvine": 33,
    "boston_college": 36,
    "tufts_university": 36,
    "university_of_wisconsin_madison": 36,
    "university_of_rochester": 40,
    "university_of_washington": 40,
    
    # 41-50
    "boston_university": 41,
    "ohio_state_university": 41,
    "purdue_university": 41,
    "rutgers_university_new_brunswick": 41,
    "university_of_california_santa_barbara": 41,
    "university_of_illinois_urbana_champaign": 41,
    "university_of_maryland_college_park": 47,
    "case_western_reserve_university": 48,
    "lehigh_university": 48,
    "university_of_georgia": 48,
    
    # 51-60
    "college_of_william_and_mary": 51,
    "the_college_of_william_and_mary": 51,
    "northeastern_university": 51,
    "university_of_minnesota_twin_cities": 51,
    "virginia_tech": 51,
    "florida_state_university": 56,
    "pennsylvania_state_university": 56,
    "stony_brook_university": 56,
    "villanova_university": 56,
    "north_carolina_state_university": 60,
    "santa_clara_university": 60,
    "george_washington_university": 60,
    
    # 61-80
    "brandeis_university": 63,
    "tulane_university": 63,
    "university_of_miami": 63,
    "michigan_state_university": 66,
    "university_of_massachusetts_amherst": 66,
    "texas_a_m_university": 68,
    "university_of_pittsburgh": 69,
    "rensselaer_polytechnic_institute": 70,
    "university_of_connecticut": 70,
    "indiana_university_bloomington": 73,
    "syracuse_university": 75,
    "university_at_buffalo_suny": 75,
    "stevens_institute_of_technology": 78,
    "clemson_university": 80,
    "drexel_university": 80,
    
    # 81-100
    "pepperdine_university": 84,
    "howard_university": 86,
    "baylor_university": 88,
    "marquette_university": 88,
    "university_of_delaware": 88,
    "university_of_south_florida": 88,
    "american_university": 91,
    "fordham_university": 91,
    "southern_methodist_university": 91,
    "university_of_colorado_boulder": 95,
    "gonzaga_university": 98,
    "the_university_of_iowa": 98,
    "university_of_oregon": 98,
    "auburn_university": 102,
    "chapman_university": 102,
    "loyola_marymount_university": 102,
    "temple_university": 102,
    "illinois_institute_of_technology": 105,
    "university_of_san_diego": 106,
    "creighton_university": 114,
    "university_of_denver": 114,
    "wake_forest_university": 47,
    "university_of_arizona": 115,
}

research_dir = "agents/university_profile_collector/research"
updated = 0
missing = []

for filepath in sorted(glob.glob(f"{research_dir}/*.json")):
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Use filename as the key (this is more reliable than _id)
        university_id = os.path.basename(filepath).replace('.json', '')
        official_name = data.get('metadata', {}).get('official_name', university_id)
        
        # Get the correct US News 2026 rank
        us_news_rank = US_NEWS_2026_RANKINGS.get(university_id)
        
        if us_news_rank is None:
            missing.append((university_id, official_name))
        
        # Update strategic_profile
        if 'strategic_profile' in data:
            data['strategic_profile']['us_news_rank'] = us_news_rank
            # Remove the rankings array
            if 'rankings' in data['strategic_profile']:
                del data['strategic_profile']['rankings']
        
        # Write back
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Updated: {official_name} -> #{us_news_rank if us_news_rank else 'N/A'}")
        updated += 1
        
    except Exception as e:
        print(f"Error processing {filepath}: {e}")

print(f"\n✓ Updated {updated} files")
if missing:
    print(f"\n⚠ Missing rankings for {len(missing)} universities:")
    for uid, name in missing:
        print(f"  - {name} ({uid})")
