#!/usr/bin/env python3
"""
Audit essay prompts across all university research files.
"""
import json
from pathlib import Path
from collections import defaultdict

RESEARCH_DIR = Path("agents/university_profile_collector/research")

def safe_get(obj, *keys):
    """Safely navigate nested dicts/lists."""
    for key in keys:
        if obj is None:
            return None
        if isinstance(obj, dict):
            obj = obj.get(key)
        elif isinstance(obj, list) and isinstance(key, int) and len(obj) > key:
            obj = obj[key]
        else:
            return None
    return obj

def count_essay_prompts(data):
    """Check various paths for essay prompts and return count and path."""
    paths_to_check = [
        ('application_process', 'supplemental_requirements', 'essay_prompts'),
        ('application_process', 'essay_prompts'),
        ('university_profile', 'application_process', 'supplemental_requirements', 'essay_prompts'),
        ('university_profile', 'application_process', 'essay_prompts'),
    ]
    
    for path_tuple in paths_to_check:
        prompts = safe_get(data, *path_tuple)
        if prompts and isinstance(prompts, list) and len(prompts) > 0:
            return len(prompts), '.'.join(path_tuple)
    
    return 0, None

def main():
    json_files = sorted(RESEARCH_DIR.glob("*.json"))
    
    results = {
        'missing': [],
        'low_count': [],
        'good': [],
        'uc_schools': [],
    }
    
    errors = []
    
    for json_file in json_files:
        name = json_file.stem
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            # Skip if top-level is a list (shouldn't happen)
            if isinstance(data, list):
                errors.append((name, "Root is a list"))
                continue
            
            count, path = count_essay_prompts(data)
            
            # Check if UC school (should have 8 PIQs)
            is_uc = 'university_of_california' in name or name.startswith('uc_')
            
            if count == 0:
                results['missing'].append(name)
            elif is_uc:
                results['uc_schools'].append((name, count))
            else:
                results['good'].append((name, count))
                    
        except Exception as e:
            errors.append((name, str(e)))
    
    # Report
    print("=" * 70)
    print("ESSAY PROMPTS AUDIT REPORT")
    print("=" * 70)
    
    print(f"\n❌ MISSING ESSAY PROMPTS ({len(results['missing'])} universities):")
    print("-" * 50)
    for name in results['missing'][:20]:  # Show first 20
        print(f"  • {name}")
    if len(results['missing']) > 20:
        print(f"  ... and {len(results['missing']) - 20} more")
    
    print(f"\n✅ UC SCHOOLS ({len(results['uc_schools'])}):")
    print("-" * 50)
    for name, count in results['uc_schools']:
        status = "✓" if count == 8 else f"⚠️ {count}/8"
        print(f"  {status} {name}")
    
    # Count distribution for non-UC schools
    print(f"\n✅ OTHER UNIVERSITIES WITH PROMPTS ({len(results['good'])}):")
    print("-" * 50)
    count_dist = defaultdict(list)
    for name, count in results['good']:
        count_dist[count].append(name)
    for cnt in sorted(count_dist.keys()):
        names = count_dist[cnt]
        print(f"  • {len(names)} universities with {cnt} prompt(s)")
        if cnt >= 3:  # Show which ones have 3+
            for n in names[:5]:
                print(f"      - {n}")
            if len(names) > 5:
                print(f"      ... and {len(names) - 5} more")
    
    if errors:
        print(f"\n⚠️ ERRORS ({len(errors)}):")
        print("-" * 50)
        for name, err in errors[:10]:
            print(f"  • {name}: {err}")
    
    print("\n" + "=" * 70)
    total = len(results['missing']) + len(results['good']) + len(results['uc_schools'])
    print(f"SUMMARY: {total} files checked")
    print(f"  Missing: {len(results['missing'])}")
    print(f"  UC Schools: {len(results['uc_schools'])}")
    print(f"  Other with prompts: {len(results['good'])}")
    print(f"  Errors: {len(errors)}")
    print("=" * 70)

if __name__ == "__main__":
    main()
