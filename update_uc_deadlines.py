#!/usr/bin/env python3
"""
Update UC (University of California) application deadlines with official 2025-2026 dates.

According to official UC Admissions website:
- Fall 2026 admission application filing period: October 1 - December 1, 2025
- UC schools do not have Early Decision or Early Action
- All UC campuses share the same deadline (except Merced has Spring options)
"""

import json
import os
import glob

RESEARCH_DIR = "agents/university_profile_collector/research"

# UC schools to update
UC_FILES = [
    "uc_san_diego.json",
    "university_of_california_berkeley.json",
    "university_of_california_davis.json",
    "university_of_california_irvine.json",
    "university_of_california_los_angeles.json",
    "university_of_california_merced.json",
    "university_of_california_san_diego_0.json",
    "university_of_california_san_diego_1.json",
    "university_of_california_santa_barbara.json",
]

# Official UC deadline for Fall 2026
UC_DEADLINES = [
    {
        "plan_type": "Regular Decision",
        "date": "2025-12-01",
        "is_binding": False,
        "notes": "UC application filing period: October 1 - December 1, 2025 (11:59 PM PST). All UC campuses share this single deadline. No Early Decision or Early Action available."
    }
]

def update_uc_file(filepath: str) -> bool:
    """Update application deadlines in a UC JSON file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Ensure application_process exists
        if 'application_process' not in data:
            data['application_process'] = {}
        
        # Update application_deadlines
        data['application_process']['application_deadlines'] = UC_DEADLINES.copy()
        
        # Write back to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return True
        
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False

def main():
    """Update all UC university JSON files."""
    updated_count = 0
    error_count = 0
    
    print("Updating UC application deadlines with official 2025-2026 dates...")
    print(f"Deadline: November 30, 2025 (filing period Oct 1 - Nov 30)")
    print()
    
    for filename in UC_FILES:
        filepath = os.path.join(RESEARCH_DIR, filename)
        
        if not os.path.exists(filepath):
            print(f"⚠️  File not found: {filename}")
            continue
        
        if update_uc_file(filepath):
            print(f"✓ Updated: {filename}")
            updated_count += 1
        else:
            print(f"✗ Error: {filename}")
            error_count += 1
    
    print(f"\n=== Summary ===")
    print(f"Updated: {updated_count}")
    print(f"Errors: {error_count}")
    
    # Return list of updated files for ingestion
    return [os.path.join(RESEARCH_DIR, f) for f in UC_FILES if os.path.exists(os.path.join(RESEARCH_DIR, f))]

if __name__ == "__main__":
    updated_files = main()
    print(f"\nUpdated files: {updated_files}")
