#!/usr/bin/env python3
"""
Final comprehensive schema fix that CORRECTLY handles all issues.
This script reverses bad fixes and properly formats data.
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
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]

def ensure_string(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ['name', 'title', 'text', 'value', 'description', 'insight']:
            if key in value:
                return str(value[key])
        return json.dumps(value)
    return str(value)

def ensure_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, str):
        return value.lower() in ('true', 'yes', '1')
    return bool(value)

def ensure_number(value):
    if isinstance(value, (int, float)):
        return value
    if value is None:
        return None
    if isinstance(value, str):
        match = re.search(r'[\d.]+', value)
        if match:
            try:
                return float(match.group())
            except:
                pass
    return None

def fix_student_insights_properly(profile):
    """
    Fix student_insights.insights to be List[Union[StudentInsight, str]].
    StudentInsight requires: source, category, insight (all strings).
    Strings are also allowed as-is.
    """
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
            # Strings are valid as-is
            new_insights.append(item)
        elif isinstance(item, dict):
            # Check if it's nested incorrectly as {"StudentInsight": {...}}
            if 'StudentInsight' in item and isinstance(item['StudentInsight'], dict):
                inner = item['StudentInsight']
                # Ensure required fields
                proper = {
                    "source": inner.get('source', 'student_review'),
                    "category": inner.get('category', 'general'),
                    "insight": inner.get('insight', '')
                }
                new_insights.append(proper)
                fixed = True
            # Check if it's already a proper StudentInsight (has insight field)
            elif 'insight' in item:
                proper = {
                    "source": item.get('source', 'student_review'),
                    "category": item.get('category', 'general'),
                    "insight": item.get('insight', '')
                }
                if proper != item:
                    fixed = True
                new_insights.append(proper)
            # Check if it has text-like field we can use as insight
            elif any(k in item for k in ['text', 'tip', 'advice', 'comment']):
                text = item.get('text') or item.get('tip') or item.get('advice') or item.get('comment')
                proper = {
                    "source": item.get('source', 'student_review'),
                    "category": item.get('category', 'general'),
                    "insight": str(text) if text else ''
                }
                new_insights.append(proper)
                fixed = True
            else:
                # Can't parse, convert whole thing to string
                new_insights.append(json.dumps(item))
                fixed = True
        else:
            new_insights.append(str(item))
            fixed = True
    
    if fixed or new_insights != insights:
        si['insights'] = new_insights
        return True
    return False

def fix_essay_tips(profile):
    """Fix essay_tips to be List[str]."""
    if 'student_insights' not in profile:
        return False
    si = profile['student_insights']
    if 'essay_tips' not in si:
        return False
    
    tips = si['essay_tips']
    if not isinstance(tips, list):
        if tips is None:
            si['essay_tips'] = []
            return True
        elif isinstance(tips, str):
            si['essay_tips'] = [tips] if tips else []
            return True
        return False
    
    fixed = False
    new_tips = []
    for item in tips:
        if isinstance(item, str):
            new_tips.append(item)
        elif isinstance(item, dict):
            text = item.get('tip') or item.get('text') or item.get('advice') or str(item)
            new_tips.append(text)
            fixed = True
        else:
            new_tips.append(str(item))
            fixed = True
    
    if fixed:
        si['essay_tips'] = new_tips
    return fixed

def fix_major_selection_tactics(profile):
    """Fix major_selection_tactics to be List[str]."""
    if 'application_strategy' not in profile:
        return False
    aps = profile['application_strategy']
    if 'major_selection_tactics' not in aps:
        return False
    
    tactics = aps['major_selection_tactics']
    if not isinstance(tactics, list):
        if tactics is None:
            aps['major_selection_tactics'] = []
            return True
        elif isinstance(tactics, str):
            aps['major_selection_tactics'] = [tactics] if tactics else []
            return True
        return False
    return False

def fix_transfer_articulation_restrictions(profile):
    """Fix transfer_articulation.restrictions to be string."""
    if 'credit_policies' not in profile:
        return False
    cp = profile['credit_policies']
    if 'transfer_articulation' not in cp:
        return False
    ta = cp['transfer_articulation']
    if not isinstance(ta, dict):
        return False
    
    if 'restrictions' in ta and not isinstance(ta['restrictions'], str):
        ta['restrictions'] = ensure_string(ta['restrictions'])
        return True
    return False

def fix_colleges_name(profile):
    """Ensure all colleges have name field."""
    if 'academic_structure' not in profile:
        return False
    acs = profile['academic_structure']
    if 'colleges' not in acs:
        return False
    
    fixed = False
    for i, college in enumerate(acs.get('colleges', [])):
        if 'name' not in college or not college['name']:
            # Try to extract from other fields
            college['name'] = college.get('college_name') or college.get('title') or f"College {i+1}"
            fixed = True
    return fixed

def fix_minors_to_strings(profile):
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
            name = item.get('name') or item.get('title') or item.get('minor_name') or str(item)
            new_items.append(name)
            fixed = True
        else:
            new_items.append(str(item))
            fixed = True
    
    if fixed:
        acs['minors_certificates'] = new_items
    return fixed

def fix_location_type(profile):
    """Ensure location has type field."""
    if 'metadata' not in profile:
        return False
    meta = profile['metadata']
    if 'location' not in meta:
        return False
    
    loc = meta['location']
    if isinstance(loc, str):
        parts = loc.split(',')
        meta['location'] = {
            "city": parts[0].strip() if parts else "",
            "state": parts[1].strip() if len(parts) > 1 else "",
            "type": "main_campus"
        }
        return True
    
    if isinstance(loc, dict) and 'type' not in loc:
        loc['type'] = "main_campus"
        return True
    return False

def fix_credit_policies_objects(profile):
    """Fix ap_policy, ib_policy, transfer_articulation to be proper objects."""
    if 'credit_policies' not in profile:
        return False
    cp = profile['credit_policies']
    fixed = False
    
    # ap_policy
    if 'ap_policy' in cp:
        ap = cp['ap_policy']
        if not isinstance(ap, dict):
            cp['ap_policy'] = {"general_rule": str(ap) if ap else "", "exceptions": [], "usage": ""}
            fixed = True
        else:
            if 'exceptions' in ap and not isinstance(ap['exceptions'], list):
                ap['exceptions'] = [ap['exceptions']] if ap['exceptions'] else []
                fixed = True
    
    # ib_policy
    if 'ib_policy' in cp:
        ib = cp['ib_policy']
        if not isinstance(ib, dict):
            cp['ib_policy'] = {"general_rule": str(ib) if ib else "", "diploma_bonus": False}
            fixed = True
        else:
            if 'diploma_bonus' in ib and not isinstance(ib['diploma_bonus'], bool):
                ib['diploma_bonus'] = ensure_bool(ib['diploma_bonus'])
                fixed = True
    
    # transfer_articulation
    if 'transfer_articulation' in cp:
        ta = cp['transfer_articulation']
        if not isinstance(ta, dict):
            cp['transfer_articulation'] = {"tools": [], "restrictions": str(ta) if ta else ""}
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
        ("student_insights", fix_student_insights_properly),
        ("essay_tips", fix_essay_tips),
        ("major_selection_tactics", fix_major_selection_tactics),
        ("transfer_restrictions", fix_transfer_articulation_restrictions),
        ("colleges_name", fix_colleges_name),
        ("minors_certificates", fix_minors_to_strings),
        ("location_type", fix_location_type),
        ("credit_policies", fix_credit_policies_objects),
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
