#!/usr/bin/env python3
"""
Comprehensive schema fix for research profiles.
Fixes all remaining schema issues without losing data.
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime

RESEARCH_DIR = Path(__file__).parent / "research"

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def ensure_list(value):
    """Ensure value is a list."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]

def ensure_string(value):
    """Ensure value is a string."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        # Try to extract meaningful text
        for key in ['name', 'title', 'text', 'value', 'description']:
            if key in value:
                return str(value[key])
        return json.dumps(value)
    return str(value)

def ensure_bool(value):
    """Ensure value is a boolean."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, str):
        return value.lower() in ('true', 'yes', '1')
    return bool(value)

def ensure_number(value):
    """Ensure value is a number."""
    if isinstance(value, (int, float)):
        return value
    if value is None:
        return None
    if isinstance(value, str):
        # Try to extract number from string like "50%" or "50"
        match = re.search(r'[\d.]+', value)
        if match:
            try:
                return float(match.group())
            except:
                pass
    return None

def fix_minors_certificates(profile):
    """Fix minors_certificates to be list of strings."""
    if 'academic_structure' not in profile:
        return False
    acs = profile['academic_structure']
    if 'minors_certificates' not in acs:
        return False
    
    items = acs['minors_certificates']
    if not isinstance(items, list):
        return False
    
    fixed = False
    new_items = []
    for item in items:
        if isinstance(item, str):
            new_items.append(item)
        elif isinstance(item, dict):
            # Extract name or title
            name = item.get('name') or item.get('title') or item.get('minor_name') or str(item)
            new_items.append(name)
            fixed = True
        else:
            new_items.append(str(item))
            fixed = True
    
    if fixed:
        acs['minors_certificates'] = new_items
    return fixed

def fix_weeder_courses(profile):
    """Fix weeder_courses to be list of strings."""
    if 'academic_structure' not in profile:
        return False
    acs = profile['academic_structure']
    if 'colleges' not in acs:
        return False
    
    fixed = False
    for college in acs.get('colleges', []):
        for major in college.get('majors', []):
            if 'weeder_courses' in major:
                courses = major['weeder_courses']
                if not isinstance(courses, list):
                    if courses is None:
                        major['weeder_courses'] = []
                    elif isinstance(courses, str):
                        major['weeder_courses'] = [courses] if courses else []
                    else:
                        major['weeder_courses'] = [str(courses)]
                    fixed = True
    return fixed

def fix_policy_object(policy_dict, required_fields):
    """Ensure policy dict has required fields."""
    if policy_dict is None:
        return {}
    if not isinstance(policy_dict, dict):
        return {"description": str(policy_dict)}
    
    for field, default in required_fields.items():
        if field not in policy_dict:
            policy_dict[field] = default
    return policy_dict

def fix_credit_policies(profile):
    """Fix ap_policy, ib_policy, transfer_articulation to be proper objects."""
    if 'credit_policies' not in profile:
        return False
    cp = profile['credit_policies']
    
    fixed = False
    
    # Fix ap_policy
    if 'ap_policy' in cp:
        ap = cp['ap_policy']
        if not isinstance(ap, dict):
            cp['ap_policy'] = {"description": str(ap) if ap else "", "minimum_score": 3, "exceptions": []}
            fixed = True
        else:
            if 'exceptions' in ap and not isinstance(ap['exceptions'], list):
                ap['exceptions'] = [ap['exceptions']] if ap['exceptions'] else []
                fixed = True
    
    # Fix ib_policy
    if 'ib_policy' in cp:
        ib = cp['ib_policy']
        if not isinstance(ib, dict):
            cp['ib_policy'] = {"description": str(ib) if ib else "", "minimum_score": 4, "diploma_bonus": False}
            fixed = True
        else:
            if 'diploma_bonus' in ib and not isinstance(ib['diploma_bonus'], bool):
                ib['diploma_bonus'] = ensure_bool(ib['diploma_bonus'])
                fixed = True
    
    # Fix transfer_articulation
    if 'transfer_articulation' in cp:
        ta = cp['transfer_articulation']
        if not isinstance(ta, dict):
            cp['transfer_articulation'] = {"description": str(ta) if ta else ""}
            fixed = True
    
    return fixed

def fix_supplemental_requirements(profile):
    """Fix supplemental_requirements to be list of proper objects."""
    if 'application_process' not in profile:
        return False
    ap = profile['application_process']
    if 'supplemental_requirements' not in ap:
        return False
    
    reqs = ap['supplemental_requirements']
    if not isinstance(reqs, list):
        if reqs is None:
            ap['supplemental_requirements'] = []
            return True
        ap['supplemental_requirements'] = [{"requirement": str(reqs)}]
        return True
    
    fixed = False
    new_reqs = []
    for item in reqs:
        if isinstance(item, dict):
            new_reqs.append(item)
        elif isinstance(item, str):
            new_reqs.append({"requirement": item, "type": "essay"})
            fixed = True
        else:
            new_reqs.append({"requirement": str(item), "type": "other"})
            fixed = True
    
    if fixed:
        ap['supplemental_requirements'] = new_reqs
    return fixed

