"""
Deterministic internal-consistency auditor for collected university profiles.
No LLM, no network — pure arithmetic/logic contradictions that prove whether the
stored data is internally coherent. If a profile fails these, the data is wrong
on its face (no external ground truth needed).
"""
import json, glob, sys, os
from collections import Counter

DIR = sys.argv[1] if len(sys.argv) > 1 else "research"
files = sorted(glob.glob(os.path.join(os.path.dirname(__file__), DIR, "*.json")))

def num(x):
    if isinstance(x, (int, float)): return float(x)
    if isinstance(x, str):
        try: return float(x.replace('%','').replace(',','').strip())
        except: return None
    return None

def rng(s):
    """parse 'X-Y' -> (X,Y)"""
    if not isinstance(s, str) or '-' not in s: return None
    parts = s.replace('–','-').split('-')
    try:
        lo, hi = float(parts[0].strip()), float(parts[-1].strip())
        return lo, hi
    except: return None

issue_counter = Counter()
per_file = {}
total = 0

for f in files:
    name = os.path.basename(f)
    issues = []
    try:
        d = json.load(open(f))
    except Exception as e:
        per_file[name] = [f"UNPARSEABLE: {e}"]; issue_counter["unparseable"] += 1; continue

    ad = d.get("admissions_data", {}) or {}
    cs = ad.get("current_status", {}) or {}
    asp = ad.get("admitted_student_profile", {}) or {}

    # 1. Fabricated/zero overall acceptance rate
    oar = num(cs.get("overall_acceptance_rate"))
    if oar == 0.0:
        issues.append("acceptance_rate==0.0 (fabricated by coercion / missing)"); issue_counter["accept_zero"] += 1
    elif oar is not None and not (0 < oar <= 100):
        issues.append(f"acceptance_rate out of range: {oar}"); issue_counter["accept_oor"] += 1
    elif oar is None:
        issues.append("acceptance_rate is null/missing"); issue_counter["accept_null"] += 1

    # 2. longitudinal arithmetic: admits/apps vs stated rate; yield vs enrolled/admits
    for t in (ad.get("longitudinal_trends") or []):
        apps, adm, enr = num(t.get("applications_total")), num(t.get("admits_total")), num(t.get("enrolled_total"))
        rate = num(t.get("acceptance_rate_overall"))
        yr = t.get("year")
        if apps and adm and rate is not None and apps > 0:
            calc = adm / apps * 100
            if rate > 0 and abs(calc - rate) > max(2.0, 0.15*rate):
                issues.append(f"{yr}: admits/apps={calc:.1f}% but acceptance_rate_overall={rate}%"); issue_counter["accept_arith"] += 1
        if apps in (0.0,) or adm in (0.0,):
            issues.append(f"{yr}: zero applications/admits (fabricated)"); issue_counter["trend_zero"] += 1
        yld = num(t.get("yield_rate"))
        if enr and adm and yld is not None and adm > 0 and yld > 0:
            calcy = enr / adm * 100
            if abs(calcy - yld) > max(3.0, 0.20*yld):
                issues.append(f"{yr}: enrolled/admits={calcy:.1f}% but yield_rate={yld}%"); issue_counter["yield_arith"] += 1
        # waitlist conversion
        ws = t.get("waitlist_stats") or {}
        acc, fromwl, wr = num(ws.get("accepted_spots")), num(ws.get("admitted_from_waitlist")), num(ws.get("waitlist_admit_rate"))
        if acc and fromwl is not None and wr is not None and acc > 0 and wr > 0:
            calcw = fromwl / acc * 100
            if abs(calcw - wr) > max(3.0, 0.25*wr):
                issues.append(f"{yr}: waitlist admitted/accepted={calcw:.1f}% but waitlist_admit_rate={wr}%"); issue_counter["wl_arith"] += 1

    # 3. racial breakdown sum
    rb = (asp.get("demographics", {}) or {}).get("racial_breakdown") or {}
    vals = [num(v) for v in rb.values() if num(v) is not None]
    if vals:
        s = sum(vals)
        if not (85 <= s <= 115):
            issues.append(f"racial_breakdown sums to {s:.0f}% (expect ~100)"); issue_counter["race_sum"] += 1

    # 4. SAT composite vs sections
    testing = asp.get("testing", {}) or {}
    comp, rd, mt = rng(testing.get("sat_composite_middle_50")), rng(testing.get("sat_reading_middle_50")), rng(testing.get("sat_math_middle_50"))
    if comp and rd and mt:
        lo = rd[0] + mt[0]; hi = rd[1] + mt[1]
        if abs(lo - comp[0]) > 40 or abs(hi - comp[1]) > 40:
            issues.append(f"SAT composite {testing.get('sat_composite_middle_50')} != R+M {int(lo)}-{int(hi)}"); issue_counter["sat_sum"] += 1
    if comp and not (400 <= comp[0] <= comp[1] <= 1600):
        issues.append(f"SAT composite range invalid: {testing.get('sat_composite_middle_50')}"); issue_counter["sat_oor"] += 1
    act = rng(testing.get("act_composite_middle_50"))
    if act and not (1 <= act[0] <= act[1] <= 36):
        issues.append(f"ACT range invalid: {testing.get('act_composite_middle_50')}"); issue_counter["act_oor"] += 1

    # 5. GPA range ordering / plausibility
    g = rng((asp.get("gpa", {}) or {}).get("weighted_middle_50"))
    if g and (g[0] > g[1] or g[1] > 5.5 or g[0] < 1.0):
        issues.append(f"weighted GPA range odd: {(asp.get('gpa',{}) or {}).get('weighted_middle_50')}"); issue_counter["gpa_odd"] += 1

    # 6. grad rate ordering
    sr = d.get("student_retention", {}) or {}
    g4, g6 = num(sr.get("graduation_rate_4_year")), num(sr.get("graduation_rate_6_year"))
    if g4 is not None and g6 is not None and g4 > g6 + 1:
        issues.append(f"4yr grad {g4}% > 6yr grad {g6}% (impossible)"); issue_counter["grad_order"] += 1
    for k in ("freshman_retention_rate","graduation_rate_4_year","graduation_rate_6_year"):
        v = num(sr.get(k))
        if v == 0.0: issues.append(f"{k}==0.0 (fabricated/missing)"); issue_counter["retention_zero"] += 1

    # 7. us_news_rank sanity
    rank = (d.get("strategic_profile", {}) or {}).get("us_news_rank")
    if isinstance(rank, int) and not (1 <= rank <= 450):
        issues.append(f"us_news_rank implausible: {rank}"); issue_counter["rank_oor"] += 1

    # 8. provenance: are sources recorded at all?
    rsf = (d.get("metadata", {}) or {}).get("report_source_files") or []
    if not rsf:
        issue_counter["no_provenance"] += 1  # counted, not per-file noise

    # 9. early admission rate sanity
    for e in (cs.get("early_admission_stats") or []):
        er = num(e.get("acceptance_rate"))
        if er is not None and not (0 < er <= 100):
            issues.append(f"early {e.get('plan_type')} rate oor: {er}"); issue_counter["early_oor"] += 1

    if issues:
        per_file[name] = issues
        total += 1

print(f"AUDITED {len(files)} profiles in '{DIR}'\n")
print(f"Profiles with >=1 internal contradiction: {total}/{len(files)} ({100*total/max(len(files),1):.0f}%)")
print(f"Profiles with NO recorded source/provenance: {issue_counter['no_provenance']}/{len(files)}\n")
print("=== Issue-type frequency (across all profiles) ===")
for k, v in issue_counter.most_common():
    print(f"  {v:4d}  {k}")
print("\n=== Sample of 12 flagged profiles ===")
for nm, iss in list(per_file.items())[:12]:
    print(f"\n• {nm}")
    for i in iss[:5]:
        print(f"    - {i}")
