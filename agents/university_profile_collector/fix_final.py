#!/usr/bin/env python3
"""
Quick fix for final remaining minor issues.
"""

import json
from pathlib import Path
from datetime import datetime

RESEARCH_DIR = Path(__file__).parent / "research"

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def ensure_string(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return json.dumps(value)
    return str(value)

def ensure_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [value] if value else []
    return [value]

def fix_common_activities(profile):
    """Fix common_activities to be List[str]."""
    if 'student_insights' not in profile:
        return False
    si = profile['student_insights']
    if 'common_activities' not in si:
        return False
    
    val = si['common_activities']
    if not isinstance(val, list):
        si['common_activities'] = ensure_list(val)
        return True
    return False

def fix_insights_list(profile):
    """Fix insights to be a list."""
    if 'student_insights' not in profile:
        return False
    si = profile['student_insights']
    if 'insights' not in si:
        return False
    
    val = si['insights']
    if not isinstance(val, list):
        si['insights'] = ensure_list(val)
        return True
    return False

def fix_supplemental_deadline(profile):
    """Fix supplemental_requirements deadline to be string."""
    if 'application_process' not in profile:
        return False
    ap = profile['application_process']
    if 'supplemental_requirements' not in ap:
        return False
    
    reqs = ap['supplemental_requirements']
    if not isinstance(reqs, list):
        return False
    
    fixed = False
    for req in reqs:
        if isinstance(req, dict) and 'deadline' in req:
            if not isinstance(req['deadline'], str):
                req['deadline'] = ensure_string(req['deadline'])
                fixed = True
    return fixed

def process_file(filepath: Path) -> tuple[bool, list]:
    try:
        content = filepath.read_text(encoding='utf-8')
        profile = json.loads(content)
    except:
        return False, ["Invalid JSON"]
    
    fixes_applied = []
    
    if fix_common_activities(profile):
        fixes_applied.append("common_activities")
    if fix_insights_list(profile):
        fixes_applied.append("insights_list")
    if fix_supplemental_deadline(profile):
        fixes_applied.append("supplemental_deadline")
    
    if fixes_applied:
        try:
            filepath.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding='utf-8')
        except Exception as e:
            return False, [str(e)]
    
    return True, fixes_applied

def main():
    files = sorted(RESEARCH_DIR.glob("*.json"))
    log(f"Processing {len(files)} files")
    
    fixed = 0
    for f in files:
        success, result = process_file(f)
        if result:
            log(f"✅ {f.name}: Fixed {', '.join(result)}")
            fixed += 1
    
    log(f"\n📊 Fixed: {fixed}")

if __name__ == "__main__":
    main()
