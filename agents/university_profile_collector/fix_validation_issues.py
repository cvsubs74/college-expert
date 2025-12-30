#!/usr/bin/env python3
"""
Fix common validation issues in research profile JSON files.
Handles:
1. String analyst_takeaways -> proper object format
2. String location -> Location object format
3. Object early_admission_stats -> list format
4. String application_deadlines -> proper object format
5. Invalid JSON (attempts repair)
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime

RESEARCH_DIR = Path(__file__).parent / "research"
BACKUP_DIR = RESEARCH_DIR / "backups"

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def fix_analyst_takeaways(profile):
    """Convert string analyst_takeaways to proper objects."""
    if 'strategic_profile' not in profile:
        return False
    sp = profile['strategic_profile']
    if 'analyst_takeaways' not in sp:
        return False
    
    takeaways = sp['analyst_takeaways']
    if not isinstance(takeaways, list):
        return False
    
    fixed = False
    new_takeaways = []
    for item in takeaways:
        if isinstance(item, str):
            # Convert string to object with 'takeaway' field
            new_takeaways.append({"takeaway": item, "category": "general"})
            fixed = True
        elif isinstance(item, dict):
            new_takeaways.append(item)
        else:
            new_takeaways.append({"takeaway": str(item), "category": "general"})
            fixed = True
    
    if fixed:
        sp['analyst_takeaways'] = new_takeaways
    return fixed

def fix_location(profile):
    """Convert string location to Location object."""
    if 'metadata' not in profile:
        return False
    metadata = profile['metadata']
    if 'location' not in metadata:
        return False
    
    location = metadata['location']
    if isinstance(location, str):
        # Parse "City, State" format
        parts = location.split(',')
        if len(parts) >= 2:
            metadata['location'] = {
                "city": parts[0].strip(),
                "state": parts[1].strip(),
                "region": ""
            }
        else:
            metadata['location'] = {
                "city": location.strip(),
                "state": "",
                "region": ""
            }
        return True
    return False

def fix_early_admission_stats(profile):
    """Convert object early_admission_stats to list."""
    if 'admissions_data' not in profile:
        return False
    ad = profile['admissions_data']
    if 'current_status' not in ad:
        return False
    cs = ad['current_status']
    if 'early_admission_stats' not in cs:
        return False
    
    stats = cs['early_admission_stats']
    if isinstance(stats, dict):
        # Convert dict to list of one item
        cs['early_admission_stats'] = [stats]
        return True
    return False

def fix_application_deadlines(profile):
    """Convert string application_deadlines to proper objects."""
    if 'application_process' not in profile:
        return False
    ap = profile['application_process']
    if 'application_deadlines' not in ap:
        return False
    
    deadlines = ap['application_deadlines']
    if not isinstance(deadlines, list):
        return False
    
    fixed = False
    new_deadlines = []
    for item in deadlines:
        if isinstance(item, str):
            # Try to parse "Type: Date" format
            if ':' in item:
                parts = item.split(':', 1)
                new_deadlines.append({
                    "round_type": parts[0].strip(),
                    "deadline_date": parts[1].strip()
                })
            else:
                new_deadlines.append({
                    "round_type": "Regular Decision",
                    "deadline_date": item.strip()
                })
            fixed = True
        elif isinstance(item, dict):
            new_deadlines.append(item)
        else:
            fixed = True
    
    if fixed:
        ap['application_deadlines'] = new_deadlines
    return fixed

def fix_colleges_admissions_model(profile):
    """Fix colleges with non-string admissions_model or non-boolean is_restricted."""
    if 'academic_structure' not in profile:
        return False
    acs = profile['academic_structure']
    if 'colleges' not in acs:
        return False
    
    fixed = False
    for college in acs['colleges']:
        if 'admissions_model' in college and not isinstance(college['admissions_model'], str):
            college['admissions_model'] = str(college['admissions_model']) if college['admissions_model'] else "Direct Admit"
            fixed = True
        if 'is_restricted_or_capped' in college and not isinstance(college['is_restricted_or_capped'], bool):
            val = college['is_restricted_or_capped']
            college['is_restricted_or_capped'] = bool(val) if val is not None else False
            fixed = True
    return fixed

def process_file(filepath: Path) -> tuple[bool, str]:
    """Process a single file and fix issues. Returns (success, message)."""
    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception as e:
        return False, f"Read error: {e}"
    
    # Try to parse JSON
    try:
        profile = json.loads(content)
    except json.JSONDecodeError as e:
        # Try basic repairs
        try:
            # Remove trailing commas
            fixed_content = re.sub(r',\s*}', '}', content)
            fixed_content = re.sub(r',\s*]', ']', fixed_content)
            profile = json.loads(fixed_content)
            log(f"  Fixed JSON syntax in {filepath.name}")
        except:
            return False, f"Invalid JSON: {e}"
    
    # Apply fixes
    fixes_applied = []
    
    if fix_analyst_takeaways(profile):
        fixes_applied.append("analyst_takeaways")
    
    if fix_location(profile):
        fixes_applied.append("location")
    
    if fix_early_admission_stats(profile):
        fixes_applied.append("early_admission_stats")
    
    if fix_application_deadlines(profile):
        fixes_applied.append("application_deadlines")
    
    if fix_colleges_admissions_model(profile):
        fixes_applied.append("colleges_fields")
    
    if fixes_applied:
        # Write back
        try:
            filepath.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding='utf-8')
            return True, f"Fixed: {', '.join(fixes_applied)}"
        except Exception as e:
            return False, f"Write error: {e}"
    
    return True, "No fixes needed"

def main():
    files = sorted(RESEARCH_DIR.glob("*.json"))
    log(f"Processing {len(files)} files in {RESEARCH_DIR}")
    
    fixed_count = 0
    error_count = 0
    no_change_count = 0
    
    for f in files:
        success, msg = process_file(f)
        if "Fixed:" in msg:
            log(f"✅ {f.name}: {msg}")
            fixed_count += 1
        elif success:
            no_change_count += 1
        else:
            log(f"❌ {f.name}: {msg}")
            error_count += 1
    
    log(f"\n📊 Summary:")
    log(f"   Fixed: {fixed_count}")
    log(f"   No change needed: {no_change_count}")
    log(f"   Errors: {error_count}")

if __name__ == "__main__":
    main()
