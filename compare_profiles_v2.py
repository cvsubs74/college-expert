import json
import os

files = [
    ("research/yale_university.json", "Latest"),
    ("research-0/yale_university.json", "Backup"),
    ("research/yale_university-0.json", "Version 0"),
    ("research/yale_university-1.json", "Version 1")
]

base_path = "/Users/cvsubramanian/CascadeProjects/graphrag/agents/college_counselor/agents/university_profile_collector/"

def count_populated(obj, depth=0):
    """Count non-null, non-empty values recursively"""
    if obj is None:
        return 0, 1  # 0 populated, 1 total
    if isinstance(obj, str):
        return (1, 1) if obj.strip() and obj.lower() not in ['n/a', 'null', 'unknown'] else (0, 1)
    if isinstance(obj, (int, float, bool)):
        return 1, 1
    if isinstance(obj, list):
        if not obj:
            return 0, 1
        pop, tot = 0, 0
        for item in obj:
            p, t = count_populated(item, depth+1)
            pop += p
            tot += t
        return pop, tot
    if isinstance(obj, dict):
        pop, tot = 0, 0
        for v in obj.values():
            p, t = count_populated(v, depth+1)
            pop += p
            tot += t
        return pop, tot
    return 1, 1

def get_key_metrics(data):
    """Extract key metrics for comparison"""
    metrics = {}
    
    # File basics
    metrics['has_id'] = '_id' in data
    
    # Strategic Profile
    sp = data.get('strategic_profile', {}) or {}
    metrics['has_executive_summary'] = bool(sp.get('executive_summary'))
    metrics['us_news_rank'] = sp.get('us_news_rank')
    metrics['analyst_takeaways'] = len(sp.get('analyst_takeaways', []) or [])
    
    # Admissions
    ad = data.get('admissions_data', {}) or {}
    cs = ad.get('current_status', {}) or {}
    metrics['acceptance_rate'] = cs.get('overall_acceptance_rate')
    metrics['longitudinal_years'] = len(ad.get('longitudinal_trends', []) or [])
    
    # Academic Structure
    ac = data.get('academic_structure', {}) or {}
    colleges = ac.get('colleges', []) or []
    metrics['colleges_count'] = len(colleges)
    total_majors = sum(len(c.get('majors', []) or []) for c in colleges if isinstance(c, dict))
    metrics['total_majors'] = total_majors
    
    # Scholarships
    sch = data.get('scholarships', {}) or {}
    if isinstance(sch, list):
        metrics['scholarships_count'] = len(sch)
    else:
        metrics['scholarships_count'] = len(sch.get('merit_scholarships', []) or [])
    
    # Financials
    fin = data.get('financials', {}) or {}
    tf = fin.get('tuition_and_fees', {}) or {}
    metrics['has_tuition'] = tf.get('in_state_tuition') is not None or tf.get('out_of_state_tuition') is not None
    
    # Outcomes
    out = data.get('outcomes', {}) or {}
    metrics['has_outcomes'] = bool(out.get('top_employers') or out.get('median_earnings'))
    
    # Application
    app = data.get('application_process', {}) or {}
    metrics['essay_prompts'] = len(app.get('supplemental_requirements', []) or [])
    
    return metrics

results = []

for fpath, label in files:
    full_path = os.path.join(base_path, fpath)
    if not os.path.exists(full_path):
        print(f"⚠️  {label}: FILE NOT FOUND")
        continue
    
    try:
        with open(full_path, 'r') as f:
            data = json.load(f)
        
        size = os.path.getsize(full_path)
        populated, total = count_populated(data)
        completeness = (populated / total * 100) if total > 0 else 0
        metrics = get_key_metrics(data)
        
        results.append({
            'label': label,
            'file': os.path.basename(fpath),
            'size': size,
            'populated': populated,
            'total': total,
            'completeness': completeness,
            **metrics
        })
    except Exception as e:
        print(f"⚠️  {label}: ERROR - {e}")

# Sort by completeness score (populated fields)
results.sort(key=lambda x: x['populated'], reverse=True)

print("\n" + "="*80)
print("YALE UNIVERSITY PROFILE COMPARISON - RANKED BY COMPREHENSIVENESS")
print("="*80)

for i, r in enumerate(results, 1):
    print(f"\n🏆 RANK #{i}: {r['label']} ({r['file']})")
    print("-" * 50)
    print(f"   📊 Size: {r['size']:,} bytes")
    print(f"   ✅ Populated Fields: {r['populated']:,} / {r['total']:,} ({r['completeness']:.1f}%)")
    print(f"   📈 US News Rank: {r['us_news_rank']}")
    print(f"   🎓 Acceptance Rate: {r['acceptance_rate']}%")
    print(f"   📚 Colleges: {r['colleges_count']} | Majors: {r['total_majors']}")
    print(f"   💰 Scholarships Listed: {r['scholarships_count']}")
    print(f"   📅 Historical Years: {r['longitudinal_years']}")
    print(f"   📝 Essay Prompts: {r['essay_prompts']}")
    print(f"   💼 Has Outcomes Data: {'Yes' if r['has_outcomes'] else 'No'}")
    print(f"   💵 Has Tuition Data: {'Yes' if r['has_tuition'] else 'No'}")

print("\n" + "="*80)
print("SUMMARY: Higher populated fields = more comprehensive data")
print("="*80)
