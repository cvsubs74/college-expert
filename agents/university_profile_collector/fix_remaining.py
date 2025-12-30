#!/usr/bin/env python3
"""
Final targeted fixes for remaining schema issues.
"""

import json
import re
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
        for key in ['text', 'strategy', 'description', 'value', 'advice']:
            if key in value:
                return str(value[key])
        # Convert whole dict to readable string
        return "; ".join(f"{k}: {v}" for k, v in value.items() if v)
    return str(value)

def fix_alternate_major_strategy(profile):
    """Fix alternate_major_strategy to be a string."""
    if 'application_strategy' not in profile:
        return False
    aps = profile['application_strategy']
    if 'alternate_major_strategy' not in aps:
        return False
    
    val = aps['alternate_major_strategy']
    if not isinstance(val, str):
        aps['alternate_major_strategy'] = ensure_string(val)
        return True
    return False

def fix_supplemental_requirements(profile):
    """Fix supplemental_requirements to have required fields."""
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
        if isinstance(req, dict):
            if 'target_program' not in req or not req['target_program']:
                req['target_program'] = "All"
                fixed = True
            if 'requirement_type' not in req or not req['requirement_type']:
                req['requirement_type'] = req.get('type', 'Essays')
                fixed = True
    return fixed

def fix_housing_profile(profile):
    """Fix housing_profile to be a string."""
    if 'academic_structure' not in profile:
        return False
    acs = profile['academic_structure']
    if 'colleges' not in acs:
        return False
    
    fixed = False
    for college in acs.get('colleges', []):
        if 'housing_profile' in college and not isinstance(college['housing_profile'], str):
            college['housing_profile'] = ensure_string(college['housing_profile'])
            fixed = True
    return fixed

def fix_application_deadlines(profile):
    """Fix application_deadlines to have required fields."""
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
            # Parse string like "Early Decision: November 1"
            if ':' in item:
                parts = item.split(':', 1)
                new_deadlines.append({
                    "plan_type": parts[0].strip(),
                    "date": parts[1].strip(),
                    "is_binding": 'decision' in parts[0].lower() and 'early' in parts[0].lower()
                })
            else:
                new_deadlines.append({
                    "plan_type": "Regular Decision",
                    "date": item.strip(),
                    "is_binding": False
                })
            fixed = True
        elif isinstance(item, dict):
            if 'plan_type' not in item or not item['plan_type']:
                item['plan_type'] = item.get('type', item.get('round', 'Regular Decision'))
                fixed = True
            if 'date' not in item:
                item['date'] = item.get('deadline', item.get('deadline_date', ''))
                fixed = True
            if 'is_binding' not in item:
                item['is_binding'] = 'decision' in str(item.get('plan_type', '')).lower()
            new_deadlines.append(item)
        else:
            new_deadlines.append({
                "plan_type": "Regular Decision",
                "date": str(item),
                "is_binding": False
            })
            fixed = True
    
    if fixed:
        ap['application_deadlines'] = new_deadlines
    return fixed

def fix_admissions_model(profile):
    """Fix colleges to have admissions_model field."""
    if 'academic_structure' not in profile:
        return False
    acs = profile['academic_structure']
    if 'colleges' not in acs:
        return False
    
    fixed = False
    for college in acs.get('colleges', []):
        if 'admissions_model' not in college or not college['admissions_model']:
            college['admissions_model'] = "Direct Admit"
            fixed = True
        elif not isinstance(college['admissions_model'], str):
            college['admissions_model'] = ensure_string(college['admissions_model'])
            fixed = True
    return fixed

def fix_longitudinal_notes(profile):
    """Fix longitudinal_trends notes to be string."""
    if 'admissions_data' not in profile:
        return False
    ad = profile['admissions_data']
    if 'longitudinal_trends' not in ad:
        return False
    
    trends = ad['longitudinal_trends']
    if not isinstance(trends, list):
        return False
    
    fixed = False
    for trend in trends:
        if isinstance(trend, dict) and 'notes' in trend:
            if not isinstance(trend['notes'], str):
                trend['notes'] = ensure_string(trend['notes'])
                fixed = True
    return fixed

