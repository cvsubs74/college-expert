#!/usr/bin/env python3
"""
Fetch university logos using Google's Favicon API.
Downloads 128x128 PNG logos for all universities in research/ folder.
"""

import os
import json
import requests
import time
from pathlib import Path

# Paths
RESEARCH_DIR = Path(__file__).parent / "research"
IMAGES_DIR = RESEARCH_DIR / "images"

# Ensure images directory exists
IMAGES_DIR.mkdir(exist_ok=True)

# University domain mappings for accurate logo fetching
DOMAIN_MAP = {
    "harvard_university": "harvard.edu",
    "stanford_university": "stanford.edu",
    "massachusetts_institute_of_technology": "mit.edu",
    "california_institute_of_technology": "caltech.edu",
    "yale_university": "yale.edu",
    "princeton_university": "princeton.edu",
    "columbia_university": "columbia.edu",
    "cornell_university": "cornell.edu",
    "brown_university": "brown.edu",
    "dartmouth_college": "dartmouth.edu",
    "university_of_pennsylvania": "upenn.edu",
    "duke_university": "duke.edu",
    "northwestern_university": "northwestern.edu",
    "rice_university": "rice.edu",
    "vanderbilt_university": "vanderbilt.edu",
    "emory_university": "emory.edu",
    "georgetown_university": "georgetown.edu",
    "carnegie_mellon_university": "cmu.edu",
    "johns_hopkins_university": "jhu.edu",
    "new_york_university": "nyu.edu",
    "boston_university": "bu.edu",
    "boston_college": "bc.edu",
    "university_of_notre_dame": "nd.edu",
    "university_of_southern_california": "usc.edu",
    "university_of_california_los_angeles": "ucla.edu",
    "university_of_california_berkeley": "berkeley.edu",
    "university_of_california_davis": "ucdavis.edu",
    "university_of_california_irvine": "uci.edu",
    "university_of_california_merced": "ucmerced.edu",
    "university_of_california_san_diego_0": "ucsd.edu",
    "university_of_california_san_diego_1": "ucsd.edu",
    "university_of_california_santa_barbara": "ucsb.edu",
    "uc_san_diego": "ucsd.edu",
    "university_of_michigan_ann_arbor": "umich.edu",
    "university_of_virginia": "virginia.edu",
    "georgia_institute_of_technology": "gatech.edu",
    "university_of_texas_at_austin": "utexas.edu",
    "university_of_florida": "ufl.edu",
    "university_of_washington": "uw.edu",
    "university_of_wisconsin_madison": "wisc.edu",
    "university_of_north_carolina_at_chapel_hill": "unc.edu",
    "university_of_chicago": "uchicago.edu",
    "ohio_state_university": "osu.edu",
    "pennsylvania_state_university": "psu.edu",
    "purdue_university": "purdue.edu",
    "university_of_illinois_urbana_champaign": "illinois.edu",
    "michigan_state_university": "msu.edu",
    "arizona_state_university": "asu.edu",
    "indiana_university_bloomington": "indiana.edu",
    "university_of_minnesota_twin_cities": "umn.edu",
    "university_of_colorado_boulder": "colorado.edu",
    "university_of_maryland_college_park": "umd.edu",
    "rutgers_university_new_brunswick": "rutgers.edu",
    "texas_a_m_university": "tamu.edu",
    "florida_state_university": "fsu.edu",
    "clemson_university": "clemson.edu",
    "virginia_tech": "vt.edu",
    "north_carolina_state_university": "ncsu.edu",
    "university_of_pittsburgh": "pitt.edu",
    "university_of_connecticut": "uconn.edu",
    "university_of_massachusetts_amherst": "umass.edu",
    "university_of_massachusetts_lowell": "uml.edu",
    "university_of_iowa": "uiowa.edu",
    "university_of_oregon": "uoregon.edu",
    "university_of_georgia": "uga.edu",
    "wake_forest_university": "wfu.edu",
    "tufts_university": "tufts.edu",
    "tulane_university": "tulane.edu",
    "lehigh_university": "lehigh.edu",
    "rensselaer_polytechnic_institute": "rpi.edu",
    "case_western_reserve_university": "case.edu",
    "northeastern_university": "northeastern.edu",
    "brandeis_university": "brandeis.edu",
    "worcester_polytechnic_institute": "wpi.edu",
    "stevens_institute_of_technology": "stevens.edu",
    "drexel_university": "drexel.edu",
    "george_washington_university": "gwu.edu",
    "syracuse_university": "syr.edu",
    "pepperdine_university": "pepperdine.edu",
    "fordham_university": "fordham.edu",
    "loyola_marymount_university": "lmu.edu",
    "loyola_university_chicago": "luc.edu",
    "marquette_university": "marquette.edu",
    "villanova_university": "villanova.edu",
    "santa_clara_university": "scu.edu",
    "gonzaga_university": "gonzaga.edu",
    "creighton_university": "creighton.edu",
    "baylor_university": "baylor.edu",
    "southern_methodist_university": "smu.edu",
    "texas_christian_university": "tcu.edu",
    "university_of_miami": "miami.edu",
    "university_of_denver": "du.edu",
    "university_of_san_diego": "sandiego.edu",
    "university_of_san_francisco": "usfca.edu",
    "howard_university": "howard.edu",
    "american_university": "american.edu",
    "university_of_rochester": "rochester.edu",
    "stony_brook_university": "stonybrook.edu",
    "university_at_buffalo_suny": "buffalo.edu",
    "temple_university": "temple.edu",
    "university_of_cincinnati": "uc.edu",
    "university_of_arizona": "arizona.edu",
    "san_diego_state_university": "sdsu.edu",
    "university_of_south_florida": "usf.edu",
    "university_of_central_florida": "ucf.edu",
    "auburn_university": "auburn.edu",
    "university_of_alabama": "ua.edu",
    "university_of_kentucky": "uky.edu",
    "university_of_tennessee_knoxville": "utk.edu",
    "university_of_south_carolina": "sc.edu",
    "university_of_oklahoma": "ou.edu",
    "oklahoma_state_university": "okstate.edu",
    "university_of_kansas": "ku.edu",
    "kansas_state_university": "ksu.edu",
    "university_of_nebraska_lincoln": "unl.edu",
    "iowa_state_university": "iastate.edu",
    "university_of_arkansas": "uark.edu",
    "university_of_missouri": "missouri.edu",
    "colorado_state_university": "colostate.edu",
    "colorado_school_of_mines": "mines.edu",
    "chapman_university": "chapman.edu",
    "clark_university": "clarku.edu",
    "clarkson_university": "clarkson.edu",
    "college_of_william_and_mary": "wm.edu",
    "the_college_of_william_and_mary": "wm.edu",
    "depaul_university": "depaul.edu",
    "duquesne_university": "duq.edu",
    "elon_university": "elon.edu",
    "hofstra_university": "hofstra.edu",
    "illinois_institute_of_technology": "iit.edu",
    "new_jersey_institute_of_technology": "njit.edu",
    "ohio_university": "ohio.edu",
    "rochester_institute_of_technology": "rit.edu",
    "saint_louis_university": "slu.edu",
    "seattle_university": "seattleu.edu",
    "seton_hall_university": "shu.edu",
    "simmons_university": "simmons.edu",
    "suny_college_of_environmental_science_and_forestry": "esf.edu",
    "the_catholic_university_of_america": "cua.edu",
    "university_of_dayton": "udayton.edu",
    "university_of_delaware": "udel.edu",
    "university_of_hawaii_at_manoa": "hawaii.edu",
    "university_of_la_verne": "laverne.edu",
    "university_of_louisville": "louisville.edu",
    "university_of_new_hampshire": "unh.edu",
    "university_of_the_pacific": "pacific.edu",
    "university_of_rhode_island": "uri.edu",
    "university_of_st_thomas_minnesota": "stthomas.edu",
    "university_of_tulsa": "utulsa.edu",
    "university_of_vermont": "uvm.edu",
    "washington_university_in_st_louis": "wustl.edu",
    "yeshiva_university": "yu.edu",
    "adelphi_university": "adelphi.edu",
    "missouri_university_of_science_and_technology": "mst.edu",
}


