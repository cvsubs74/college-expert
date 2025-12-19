
import re
import json
import logging

logger = logging.getLogger(__name__)

def fix_escape_sequences(content: str) -> str:
    """Fix invalid escape sequences like \\' -> '"""
    return content.replace("\\'", "'")

def fix_json_syntax(content: str) -> str:
    """Fix common JSON syntax issues."""
    content = re.sub(r',(\s*[}\]])', r'\1', content)
    return content

def fix_is_waitlist_ranked(data: dict) -> int:
    fixes = 0
    if 'admissions_data' in data and 'longitudinal_trends' in data['admissions_data']:
        for trend in data['admissions_data']['longitudinal_trends']:
            if 'waitlist_stats' in trend:
                ws = trend['waitlist_stats']
                if 'is_waitlist_ranked' in ws:
                    val = ws['is_waitlist_ranked']
                    if not isinstance(val, bool):
                        ws['is_waitlist_ranked'] = False
                        fixes += 1
                else:
                    ws['is_waitlist_ranked'] = False
                    fixes += 1
    return fixes

def fix_report_source_files(data: dict) -> int:
    fixes = 0
    if 'metadata' in data and 'report_source_files' in data['metadata']:
        rsf = data['metadata']['report_source_files']
        if isinstance(rsf, list):
            if any(not isinstance(x, str) for x in rsf):
                data['metadata']['report_source_files'] = []
                fixes += 1
    return fixes

def fix_rank_in_category(data: dict) -> int:
    fixes = 0
    if 'strategic_profile' in data and 'rankings' in data['strategic_profile']:
        for ranking in data['strategic_profile']['rankings']:
            if 'rank_in_category' in ranking:
                val = ranking['rank_in_category']
                if isinstance(val, str):
                    ranking['rank_in_category'] = None
                    fixes += 1
    return fixes

def fix_admissions_pathway(data: dict) -> int:
    fixes = 0
    if 'academic_structure' in data and 'colleges' in data['academic_structure']:
        for college in data['academic_structure']['colleges']:
            if 'admissions_model' in college:
                if not isinstance(college['admissions_model'], str) or college['admissions_model'] is None:
                    college['admissions_model'] = "Not specified"
                    fixes += 1
            if 'majors' in college:
                for major in college['majors']:
                    if 'admissions_pathway' in major:
                        if not isinstance(major['admissions_pathway'], str) or major['admissions_pathway'] is None:
                            major['admissions_pathway'] = "Not specified"
                            fixes += 1
    return fixes

def fix_is_impacted(data: dict) -> int:
    fixes = 0
    if 'academic_structure' in data and 'colleges' in data['academic_structure']:
        for college in data['academic_structure']['colleges']:
            if 'majors' in college:
                for major in college['majors']:
                    if 'is_impacted' in major:
                        val = major['is_impacted']
                        if not isinstance(val, bool):
                            major['is_impacted'] = False
                            fixes += 1
    return fixes

def fix_geographic_breakdown(data: dict) -> int:
    fixes = 0
    try:
        if 'admissions_data' in data:
            profile = data['admissions_data'].get('admitted_student_profile', {})
            demographics = profile.get('demographics', {})
            if 'geographic_breakdown' in demographics:
                gb = demographics['geographic_breakdown']
                if isinstance(gb, list):
                    valid_entries = []
                    for entry in gb:
                        if isinstance(entry, dict) and 'percentage' in entry:
                            pct = entry['percentage']
                            if isinstance(pct, (int, float)):
                                valid_entries.append(entry)
                            elif isinstance(pct, str):
                                try:
                                    entry['percentage'] = float(pct.replace('%', ''))
                                    valid_entries.append(entry)
                                    fixes += 1
                                except:
                                    fixes += 1
                            else:
                                fixes += 1
                        elif isinstance(entry, dict):
                            valid_entries.append(entry)
                    demographics['geographic_breakdown'] = valid_entries
    except Exception:
        pass
    return fixes

def fix_integer_fields(data: dict) -> int:
    fixes = 0
    if 'admissions_data' in data and 'longitudinal_trends' in data['admissions_data']:
        for trend in data['admissions_data']['longitudinal_trends']:
            for field in ['applications_total', 'admits_total', 'enrolled_total']:
                if field in trend:
                    val = trend[field]
                    if val is None or isinstance(val, str):
                        trend[field] = 0
                        fixes += 1
            if 'acceptance_rate_overall' in trend:
                val = trend['acceptance_rate_overall']
                if val is not None and isinstance(val, str):
                    try:
                        trend['acceptance_rate_overall'] = float(val.replace('%', ''))
                        fixes += 1
                    except:
                        trend['acceptance_rate_overall'] = 0.0
                        fixes += 1
    return fixes

