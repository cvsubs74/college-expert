#!/usr/bin/env python3
"""
Comprehensive fix for all remaining schema issues in research profiles.
Handles all known type mismatches.
"""

import json
from pathlib import Path
from datetime import datetime

RESEARCH_DIR = Path(__file__).parent / "research"

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def ensure_string(val):
    if val is None: return ""
    if isinstance(val, str): return val
    if isinstance(val, dict):
        # Try to extract meaningful text from common keys
        for k in ['text', 'description', 'value', 'strategy', 'details']:
            if k in val: return str(val[k])
        # Otherwise join key-value pairs
        return "; ".join(f"{k}: {v}" for k, v in val.items() if v)
    if isinstance(val, list):
        return "; ".join(str(x) for x in val if x)
    return str(val)

def ensure_bool(val):
    if isinstance(val, bool): return val
    if val is None: return False
    if isinstance(val, str): return val.lower() in ('true', 'yes', '1')
    return bool(val)

def ensure_list(val):
    if val is None: return []
    if isinstance(val, list): return val
    return [val]

def fix_profile(profile):
    fixes = []
    
    # 1. Fix alternate_major_strategy (should be string)
    if 'application_strategy' in profile:
        aps = profile['application_strategy']
        if 'alternate_major_strategy' in aps and not isinstance(aps['alternate_major_strategy'], str):
            aps['alternate_major_strategy'] = ensure_string(aps['alternate_major_strategy'])
            fixes.append("alternate_major_strategy")
    
    # 2. Fix GPA percentile_25 and percentile_75 (should be string)
    try:
        gpa = profile['admissions_data']['admitted_student_profile']['gpa']
        for field in ['percentile_25', 'percentile_75']:
            if field in gpa and gpa[field] is not None:
                if not isinstance(gpa[field], str):
                    gpa[field] = str(gpa[field])
                    fixes.append(f"gpa.{field}")
    except (KeyError, TypeError): pass
    
    # 3. Fix transfer_articulation.restrictions (should be string)
    try:
        ta = profile['credit_policies']['transfer_articulation']
        if 'restrictions' in ta and not isinstance(ta['restrictions'], str):
            ta['restrictions'] = ensure_string(ta['restrictions'])
            fixes.append("transfer_restrictions")
    except (KeyError, TypeError): pass
    
    # 4. Fix colleges - majors, admissions_model, housing_profile, strategic_fit_advice, student_archetype
    try:
        for i, college in enumerate(profile.get('academic_structure', {}).get('colleges', [])):
            # majors should be list
            if 'majors' in college and not isinstance(college['majors'], list):
                if college['majors'] is None:
                    college['majors'] = []
                else:
                    college['majors'] = []
                fixes.append(f"college{i}.majors")
            
            # admissions_model should be string
            if 'admissions_model' in college:
                if not isinstance(college['admissions_model'], str):
                    college['admissions_model'] = ensure_string(college['admissions_model']) or "Direct Admit"
                    fixes.append(f"college{i}.admissions_model")
                elif not college['admissions_model']:
                    college['admissions_model'] = "Direct Admit"
                    fixes.append(f"college{i}.admissions_model")
            
            # housing_profile should be string
            if 'housing_profile' in college and not isinstance(college['housing_profile'], str):
                college['housing_profile'] = ensure_string(college['housing_profile'])
                fixes.append(f"college{i}.housing_profile")
            
            # strategic_fit_advice should be string
            if 'strategic_fit_advice' in college and not isinstance(college['strategic_fit_advice'], str):
                college['strategic_fit_advice'] = ensure_string(college['strategic_fit_advice'])
                fixes.append(f"college{i}.strategic_fit_advice")
            
            # student_archetype should be string
            if 'student_archetype' in college and not isinstance(college['student_archetype'], str):
                college['student_archetype'] = ensure_string(college['student_archetype'])
                fixes.append(f"college{i}.student_archetype")
            
            # Fix majors fields
            for j, major in enumerate(college.get('majors', [])):
                # admissions_pathway should be string
                if 'admissions_pathway' in major and not isinstance(major['admissions_pathway'], str):
                    major['admissions_pathway'] = ensure_string(major['admissions_pathway']) or "Direct Admit"
                    fixes.append(f"major{j}.admissions_pathway")
                
                # is_impacted should be bool
                if 'is_impacted' in major and not isinstance(major['is_impacted'], bool):
                    major['is_impacted'] = ensure_bool(major['is_impacted'])
                    fixes.append(f"major{j}.is_impacted")
                
                # direct_admit_only should be bool
                if 'direct_admit_only' in major and not isinstance(major['direct_admit_only'], bool):
                    major['direct_admit_only'] = ensure_bool(major['direct_admit_only'])
                    fixes.append(f"major{j}.direct_admit_only")
                
                # internal_transfer_allowed should be bool
                if 'internal_transfer_allowed' in major and not isinstance(major['internal_transfer_allowed'], bool):
                    major['internal_transfer_allowed'] = ensure_bool(major['internal_transfer_allowed'])
                    fixes.append(f"major{j}.internal_transfer_allowed")
                
                # prerequisite_courses should be list
                if 'prerequisite_courses' in major and not isinstance(major['prerequisite_courses'], list):
                    major['prerequisite_courses'] = ensure_list(major['prerequisite_courses'])
                    fixes.append(f"major{j}.prerequisite_courses")
                
                # weeder_courses should be list
                if 'weeder_courses' in major and not isinstance(major['weeder_courses'], list):
                    major['weeder_courses'] = ensure_list(major['weeder_courses'])
                    fixes.append(f"major{j}.weeder_courses")
                
                # degree_type should be string
                if 'degree_type' not in major or not major['degree_type']:
                    major['degree_type'] = "B.S."
                    fixes.append(f"major{j}.degree_type")
    except (KeyError, TypeError): pass
    
    # 5. Fix early_admission_stats plan_type
    try:
        stats = profile['admissions_data']['current_status']['early_admission_stats']
        for item in stats:
            if isinstance(item, dict) and ('plan_type' not in item or not item['plan_type']):
                item['plan_type'] = item.get('type', 'Early Decision')
                fixes.append("early_admission_plan_type")
    except (KeyError, TypeError): pass
    
    # 6. Fix racial_breakdown (should be dict)
    try:
        demo = profile['admissions_data']['admitted_student_profile']['demographics']
        if 'racial_breakdown' in demo and not isinstance(demo['racial_breakdown'], dict):
            demo['racial_breakdown'] = {}
            fixes.append("racial_breakdown")
    except (KeyError, TypeError): pass
    
    # 7. Fix submission_rate (should be number)
    try:
        testing = profile['admissions_data']['admitted_student_profile']['testing']
        if 'submission_rate' in testing:
            sr = testing['submission_rate']
            if isinstance(sr, str):
                import re
                match = re.search(r'[\d.]+', sr)
                testing['submission_rate'] = float(match.group()) if match else None
                fixes.append("submission_rate")
    except (KeyError, TypeError, ValueError): pass
    
    # 8. Fix average_weighted GPA (should be number)
    try:
        gpa = profile['admissions_data']['admitted_student_profile']['gpa']
        if 'average_weighted' in gpa:
            aw = gpa['average_weighted']
            if isinstance(aw, str):
                import re
                match = re.search(r'[\d.]+', aw)
                gpa['average_weighted'] = float(match.group()) if match else None
                fixes.append("average_weighted")
    except (KeyError, TypeError, ValueError): pass
    
    # 9. Fix what_it_takes (should be list of strings)
    try:
        wit = profile['student_insights']['what_it_takes']
        if isinstance(wit, list):
            new_wit = []
            for item in wit:
                if isinstance(item, str):
                    new_wit.append(item)
                elif isinstance(item, dict):
                    text = item.get('factor', item.get('text', item.get('details', '')))
                    details = item.get('details', '')
                    new_wit.append(f"{text}: {details}" if details and text != details else text or str(item))
                else:
                    new_wit.append(str(item))
            if new_wit != wit:
                profile['student_insights']['what_it_takes'] = new_wit
                fixes.append("what_it_takes")
    except (KeyError, TypeError): pass
    
    return fixes

def process_file(filepath):
    try:
        content = filepath.read_text(encoding='utf-8')
        profile = json.loads(content)
    except json.JSONDecodeError as e:
        return False, [f"JSON error: {e}"]
    except Exception as e:
        return False, [str(e)]
    
    try:
        fixes = fix_profile(profile)
    except Exception as e:
        return False, [f"Fix error: {e}"]
    
    if fixes:
        filepath.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding='utf-8')
    
    return True, fixes

def main():
    files = sorted(RESEARCH_DIR.glob("*.json"))
    log(f"Processing {len(files)} files")
    
    fixed = 0
    errors = 0
    
    for f in files:
        success, result = process_file(f)
        if not success:
            log(f"❌ {f.name}: {result}")
            errors += 1
        elif result:
            log(f"✅ {f.name}: Fixed {len(result)} issues")
            fixed += 1
    
    log(f"\n📊 Fixed: {fixed}, Errors: {errors}")

if __name__ == "__main__":
    main()
