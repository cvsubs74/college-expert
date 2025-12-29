#!/usr/bin/env python3
"""
Fix duplicate strategic_profile entries in university JSON files.

The previous update_rankings.py script incorrectly added a new strategic_profile
at the root level. This script:
1. Finds all JSON files with duplicate strategic_profile
2. Removes the root-level duplicate
3. Ensures the correct nested us_news_rank is preserved
"""

import json
from pathlib import Path

RESEARCH_DIR = Path(__file__).parent.parent / "agents" / "university_profile_collector" / "research"


def fix_json_file(json_path: Path) -> dict:
    """Fix a single JSON file by removing duplicate strategic_profile."""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    fixed = False
    result = {}
    
    # Check if there's a root-level strategic_profile that's a duplicate
    if 'strategic_profile' in data:
        root_strategic = data.get('strategic_profile', {})
        
        # Check if it's just {us_news_rank: X} - a duplicate from our script
        if set(root_strategic.keys()) == {'us_news_rank'}:
            new_rank = root_strategic.get('us_news_rank')
            
            # Update the correct location based on file structure
            # Some files have university_profile wrapper, some don't
            if 'university_profile' in data:
                # Nested structure: university_profile.strategic_profile
                profile = data.get('university_profile', {})
                if 'strategic_profile' in profile:
                    old_rank = profile['strategic_profile'].get('us_news_rank')
                    if new_rank != old_rank:
                        profile['strategic_profile']['us_news_rank'] = new_rank
                        result['old_rank'] = old_rank
                        result['new_rank'] = new_rank
                else:
                    profile['strategic_profile'] = {'us_news_rank': new_rank}
                    result['new_rank'] = new_rank
            elif 'profile' in data:
                # profile wrapper (e.g., some files)
                profile = data.get('profile', {})
                if 'strategic_profile' in profile:
                    old_rank = profile['strategic_profile'].get('us_news_rank')
                    if new_rank != old_rank:
                        profile['strategic_profile']['us_news_rank'] = new_rank
                        result['old_rank'] = old_rank
                        result['new_rank'] = new_rank
            else:
                # Root-level strategic_profile is the main one - keep it as is
                # This means the file structure is correct
                pass
            
            # Remove the duplicate root-level entry (only if we found nested)
            if 'university_profile' in data or 'profile' in data:
                del data['strategic_profile']
                fixed = True
    
    if fixed:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        result['fixed'] = True
    else:
        result['fixed'] = False
    
    return result


def main():
    json_files = list(RESEARCH_DIR.glob("*.json"))
    
    print(f"Scanning {len(json_files)} JSON files for duplicate strategic_profile...")
    print("-" * 60)
    
    fixed_count = 0
    no_issue_count = 0
    
    for json_file in sorted(json_files):
        try:
            result = fix_json_file(json_file)
            
            if result.get('fixed'):
                rank_info = ""
                if 'old_rank' in result:
                    rank_info = f" (rank: {result['old_rank']} → {result['new_rank']})"
                elif 'new_rank' in result:
                    rank_info = f" (rank: {result['new_rank']})"
                print(f"✅ Fixed: {json_file.name}{rank_info}")
                fixed_count += 1
            else:
                no_issue_count += 1
                
        except Exception as e:
            print(f"❌ Error processing {json_file.name}: {e}")
    
    print("-" * 60)
    print(f"\nSummary:")
    print(f"  Fixed: {fixed_count}")
    print(f"  No issues: {no_issue_count}")


if __name__ == "__main__":
    main()