def fix_gender_breakdown(data: dict) -> int:
    fixes = 0
    try:
        if 'admissions_data' in data:
            profile = data['admissions_data'].get('admitted_student_profile', {})
            demographics = profile.get('demographics', {})
            gb = demographics.get('gender_breakdown', {})
            for gender in ['men', 'women']:
                if gender in gb and isinstance(gb[gender], dict):
                    if 'note' in gb[gender]:
                        if gb[gender]['note'] is None:
                            gb[gender]['note'] = "Not specified"
                            fixes += 1
                        elif not isinstance(gb[gender]['note'], str):
                            gb[gender]['note'] = str(gb[gender]['note'])
                            fixes += 1
            if 'non_binary' in gb:
                val = gb['non_binary']
                if val is not None and not isinstance(val, dict):
                    gb['non_binary'] = None
                    fixes += 1
    except Exception:
        pass
    return fixes

def fix_gpa_percentiles(data: dict) -> int:
    fixes = 0
    try:
        if 'admissions_data' in data:
            profile = data['admissions_data'].get('admitted_student_profile', {})
            gpa = profile.get('gpa', {})
            for field in ['percentile_25', 'percentile_75']:
                if field in gpa:
                    val = gpa[field]
                    if val is not None and not isinstance(val, str):
                        gpa[field] = str(val) if val else None
                        fixes += 1
    except Exception:
        pass
    return fixes

def fix_average_gpa_admitted(data: dict) -> int:
    fixes = 0
    try:
        if 'academic_structure' in data and 'colleges' in data['academic_structure']:
            for college in data['academic_structure']['colleges']:
                if 'majors' in college:
                    for major in college['majors']:
                        if 'average_gpa_admitted' in major:
                            val = major['average_gpa_admitted']
                            if isinstance(val, dict):
                                major['average_gpa_admitted'] = None
                                fixes += 1
                            elif isinstance(val, str):
                                try:
                                    major['average_gpa_admitted'] = float(val)
                                    fixes += 1
                                except:
                                    major['average_gpa_admitted'] = None
                                    fixes += 1
    except Exception:
        pass
    return fixes

def fix_restrictions(data: dict) -> int:
    fixes = 0
    try:
        if 'credit_policies' in data:
            ta = data['credit_policies'].get('transfer_articulation', {})
            if 'restrictions' in ta:
                val = ta['restrictions']
                if not isinstance(val, str):
                    if isinstance(val, list):
                        ta['restrictions'] = "; ".join(str(x) for x in val)
                    else:
                        ta['restrictions'] = "None specified"
                    fixes += 1
    except Exception:
        pass
    return fixes

def fix_supplemental_requirements(data: dict) -> int:
    fixes = 0
    try:
        if 'application_process' in data:
            reqs = data['application_process'].get('supplemental_requirements', [])
            if isinstance(reqs, list):
                for req in reqs:
                    if isinstance(req, dict):
                        if 'target_program' not in req:
                            req['target_program'] = "General"
                            fixes += 1
                        if 'requirement_type' not in req:
                            req['requirement_type'] = "Not specified"
                            fixes += 1
    except Exception:
        pass
    return fixes

def fix_acceptance_rate_overall(data: dict) -> int:
    fixes = 0
    try:
        if 'admissions_data' in data:
            cs = data['admissions_data'].get('current_status', {})
            if 'overall_acceptance_rate' in cs:
                val = cs['overall_acceptance_rate']
                if val is None or isinstance(val, str):
                    if isinstance(val, str):
                        try:
                            cs['overall_acceptance_rate'] = float(val.replace('%', '').strip())
                            fixes += 1
                        except:
                            cs['overall_acceptance_rate'] = 0.0
                            fixes += 1
                    else:
                        cs['overall_acceptance_rate'] = 0.0
                        fixes += 1
            if 'longitudinal_trends' in data['admissions_data']:
                for trend in data['admissions_data']['longitudinal_trends']:
                    if 'acceptance_rate_overall' in trend:
                        val = trend['acceptance_rate_overall']
                        if val is None or isinstance(val, str):
                            if isinstance(val, str):
                                try:
                                    trend['acceptance_rate_overall'] = float(val.replace('%', '').strip())
                                    fixes += 1
                                except:
                                    trend['acceptance_rate_overall'] = 0.0
                                    fixes += 1
                            else:
                                trend['acceptance_rate_overall'] = 0.0
                                fixes += 1
    except Exception:
        pass
    return fixes