def fetch_logo(domain: str, output_path: Path) -> bool:
    """Fetch logo using Google Favicon API."""
    try:
        # Google's Favicon API with 128px size
        url = f"https://www.google.com/s2/favicons?sz=128&domain={domain}"
        response = requests.get(url, timeout=10, allow_redirects=True)
        
        if response.status_code == 200:
            # Check if response is actual image data (not HTML error page)
            content_type = response.headers.get('content-type', '')
            if 'image' in content_type and len(response.content) > 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                
                # Check image size
                import imghdr
                img_type = imghdr.what(output_path)
                if img_type:
                    # Get image dimensions
                    from PIL import Image
                    try:
                        with Image.open(output_path) as img:
                            width, height = img.size
                            if width < 32 or height < 32:
                                print(f"  ⚠️  Small image ({width}x{height})")
                            return True
                    except:
                        return True  # Image exists even if we can't read dimensions
                return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
    return False


def main():
    """Fetch logos for all universities."""
    json_files = list(RESEARCH_DIR.glob("*.json"))
    
    print(f"Found {len(json_files)} university files")
    print(f"Saving logos to: {IMAGES_DIR}")
    print("-" * 60)
    
    success = 0
    skipped = 0
    failed = []
    
    for json_file in sorted(json_files):
        university_id = json_file.stem
        logo_path = IMAGES_DIR / f"{university_id}_logo.png"
        
        # Skip if exists
        if logo_path.exists():
            print(f"✓ {university_id} - already exists")
            skipped += 1
            continue
        
        # Get domain
        domain = DOMAIN_MAP.get(university_id, f"{university_id.replace('_', '')[:20]}.edu")
        print(f"→ {university_id} ({domain})...")
        
        if fetch_logo(domain, logo_path):
            print(f"  ✓ Downloaded")
            success += 1
        else:
            print(f"  ✗ Failed")
            failed.append(university_id)
        
        time.sleep(0.3)  # Rate limiting
    
    print("-" * 60)
    print(f"\nSummary:")
    print(f"  Downloaded: {success}")
    print(f"  Skipped: {skipped}")
    print(f"  Failed: {len(failed)}")
    
    if failed:
        print(f"\nFailed:")
        for uni in failed:
            print(f"  - {uni}")


if __name__ == "__main__":
    main()
