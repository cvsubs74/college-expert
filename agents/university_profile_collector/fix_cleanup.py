#!/usr/bin/env python3
"""Final cleanup for last 8 fixable files."""

import json
from pathlib import Path
from datetime import datetime

RESEARCH_DIR = Path(__file__).parent / "research"

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def ensure_string(val):
    if val is None: return ""
    if isinstance(val, str): return val
    if isinstance(val, dict): return json.dumps(val)
    return str(val)

def ensure_list(val):
    if val is None: return []
    if isinstance(val, list): return val
    return [val]

def ensure_bool(val):
    if isinstance(val, bool): return val
    if val is None: return False
    if isinstance(val, str): return val.lower() in ('true', 'yes', '1')
    return bool(val)

def fix_ap_exceptions(profile):
    """Fix ap_policy.exceptions to be List[str]."""
    try:
        exceptions = profile['credit_policies']['ap_policy']['exceptions']
        if not isinstance(exceptions, list): return False
        new_exc = []
        fixed = False
        for e in exceptions:
            if isinstance(e, str):
                new_exc.append(e)
            else:
                new_exc.append(ensure_string(e))
                fixed = True
        if fixed:
            profile['credit_policies']['ap_policy']['exceptions'] = new_exc
        return fixed
    except: return False

def fix_top_employers(profile):
    """Fix outcomes.top_employers to be list."""
    try:
        emp = profile['outcomes']['top_employers']
        if not isinstance(emp, list):
            profile['outcomes']['top_employers'] = ensure_list(emp)
            return True
        return False
    except: return False

def fix_holistic_factors(profile):
    """Fix holistic_factors to be proper dict."""
    try:
        hf = profile['application_process']['holistic_factors']
        if not isinstance(hf, dict):
            profile['application_process']['holistic_factors'] = {
                "primary_factors": [], "secondary_factors": [], 
                "essay_importance": "High", "demonstrated_interest": "Not Considered",
                "interview_policy": "Not Offered"
            }
            return True
        return False
    except: return False

def fix_credit_philosophy(profile):
    """Fix credit_policies.philosophy to be string."""
    try:
        phil = profile['credit_policies']['philosophy']
        if not isinstance(phil, str):
            profile['credit_policies']['philosophy'] = ensure_string(phil)
            return True
        return False
    except: return False

def fix_internal_transfer_fields(profile):
    """Fix major internal_transfer_allowed and internal_transfer_gpa."""
    try:
        fixed = False
        for college in profile.get('academic_structure', {}).get('colleges', []):
            for major in college.get('majors', []):
                if 'internal_transfer_allowed' in major:
                    if not isinstance(major['internal_transfer_allowed'], bool):
                        major['internal_transfer_allowed'] = ensure_bool(major['internal_transfer_allowed'])
                        fixed = True
                if 'internal_transfer_gpa' in major:
                    val = major['internal_transfer_gpa']
                    if isinstance(val, dict):
                        # Extract float or string
                        major['internal_transfer_gpa'] = val.get('float', val.get('value', ''))
                        fixed = True
        return fixed
    except: return False

def fix_nested_insights(profile):
    """Fix nested StudentInsight format."""
    try:
        insights = profile['student_insights']['insights']
        if not isinstance(insights, list): return False
        new_insights = []
        fixed = False
        for item in insights:
            if isinstance(item, str):
                new_insights.append(item)
            elif isinstance(item, dict):
                # Unwrap nested StudentInsight
                if 'StudentInsight' in item:
                    inner = item['StudentInsight']
                    new_insights.append({
                        "source": inner.get('source', 'student_review'),
                        "category": inner.get('category', 'general'),
                        "insight": inner.get('insight', '')
                    })
                    fixed = True
                else:
                    new_insights.append(item)
            else:
                new_insights.append(str(item))
                fixed = True
        if fixed:
            profile['student_insights']['insights'] = new_insights
        return fixed
    except: return False

def process_file(filepath: Path) -> tuple[bool, list]:
    try:
        profile = json.loads(filepath.read_text(encoding='utf-8'))
    except: return False, ["JSON error"]
    
    fixes = []
    if fix_ap_exceptions(profile): fixes.append("ap_exceptions")
    if fix_top_employers(profile): fixes.append("top_employers")
    if fix_holistic_factors(profile): fixes.append("holistic_factors")
    if fix_credit_philosophy(profile): fixes.append("credit_philosophy")
    if fix_internal_transfer_fields(profile): fixes.append("internal_transfer")
    if fix_nested_insights(profile): fixes.append("nested_insights")
    
    if fixes:
        filepath.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding='utf-8')
    return True, fixes

def main():
    files = sorted(RESEARCH_DIR.glob("*.json"))
    log(f"Processing {len(files)} files")
    fixed = 0
    for f in files:
        success, result = process_file(f)
        if result:
            log(f"✅ {f.name}: {', '.join(result)}")
            fixed += 1
    log(f"\n📊 Fixed: {fixed}")

if __name__ == "__main__":
    main()
