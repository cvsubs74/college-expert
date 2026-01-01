#!/usr/bin/env python3
"""
Fix essay_prompts location - move from root level to application_process.essay_prompts
and clean up any in supplemental_requirements.
"""
import json
import ast
from pathlib import Path

RESEARCH_DIR = Path("agents/university_profile_collector/research")

def fix_essay_prompts_location(file_path: Path) -> dict:
    """Fix essay_prompts location for a single file."""
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        modified = False
        
        # Step 1: Check if there are essay_prompts at root level
        root_prompts = data.get('essay_prompts', [])
        
        # Step 2: Check if application_process exists
        if "application_process" not in data:
            data["application_process"] = {}
        
        app_process = data["application_process"]
        
        # Step 3: Get existing essay_prompts in application_process
        existing_app_prompts = app_process.get('essay_prompts', [])
        
        # Step 4: Extract essay_prompts from supplemental_requirements if any
        supp_req_prompts = []
        supp_req = app_process.get("supplemental_requirements")
        if isinstance(supp_req, list):
            for req in supp_req:
                if isinstance(req, dict) and "requirement" in req:
                    req_val = req["requirement"]
                    if isinstance(req_val, str) and 'essay_prompts' in req_val:
                        try:
                            parsed = ast.literal_eval(req_val)
                            if isinstance(parsed, dict) and 'essay_prompts' in parsed:
                                supp_req_prompts = parsed['essay_prompts']
                                break
                        except Exception:
                            pass
        
        # Step 5: Decide which prompts to keep
        # Priority: existing application_process > root > supplemental_requirements
        final_prompts = existing_app_prompts or root_prompts or supp_req_prompts
        
        # Step 6: Set essay_prompts in application_process
        if final_prompts:
            app_process['essay_prompts'] = final_prompts
            modified = True
        
        # Step 7: Remove essay_prompts from root level if present
        if 'essay_prompts' in data:
            del data['essay_prompts']
            modified = True
        
        # Step 8: Write back if modified
        if modified:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            return {
                "success": True,
                "action": "fixed",
                "prompts_count": len(final_prompts),
                "message": f"Moved to application_process.essay_prompts ({len(final_prompts)} prompts)"
            }
        else:
            return {
                "success": True,
                "action": "skipped",
                "message": "No changes needed"
            }
    
    except Exception as e:
        return {
            "success": False,
            "action": "error",
            "message": str(e)
        }


def main():
    print("=" * 70)
    print("Essay Prompts Location Fix - Move to application_process")
    print("=" * 70)
    
    json_files = list(RESEARCH_DIR.glob("*.json"))
    
    fixed = 0
    skipped = 0
    errors = 0
    
    print(f"\nProcessing {len(json_files)} files...\n")
    
    for file_path in sorted(json_files):
        result = fix_essay_prompts_location(file_path)
        
        if result["success"]:
            if result["action"] == "fixed":
                print(f"✓ {file_path.name}: {result['message']}")
                fixed += 1
            else:
                skipped += 1
        else:
            print(f"✗ {file_path.name}: {result['message']}")
            errors += 1
    
    print("\n" + "=" * 70)
    print("Summary:")
    print(f"  Fixed: {fixed}")
    print(f"  Skipped: {skipped}")
    print(f"  Errors: {errors}")
    print("=" * 70)


if __name__ == "__main__":
    main()
