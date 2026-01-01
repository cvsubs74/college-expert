#!/usr/bin/env python3
"""
Migration script to extract essay_prompts from supplemental_requirements 
and move them to root level in university JSON files.
"""
import json
import ast
from pathlib import Path
from typing import Dict, List, Any

RESEARCH_DIR = Path("agents/university_profile_collector/research")

def extract_essay_prompts_from_supp_req(data: dict) -> tuple[list, bool]:
    """
    Extract essay_prompts from supplemental_requirements if present.
    
    Returns:
        tuple: (essay_prompts_list, found_flag)
    """
    essay_prompts = []
    found = False
    
    # Navigate to application_process
    if "application_process" not in data:
        return essay_prompts, found
    
    supp_req = data["application_process"].get("supplemental_requirements")
    
    if isinstance(supp_req, list):
        # Check each requirement in the list
        for req in supp_req:
            if isinstance(req, dict) and "requirement" in req:
                req_val = req["requirement"]
                
                # Check if it's a string containing essay_prompts
                if isinstance(req_val, str) and 'essay_prompts' in req_val:
                    try:
                        # Parse the stringified JSON
                        parsed = ast.literal_eval(req_val)
                        if isinstance(parsed, dict) and 'essay_prompts' in parsed:
                            essay_prompts = parsed['essay_prompts']
                            found = True
                            print(f"    → Extracted {len(essay_prompts)} essay prompts from stringified JSON")
                            break
                    except Exception as e:
                        print(f"    ⚠ Failed to parse requirement: {e}")
    
    elif isinstance(supp_req, dict):
        # Check if essay_prompts is directly in the dict
        if 'essay_prompts' in supp_req:
            essay_prompts = supp_req['essay_prompts']
            found = True
            print(f"    → Extracted {len(essay_prompts)} essay prompts from dict")
    
    return essay_prompts, found


def clean_supplemental_requirements(data: dict) -> None:
    """
    Remove essay_prompts from supplemental_requirements structure.
    Convert dict back to list if needed.
    """
    if "application_process" not in data:
        return
    
    supp_req = data["application_process"].get("supplemental_requirements")
    
    if isinstance(supp_req, dict):
        # If it's a dict with requirements_list and essay_prompts
        if 'requirements_list' in supp_req:
            # Replace with just the requirements_list
            data["application_process"]["supplemental_requirements"] = supp_req['requirements_list']
            print("    → Converted supplemental_requirements from dict to list")
        elif 'essay_prompts' in supp_req:
            # Remove essay_prompts key
            del supp_req['essay_prompts']
            print("    → Removed essay_prompts from supplemental_requirements dict")


def migrate_university_essay_prompts(file_path: Path) -> Dict[str, Any]:
    """Migrate essay_prompts to root level for a single university file."""
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Check if essay_prompts already at root level
        if "essay_prompts" in data:
            return {
                "success": True,
                "action": "skipped",
                "message": "Essay prompts already at root level"
            }
        
        # Extract from supplemental_requirements
        essay_prompts, found = extract_essay_prompts_from_supp_req(data)
        
        if not found:
            return {
                "success": True,
                "action": "skipped",
                "message": "No essay prompts found in supplemental_requirements"
            }
        
        # Add to root level
        data["essay_prompts"] = essay_prompts
        
        # Clean up old location
        clean_supplemental_requirements(data)
        
        # Write back
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        return {
            "success": True,
            "action": "migrated",
            "prompts_count": len(essay_prompts),
            "message": f"Migrated {len(essay_prompts)} prompts to root level"
        }
    
    except Exception as e:
        return {
            "success": False,
            "action": "error",
            "message": str(e)
        }


def main():
    print("=" * 70)
    print("Essay Prompts Migration - Move to Root Level")
    print("=" * 70)
    
    # Get all JSON files
    json_files = list(RESEARCH_DIR.glob("*.json"))
    
    migrated = 0
    skipped = 0
    errors = 0
    
    print(f"\nProcessing {len(json_files)} files...\n")
    
    for file_path in sorted(json_files):
        print(f"Processing {file_path.name}...")
        result = migrate_university_essay_prompts(file_path)
        
        if result["success"]:
            if result["action"] == "migrated":
                print(f"  ✓ {result['message']}")
                migrated += 1
            else:
                # print(f"  ○ {result['message']}")
                skipped += 1
        else:
            print(f"  ✗ Error: {result['message']}")
            errors += 1
    
    print("\n" + "=" * 70)
    print("Migration Summary:")
    print(f"  Migrated: {migrated}")
    print(f"  Skipped: {skipped}")
    print(f"  Errors: {errors}")
    print("=" * 70)
    
    if migrated > 0:
        print("\n⚠ Next Steps:")
        print("  1. Review migrated files manually")
        print("  2. Re-ingest affected universities to Elasticsearch")
        print("  3. Update add_essay_prompts.py to add at root level")
        print("  4. Update API code to read from root level")


if __name__ == "__main__":
    main()