def fix_transfer_tools(profile):
    """Fix transfer_articulation.tools to be a list."""
    if 'credit_policies' not in profile:
        return False
    cp = profile['credit_policies']
    if 'transfer_articulation' not in cp:
        return False
    ta = cp['transfer_articulation']
    if not isinstance(ta, dict):
        return False
    
    if 'tools' in ta and not isinstance(ta['tools'], list):
        val = ta['tools']
        if val is None:
            ta['tools'] = []
        elif isinstance(val, str):
            ta['tools'] = [val] if val else []
        else:
            ta['tools'] = [str(val)]
        return True
    return False

def fix_admissions_philosophy(profile):
    """Fix strategic_profile.admissions_philosophy to exist."""
    if 'strategic_profile' not in profile:
        return False
    sp = profile['strategic_profile']
    
    if 'admissions_philosophy' not in sp or not sp['admissions_philosophy']:
        # Try to infer from other fields
        sp['admissions_philosophy'] = sp.get('philosophy', sp.get('approach', 'Holistic Review'))
        return True
    if not isinstance(sp['admissions_philosophy'], str):
        sp['admissions_philosophy'] = ensure_string(sp['admissions_philosophy'])
        return True
    return False

def fix_early_admission_plan_type(profile):
    """Fix early_admission_stats to have plan_type."""
    if 'admissions_data' not in profile:
        return False
    ad = profile['admissions_data']
    if 'current_status' not in ad:
        return False
    cs = ad['current_status']
    if 'early_admission_stats' not in cs:
        return False
    
    stats = cs['early_admission_stats']
    if not isinstance(stats, list):
        return False
    
    fixed = False
    for item in stats:
        if isinstance(item, dict) and 'plan_type' not in item:
            item['plan_type'] = item.get('type', item.get('round', 'Early Decision'))
            fixed = True
    return fixed

def process_file(filepath: Path) -> tuple[bool, list]:
    """Process a single file and fix all issues."""
    try:
        content = filepath.read_text(encoding='utf-8')
        profile = json.loads(content)
    except json.JSONDecodeError:
        return False, ["Invalid JSON"]
    except Exception as e:
        return False, [f"Read error: {e}"]
    
    fixes_applied = []
    
    fixes = [
        ("alternate_major_strategy", fix_alternate_major_strategy),
        ("supplemental_requirements", fix_supplemental_requirements),
        ("housing_profile", fix_housing_profile),
        ("application_deadlines", fix_application_deadlines),
        ("admissions_model", fix_admissions_model),
        ("longitudinal_notes", fix_longitudinal_notes),
        ("transfer_tools", fix_transfer_tools),
        ("admissions_philosophy", fix_admissions_philosophy),
        ("early_admission_plan_type", fix_early_admission_plan_type),
    ]
    
    for name, fix_func in fixes:
        try:
            if fix_func(profile):
                fixes_applied.append(name)
        except Exception as e:
            pass
    
    if fixes_applied:
        try:
            filepath.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding='utf-8')
        except Exception as e:
            return False, [f"Write error: {e}"]
    
    return True, fixes_applied

def main():
    files = sorted(RESEARCH_DIR.glob("*.json"))
    log(f"Processing {len(files)} files in {RESEARCH_DIR}")
    
    fixed_count = 0
    error_count = 0
    no_change_count = 0
    
    for f in files:
        success, result = process_file(f)
        if not success:
            log(f"❌ {f.name}: {result}")
            error_count += 1
        elif result:
            log(f"✅ {f.name}: Fixed {', '.join(result)}")
            fixed_count += 1
        else:
            no_change_count += 1
    
    log(f"\n📊 Summary:")
    log(f"   Fixed: {fixed_count}")
    log(f"   No change needed: {no_change_count}")
    log(f"   Errors: {error_count}")

if __name__ == "__main__":
    main()