def fix_early_admission_stats(profile):
    """Fix early_admission_stats to be list with required fields."""
    if 'admissions_data' not in profile:
        return False
    ad = profile['admissions_data']
    if 'current_status' not in ad:
        return False
    cs = ad['current_status']
    if 'early_admission_stats' not in cs:
        return False
    
    stats = cs['early_admission_stats']
    
    # Ensure it's a list
    if not isinstance(stats, list):
        if isinstance(stats, dict):
            stats = [stats]
        else:
            cs['early_admission_stats'] = []
            return True
    
    fixed = False
    for item in stats:
        if isinstance(item, dict):
            if 'plan_type' not in item:
                item['plan_type'] = item.get('type', item.get('round', 'Early Decision'))
                fixed = True
    
    cs['early_admission_stats'] = stats
    return fixed

def fix_location(profile):
    """Fix location to have type field and be a proper object."""
    if 'metadata' not in profile:
        return False
    meta = profile['metadata']
    if 'location' not in meta:
        return False
    
    loc = meta['location']
    
    # If string, convert to object
    if isinstance(loc, str):
        parts = loc.split(',')
        meta['location'] = {
            "city": parts[0].strip() if parts else "",
            "state": parts[1].strip() if len(parts) > 1 else "",
            "type": "main_campus"
        }
        return True
    
    # If dict, ensure type field exists
    if isinstance(loc, dict):
        if 'type' not in loc:
            loc['type'] = "main_campus"
            return True
    
    return False

def fix_student_insights(profile):
    """Fix student_insights to have proper format."""
    if 'student_insights' not in profile:
        return False
    si = profile['student_insights']
    if 'insights' not in si:
        return False
    
    insights = si['insights']
    if not isinstance(insights, list):
        return False
    
    fixed = False
    new_insights = []
    for item in insights:
        if isinstance(item, str):
            new_insights.append({"insight": item, "source": "student_review"})
            fixed = True
        elif isinstance(item, dict):
            # Handle nested StudentInsight structure
            if 'StudentInsight' in item:
                inner = item['StudentInsight']
                if 'source' not in inner:
                    inner['source'] = 'student_review'
                    fixed = True
                new_insights.append(inner)
            else:
                if 'source' not in item:
                    item['source'] = 'student_review'
                    fixed = True
                new_insights.append(item)
        else:
            new_insights.append({"insight": str(item), "source": "student_review"})
            fixed = True
    
    if fixed:
        si['insights'] = new_insights
    return fixed

def fix_gender_breakdown(profile):
    """Fix gender_breakdown to have proper GenderStats objects."""
    if 'admissions_data' not in profile:
        return False
    ad = profile['admissions_data']
    if 'admitted_student_profile' not in ad:
        return False
    asp = ad['admitted_student_profile']
    if 'demographics' not in asp:
        return False
    demo = asp['demographics']
    if 'gender_breakdown' not in demo:
        return False
    
    gb = demo['gender_breakdown']
    if not isinstance(gb, dict):
        return False
    
    fixed = False
    for gender in ['men', 'women', 'other']:
        if gender in gb:
            val = gb[gender]
            if not isinstance(val, dict):
                # Convert number/string to object
                if isinstance(val, (int, float)):
                    gb[gender] = {"percentage": val}
                elif isinstance(val, str):
                    num = ensure_number(val)
                    gb[gender] = {"percentage": num if num else 0}
                else:
                    gb[gender] = {"percentage": 0}
                fixed = True
    
    return fixed

def fix_testing_submission_rate(profile):
    """Fix testing.submission_rate to be a number."""
    if 'admissions_data' not in profile:
        return False
    ad = profile['admissions_data']
    if 'admitted_student_profile' not in ad:
        return False
    asp = ad['admitted_student_profile']
    if 'testing' not in asp:
        return False
    testing = asp['testing']
    
    if 'submission_rate' in testing:
        val = testing['submission_rate']
        if not isinstance(val, (int, float)):
            testing['submission_rate'] = ensure_number(val)
            return True
    
    return False

def fix_majors_fields(profile):
    """Fix major fields like is_impacted, admissions_pathway."""
    if 'academic_structure' not in profile:
        return False
    acs = profile['academic_structure']
    if 'colleges' not in acs:
        return False
    
    fixed = False
    for college in acs.get('colleges', []):
        for major in college.get('majors', []):
            if 'is_impacted' in major and not isinstance(major['is_impacted'], bool):
                major['is_impacted'] = ensure_bool(major['is_impacted'])
                fixed = True
            if 'admissions_pathway' in major and not isinstance(major['admissions_pathway'], str):
                major['admissions_pathway'] = ensure_string(major['admissions_pathway'])
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
        ("minors_certificates", fix_minors_certificates),
        ("weeder_courses", fix_weeder_courses),
        ("credit_policies", fix_credit_policies),
        ("supplemental_requirements", fix_supplemental_requirements),
        ("early_admission_stats", fix_early_admission_stats),
        ("location", fix_location),
        ("student_insights", fix_student_insights),
        ("gender_breakdown", fix_gender_breakdown),
        ("testing_submission_rate", fix_testing_submission_rate),
        ("majors_fields", fix_majors_fields),
    ]
    
    for name, fix_func in fixes:
        try:
            if fix_func(profile):
                fixes_applied.append(name)
        except Exception as e:
            pass  # Skip failed fixes
    
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