def fix_notes_fields(data: dict) -> int:
    fixes = 0
    try:
        if 'admissions_data' in data:
            if 'longitudinal_trends' in data['admissions_data']:
                for trend in data['admissions_data']['longitudinal_trends']:
                    if 'notes' in trend:
                        if not isinstance(trend['notes'], str):
                            trend['notes'] = str(trend['notes']) if trend['notes'] else ""
                            fixes += 1
            profile = data['admissions_data'].get('admitted_student_profile', {})
            gpa = profile.get('gpa', {})
            if 'notes' in gpa:
                if not isinstance(gpa['notes'], str):
                    gpa['notes'] = str(gpa['notes']) if gpa['notes'] else ""
                    fixes += 1
    except Exception:
        pass
    return fixes

def fix_is_restricted_or_capped(data: dict) -> int:
    fixes = 0
    try:
        if 'academic_structure' in data and 'colleges' in data['academic_structure']:
            for college in data['academic_structure']['colleges']:
                if 'is_restricted_or_capped' in college:
                    if not isinstance(college['is_restricted_or_capped'], bool):
                        college['is_restricted_or_capped'] = False
                        fixes += 1
    except Exception:
        pass
    return fixes

def fix_holistic_factors(data: dict) -> int:
    fixes = 0
    try:
        if 'application_process' in data:
            hf = data['application_process'].get('holistic_factors', {})
            for field in ['legacy_consideration', 'first_gen_boost', 'demonstrated_interest']:
                if field in hf:
                    if not isinstance(hf[field], str):
                        hf[field] = str(hf[field]) if hf[field] else "Not specified"
                        fixes += 1
    except Exception:
        pass
    return fixes

def fix_major_acceptance_rate(data: dict) -> int:
    fixes = 0
    try:
        if 'academic_structure' in data and 'colleges' in data['academic_structure']:
            for college in data['academic_structure']['colleges']:
                if 'majors' in college:
                    for major in college['majors']:
                        if 'acceptance_rate' in major:
                            val = major['acceptance_rate']
                            if isinstance(val, dict):
                                major['acceptance_rate'] = None
                                fixes += 1
                            elif isinstance(val, str):
                                try:
                                    major['acceptance_rate'] = float(val.replace('%', ''))
                                    fixes += 1
                                except:
                                    major['acceptance_rate'] = None
                                    fixes += 1
    except Exception:
        pass
    return fixes

def fix_geographic_breakdown_type(data: dict) -> int:
    fixes = 0
    try:
        if 'admissions_data' in data:
            profile = data['admissions_data'].get('admitted_student_profile', {})
            demographics = profile.get('demographics', {})
            if 'geographic_breakdown' in demographics:
                if not isinstance(demographics['geographic_breakdown'], list):
                    demographics['geographic_breakdown'] = []
                    fixes += 1
    except Exception:
        pass
    return fixes

def fix_top_employers_type(data: dict) -> int:
    fixes = 0
    try:
        if 'outcomes' in data:
            if 'top_employers' in data['outcomes']:
                if not isinstance(data['outcomes']['top_employers'], list):
                    data['outcomes']['top_employers'] = []
                    fixes += 1
    except Exception:
        pass
    return fixes

def fix_waitlist_year(data: dict) -> int:
    fixes = 0
    try:
        if 'admissions_data' in data and 'longitudinal_trends' in data['admissions_data']:
            for trend in data['admissions_data']['longitudinal_trends']:
                if 'waitlist_stats' in trend:
                    ws = trend['waitlist_stats']
                    if 'year' not in ws or ws['year'] is None:
                        ws['year'] = trend.get('year', 2024)
                        fixes += 1
    except Exception:
        pass
    return fixes

def apply_all_fixes(data: dict) -> tuple[dict, int]:
    """Applies all available fixes to the data dictionary."""
    total_fixes = 0
    total_fixes += fix_is_waitlist_ranked(data)
    total_fixes += fix_report_source_files(data)
    total_fixes += fix_rank_in_category(data)
    total_fixes += fix_admissions_pathway(data)
    total_fixes += fix_is_impacted(data)
    total_fixes += fix_geographic_breakdown(data)
    total_fixes += fix_integer_fields(data)
    total_fixes += fix_gender_breakdown(data)
    total_fixes += fix_gpa_percentiles(data)
    total_fixes += fix_average_gpa_admitted(data)
    total_fixes += fix_restrictions(data)
    total_fixes += fix_supplemental_requirements(data)
    total_fixes += fix_acceptance_rate_overall(data)
    total_fixes += fix_notes_fields(data)
    total_fixes += fix_is_restricted_or_capped(data)
    total_fixes += fix_holistic_factors(data)
    total_fixes += fix_major_acceptance_rate(data)
    total_fixes += fix_geographic_breakdown_type(data)
    total_fixes += fix_top_employers_type(data)
    total_fixes += fix_waitlist_year(data)
    return data, total_fixes
