
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# =============================================================================
# ROADMAP TEMPLATES
# =============================================================================

TEMPLATES = {
    'freshman_fall': {
        'title': 'Freshman Fall: Transition & Foundation',
        'phases': [
            {
                'id': 'phase_adjustment',
                'name': 'High School Transition',
                'date_range': 'Aug - Oct',
                'tasks': [
                    {'id': 'task_adjust_schedule', 'title': 'Adjust to High School Schedule & Workload', 'type': 'core'},
                    {'id': 'task_explore_clubs', 'title': 'Explore Extracurricular Activities & Clubs', 'type': 'core'},
                    {'id': 'task_study_habits', 'title': 'Develop Strong Study Habits', 'type': 'core'}
                ]
            },
            {
                'id': 'phase_engagement',
                'name': 'Academic & Social Engagement',
                'date_range': 'Oct - Dec',
                'tasks': [
                    {'id': 'task_join_activities', 'title': 'Join 1-2 Extracurricular Activities', 'type': 'core'},
                    {'id': 'task_meet_counselor', 'title': 'Meet with School Counselor', 'type': 'optional'},
                    {'id': 'task_maintain_grades', 'title': 'Maintain Strong Academic Performance', 'type': 'core'}
                ]
            }
        ]
    },
    'freshman_spring': {
        'title': 'Freshman Spring: Building Momentum',
        'phases': [
            {
                'id': 'phase_planning',
                'name': 'Course & Activity Planning',
                'date_range': 'Jan - Mar',
                'tasks': [
                    {'id': 'task_course_selection', 'title': 'Select Challenging Courses for Sophomore Year', 'type': 'core'},
                    {'id': 'task_deepen_involvement', 'title': 'Deepen Commitment to Activities', 'type': 'core'},
                    {'id': 'task_explore_interests', 'title': 'Explore Academic & Career Interests', 'type': 'optional'}
                ]
            },
            {
                'id': 'phase_summer_prep',
                'name': 'Summer Preparation',
                'date_range': 'Apr - May',
                'tasks': [
                    {'id': 'task_summer_programs', 'title': 'Research Summer Programs or Activities', 'type': 'optional'},
                    {'id': 'task_volunteer', 'title': 'Consider Volunteer or Service Opportunities', 'type': 'optional'},
                    {'id': 'task_finish_strong', 'title': 'Finish Freshman Year Strong Academically', 'type': 'core'}
                ]
            }
        ]
    },
    'sophomore_fall': {
        'title': 'Sophomore Fall: Exploration & Growth',
        'phases': [
            {
                'id': 'phase_rigor',
                'name': 'Academic Rigor',
                'date_range': 'Aug - Oct',
                'tasks': [
                    {'id': 'task_challenging_courses', 'title': 'Excel in More Challenging Course Load', 'type': 'core'},
                    {'id': 'task_psat', 'title': 'Take PSAT/NMSQT for Practice', 'type': 'core'},
                    {'id': 'task_leadership_roles', 'title': 'Seek Leadership Roles in Activities', 'type': 'optional'}
                ]
            },
            {
                'id': 'phase_career_exploration',
                'name': 'Career Exploration',
                'date_range': 'Oct - Dec',
                'tasks': [
                    {'id': 'task_career_research', 'title': 'Research Potential Career Paths', 'type': 'optional'},
                    {'id': 'task_job_shadow', 'title': 'Consider Job Shadowing Opportunities', 'type': 'optional'},
                    {'id': 'task_build_resume', 'title': 'Start Building an Activities Resume', 'type': 'core'}
                ]
            }
        ]
    },
    'sophomore_spring': {
        'title': 'Sophomore Spring: Pre-College Prep',
        'phases': [
            {
                'id': 'phase_junior_prep',
                'name': 'Junior Year Preparation',
                'date_range': 'Jan - Mar',
                'tasks': [
                    {'id': 'task_honors_ap', 'title': 'Select Honors/AP Courses for Junior Year', 'type': 'core'},
                    {'id': 'task_test_prep_start', 'title': 'Begin SAT/ACT Preparation', 'type': 'optional'},
                    {'id': 'task_college_research', 'title': 'Start Researching Colleges (Informally)', 'type': 'optional'}
                ]
            },
            {
                'id': 'phase_commitment',
                'name': 'Activity Commitment',
                'date_range': 'Apr - May',
                'tasks': [
                    {'id': 'task_leadership_pursuit', 'title': 'Pursue Leadership Positions for Junior Year', 'type': 'core'},
                    {'id': 'task_summer_enrichment', 'title': 'Plan Meaningful Summer Activities', 'type': 'core'},
                    {'id': 'task_community_service', 'title': 'Continue/Expand Community Service', 'type': 'optional'}
                ]
            }
        ]
    },
    'junior_fall': {
        'title': 'Junior Fall: Critical Year Begins',
        'phases': [
            {
                'id': 'phase_academics',
                'name': 'Academic Excellence',
                'date_range': 'Aug - Oct',
                'tasks': [
                    {'id': 'task_excel_difficult', 'title': 'Excel in Most Difficult Courses', 'type': 'core'},
                    {'id': 'task_test_prep', 'title': 'Continue SAT/ACT Preparation', 'type': 'core'},
                    {'id': 'task_psat_junior', 'title': 'Take PSAT/NMSQT (National Merit Qualifier)', 'type': 'core'}
                ]
            },
            {
                'id': 'phase_testing_start',
                'name': 'Testing Strategy',
                'date_range': 'Oct - Dec',
                'tasks': [
                    {'id': 'task_test_schedule', 'title': 'Schedule SAT/ACT for Spring', 'type': 'core'},
                    {'id': 'task_college_fairs', 'title': 'Attend College Fairs & Information Sessions', 'type': 'optional'},
                    {'id': 'task_leadership_impact', 'title': 'Make Meaningful Impact in Leadership Roles', 'type': 'core'}
                ]
            }
        ]
    },
    'junior_spring': {
        'title': 'Junior Spring: Building the Foundation',
        'phases': [
            {
                'id': 'phase_discovery',
                'name': 'Discovery & Research',
                'date_range': 'Jan - May',
                'tasks': [
                    {'id': 'task_preferences', 'title': 'Define College Preferences (Size, Location, Major)', 'type': 'core'},
                    {'id': 'task_initial_list', 'title': 'Build Initial College List (15-20 schools)', 'type': 'core'},
                    {'id': 'task_virtual_tours', 'title': 'Attend Virtual Tours or Visit Campuses', 'type': 'optional'}
                ]
            },
            {
                'id': 'phase_testing',
                'name': 'Standardized Testing',
                'date_range': 'Mar - Jun',
                'tasks': [
                    {'id': 'task_sat_act_register', 'title': 'Register for SAT/ACT', 'type': 'core'},
                    {'id': 'task_sat_act_prep', 'title': 'Complete Prep Course / Self-Study', 'type': 'core'},
                    {'id': 'task_sat_act_take', 'title': 'Take SAT/ACT', 'type': 'core'}
                ]
            },
            {
                'id': 'phase_letters',
                'name': 'Letters of Recommendation',
                'date_range': 'May - Jun',
                'tasks': [
                    {'id': 'task_ask_teacher_1', 'title': 'Ask Teacher #1 for Recommendation', 'type': 'core'},
                    {'id': 'task_ask_teacher_2', 'title': 'Ask Teacher #2 for Recommendation', 'type': 'core'},
                    {'id': 'task_brag_sheet', 'title': 'Complete "Brag Sheet" for Counselor', 'type': 'core'}
                ]
            }
        ]
    },
    'junior_summer': {
        'title': 'Junior Summer: Strategic Essay & Application Prep',
        'phases': [
            {
                'id': 'phase_essay_foundation',
                'name': 'Essay Foundation (START EARLY!)',
                'date_range': 'Jun - Jul',
                'tasks': [
                    {'id': 'task_brainstorm_topics', 'title': '📝 Brainstorm 5-7 Personal Essay Topics', 'type': 'core', 'description': 'Identify unique stories, experiences, or perspectives that define you'},
                    {'id': 'task_create_outline', 'title': 'Create Essay Outline for Personal Statement', 'type': 'core'},
                    {'id': 'task_draft_1_personal', 'title': '✍️ COMPLETE First Draft of Personal Statement (650 words)', 'type': 'deadline', 'due_date': 'July 15'},
                    {'id': 'task_research_supplements', 'title': 'Research Top 5 Schools\' Supplement Prompts', 'type': 'core'},
                    {'id': 'task_activity_list', 'title': 'Draft Activities List (all 10 slots)', 'type': 'core'}
                ]
            },
            {
                'id': 'phase_essay_refinement',
                'name': 'Essay Refinement',
                'date_range': 'Jul - Aug',
                'tasks': [
                    {'id': 'task_feedback_draft_1', 'title': 'Get Feedback from 2-3 Trusted Readers', 'type': 'core'},
                    {'id': 'task_draft_2_personal', 'title': '✍️ Revise Personal Statement (Draft 2)', 'type': 'core'},
                    {'id': 'task_start_supplements', 'title': 'Start Drafting "Why Us?" Essays for Top 3 Schools', 'type': 'core'},
                    {'id': 'task_draft_uc_piqs', 'title': 'Draft 4 UC PIQs (if applying to UCs)', 'type': 'core'},
                    {'id': 'task_common_app_account', 'title': 'Create Common App Account & Fill Profile Sections', 'type': 'core'}
                ]
            },
            {
                'id': 'phase_app_prep',
                'name': 'Application Preparation',
                'date_range': 'Aug',
                'tasks': [
                    {'id': 'task_finalize_personal', 'title': '🎯 FINALIZE Personal Statement (by Aug 15)', 'type': 'deadline', 'due_date': 'August 15'},
                    {'id': 'task_lor_followup', 'title': 'Follow Up with Recommenders', 'type': 'core'},
                    {'id': 'task_refine_list', 'title': 'Narrow College List to 10-15 Schools', 'type': 'core'},
                    {'id': 'task_early_apps_identify', 'title': 'Identify ED/EA Schools & Deadlines', 'type': 'core'},
                    {'id': 'task_financial_docs', 'title': 'Gather Financial Documents (for FAFSA/CSS)', 'type': 'optional'}
                ]
            }
        ]
    },
    'senior_fall': {
        'title': 'Senior Fall: Execution Mode',
        'phases': [
            {
                'id': 'phase_early_apps',
                'name': '🚨 Early Applications (ED/EA)',
                'date_range': 'Sep 1 - Oct 15',
                'tasks': [
                    {'id': 'task_ed_supplements_final', 'title': '✍️ FINALIZE ED School Supplements (2 weeks before deadline)', 'type': 'deadline'},
                    {'id': 'task_proofread_all', 'title': 'Proofread ALL Essays - No Typos!', 'type': 'core'},
                    {'id': 'task_submit_ed_ea', 'title': '🎯 Submit ED/EA Applications (by Oct 25 - NOT last minute!)', 'type': 'deadline'},
                    {'id': 'task_confirm_lors', 'title': 'Confirm Recommenders Have Submitted', 'type': 'core'}
                ]
            },
            {
                'id': 'phase_regular_essays',
                'name': 'Regular Decision Essays',
                'date_range': 'Oct - Nov',
                'tasks': [
                    {'id': 'task_rd_supplements', 'title': 'Draft ALL Remaining Supplements (Complete by Nov 15)', 'type': 'core'},
                    {'id': 'task_essay_review_2', 'title': 'Second Round of Feedback on Supplements', 'type': 'core'},
                    {'id': 'task_finalize_rd_essays', 'title': '🎯 Finalize RD Essays (by Dec 15)', 'type': 'deadline'}
                ]
            },
            {
                'id': 'phase_financials',
                'name': 'Financial Aid',
                'date_range': 'Oct 1 - Nov 15',
                'tasks': [
                    {'id': 'task_fafsa', 'title': '💰 Submit FAFSA (Opens Oct 1 - Submit by Oct 15)', 'type': 'deadline'},
                    {'id': 'task_css_profile', 'title': '💰 Submit CSS Profile (by Nov 1 for ED schools)', 'type': 'deadline'},
                    {'id': 'task_scholarship_apps', 'title': 'Identify & Start Merit Scholarship Applications', 'type': 'core'}
                ]
            },
            {
                'id': 'phase_rd_submission',
                'name': 'Regular Decision Submission',
                'date_range': 'Dec - Jan 1',
                'tasks': [
                    {'id': 'task_common_app_complete', 'title': 'Complete All Common App Sections', 'type': 'core'},
                    {'id': 'task_submit_rd', 'title': '🎯 Submit ALL RD Applications (by Dec 28 - NOT Jan 1!)', 'type': 'deadline'},
                    {'id': 'task_verify_complete', 'title': 'Verify All Materials Received by Each School', 'type': 'core'}
                ]
            }
        ]
    },
    'senior_spring': {
        'title': 'Senior Spring: Final Push & Decisions',
        'phases': [
            {
                'id': 'phase_final_apps',
                'name': 'Final Applications',
                'date_range': 'Jan - Feb',
                'tasks': [
                    {'id': 'task_submit_regular', 'title': 'Submit Regular Decision Applications', 'type': 'core'},
                    {'id': 'task_verify_materials', 'title': 'Verify All Materials Received by Colleges', 'type': 'core'},
                    {'id': 'task_update_activities', 'title': 'Send Updates on Achievements (if significant)', 'type': 'optional'}
                ]
            },
            {
                'id': 'phase_scholarships',
                'name': 'Scholarship Season',
                'date_range': 'Jan - Mar',
                'tasks': [
                    {'id': 'task_local_scholarships', 'title': 'Apply for Local Scholarships', 'type': 'core'},
                    {'id': 'task_national_scholarships', 'title': 'Apply for National Scholarships', 'type': 'core'},
                    {'id': 'task_financial_aid_appeals', 'title': 'Prepare Financial Aid Appeal Letters (if needed)', 'type': 'optional'}
                ]
            },
            {
                'id': 'phase_decisions',
                'name': 'Decision Time',
                'date_range': 'Mar - May',
                'tasks': [
                    {'id': 'task_review_offers', 'title': 'Review All Admission Offers', 'type': 'core'},
                    {'id': 'task_compare_aid', 'title': 'Compare Financial Aid Packages', 'type': 'core'},
                    {'id': 'task_revisit_days', 'title': 'Attend Accepted Student Days', 'type': 'optional'},
                    {'id': 'task_commit', 'title': 'Submit Enrollment Deposit (by May 1)', 'type': 'deadline'},
                    {'id': 'task_housing', 'title': 'Apply for Housing', 'type': 'core'}
                ]
            }
        ]
    }
}




# Import tools
from counselor_tools import fetch_aggregated_deadlines, get_student_profile, get_college_list

# =============================================================================
# GRADE & SEMESTER RESOLUTION
# =============================================================================
# These helpers map (caller hints + profile + current date) → a template key.
# Behavior is additive over the legacy logic that lived inline in
# generate_roadmap: callers that pass BOTH grade_level and semester get their
# values honored; otherwise the resolver falls back to the existing
# graduation_year + month-based inference. The bar for "honor caller" is
# intentionally high — passing only grade_level (which today's frontend
# hardcodes to '11th Grade') does NOT trigger override, so we don't break
# users whose profile.graduation_year is up-to-date while the frontend still
# ships a stale grade.

VALID_SEMESTERS = ('fall', 'spring', 'summer')

# Some grade/semester combos don't have their own template (academic calendar
# doesn't really have a freshman-summer or senior-summer phase). Fall back to
# the spring template of the same grade — that's the closest semantic match
# and matches the legacy behavior for senior summer.
_TEMPLATE_FALLBACKS = {
    'freshman_summer': 'freshman_spring',
    'sophomore_summer': 'sophomore_spring',
    'senior_summer': 'senior_spring',
}


def semester_from_date(now=None):
    """Return 'fall' (Aug-Dec), 'spring' (Jan-May), or 'summer' (Jun-Jul)."""
    now = now or datetime.now()
    m = now.month
    if 8 <= m <= 12:
        return 'fall'
    if 1 <= m <= 5:
        return 'spring'
    return 'summer'


def grade_name_from_grade_level(grade_level):
    """
    Map a UI-style grade label ('9th Grade', 'Junior', '11th', etc.) to one
    of ('freshman', 'sophomore', 'junior', 'senior'). Returns None if the
    string doesn't clearly indicate a grade.
    """
    if not grade_level or not isinstance(grade_level, str):
        return None
    g = grade_level.lower()
    if '9' in g or 'freshman' in g:
        return 'freshman'
    if '10' in g or 'sophomore' in g:
        return 'sophomore'
    if '11' in g or 'junior' in g:
        return 'junior'
    if '12' in g or 'senior' in g:
        return 'senior'
    return None


def grade_name_from_graduation_year(grad_year, now=None):
    """
    Compute the student's current grade name from their graduation year and
    today's date, mirroring the inline mapping that used to live in
    generate_roadmap (so users without caller-provided overrides see the same
    template they got before this refactor).
    """
    now = now or datetime.now()
    years_until_grad = grad_year - now.year
    semester = semester_from_date(now)

    if years_until_grad <= 0:
        return 'senior'
    if years_until_grad == 1:
        return 'senior' if semester == 'fall' else 'junior'
    if years_until_grad == 2:
        return 'junior' if semester == 'fall' else 'sophomore'
    if years_until_grad == 3:
        return 'sophomore' if semester == 'fall' else 'freshman'
    return 'freshman'


def _compose_template_key(grade, semester):
    """Compose '<grade>_<semester>' with the summer-fallback table applied."""
    candidate = f'{grade}_{semester}'
    if candidate in TEMPLATES:
        return candidate
    return _TEMPLATE_FALLBACKS.get(candidate)


def resolve_template_key(grade_level=None, semester=None, profile=None, now=None):
    """
    Pick a template key honoring caller hints when both are provided, else
    falling back to profile.graduation_year + computed semester, else default.

    Returns (template_key, source) where source is one of:
      'caller'  — both grade_level and semester were provided and resolved.
      'profile' — derived from profile.graduation_year + computed semester.
      'default' — no usable input; conservative default ('senior_fall').
    """
    sem_in = semester if semester in VALID_SEMESTERS else None
    grade_in = grade_name_from_grade_level(grade_level)

    # Caller wins only when BOTH are provided AND resolve to a known template.
    if grade_in and sem_in:
        key = _compose_template_key(grade_in, sem_in)
        if key:
            return key, 'caller'

    # Profile-based fallback. Compute semester from date (Aug-Dec=fall, etc.).
    computed_sem = sem_in or semester_from_date(now)
    grad_year = None
    if profile:
        try:
            grad_year_raw = profile.get('graduation_year')
            grad_year = int(grad_year_raw) if grad_year_raw else None
        except (TypeError, ValueError):
            grad_year = None

    if grad_year:
        computed_grade = grade_name_from_graduation_year(grad_year, now=now)
        key = _compose_template_key(computed_grade, computed_sem)
        if key:
            return key, 'profile'

    # Last resort: caller passed grade alone but no profile/grad_year? Use it.
    if grade_in:
        key = _compose_template_key(grade_in, computed_sem)
        if key:
            return key, 'caller-grade-only'

    return 'senior_fall', 'default'


# =============================================================================
# COLLEGE-SPECIFIC TRANSLATION
# =============================================================================

def get_college_context(user_email):
    """
    Fetch college list and build context for roadmap personalization.
    
    Returns:
        {
            'colleges': [...],  # List of colleges with deadlines
            'uc_schools': ['UCI', 'UCSD'],  # Grouped UC school names
            'has_early_decision': bool,
            'has_early_action': bool
        }
    """
    try:
        deadlines = fetch_aggregated_deadlines(user_email)
        
        uc_schools = []
        has_ed = False
        has_ea = False
        
        colleges = []
        for d in deadlines:
            uni_id = d['university_id']
            uni_name = d['university_name']
            
            # Check if UC school
            if 'university_of_california' in uni_id.lower():
                # Extract short name
                short_name = uni_name
                if 'Los Angeles' in uni_name or 'los_angeles' in uni_id:
                    short_name = 'UCLA'
                elif 'San Diego' in uni_name or 'san_diego' in uni_id:
                    short_name = 'UCSD'
                elif 'Berkeley' in uni_name or 'berkeley' in uni_id:
                    short_name = 'UC Berkeley'
                elif 'Davis' in uni_name:
                    short_name = 'UC Davis'
                elif 'Irvine' in uni_name:
                    short_name = 'UCI'
                elif 'Santa Barbara' in uni_name:
                    short_name = 'UCSB'
                elif 'Santa Cruz' in uni_name:
                    short_name = 'UCSC'
                elif 'Riverside' in uni_name:
                    short_name = 'UCR'
                elif 'Merced' in uni_name:
                    short_name = 'UC Merced'
                
                if short_name not in uc_schools:
                    uc_schools.append(short_name)
            
            # Check deadline types
            deadline_type = d.get('deadline_type', '').lower()
            if 'early decision' in deadline_type or 'ed' in deadline_type:
                has_ed = True
            if 'early action' in deadline_type or 'ea' in deadline_type:
                has_ea = True
            
            colleges.append({
                'id': uni_id,
                'name': uni_name,
                'deadline': d.get('date'),
                'deadline_type': d.get('deadline_type'),
                'is_uc': 'university_of_california' in uni_id.lower()
            })
        
        return {
            'colleges': colleges,
            'uc_schools': sorted(set(uc_schools)),
            'has_early_decision': has_ed,
            'has_early_action': has_ea
        }
    except Exception as e:
        logger.error(f"Error getting college context: {e}")
        return {'colleges': [], 'uc_schools': [], 'has_early_decision': False, 'has_early_action': False}


# =============================================================================
# ARTIFACT REFS — cross-link template tasks to the right tab/item
# =============================================================================
# Tasks that resolve to a specific college, scholarship, or essay get an
# `artifact_ref` field. The frontend renders this as a clickable badge that
# navigates via `deep_link`. Kept additive: tasks without a clear artifact
# omit the field entirely; existing consumers ignore unknown fields.

def _college_artifact_ref(college):
    """
    Build an artifact_ref pointing at the Colleges tab focused on this school.
    Returns None when the college dict lacks an id (data quality guard).
    """
    if not college or not college.get('id'):
        return None
    uni_id = college['id']
    name = college.get('name') or uni_id
    return {
        'type': 'college',
        'university_id': uni_id,
        'label': f'Open {name}',
        'deep_link': f'/roadmap?tab=colleges&school={uni_id}',
    }


def _tab_artifact_ref(tab, label):
    """
    Build a tab-level artifact_ref (no specific item id). Used when a task
    relates to a surface but doesn't resolve to a single row — e.g.,
    "Apply for need-based scholarships" → just the Scholarships tab.
    """
    return {
        'type': 'tab',
        'tab': tab,
        'label': label,
        'deep_link': f'/roadmap?tab={tab}',
    }


def translate_rd_submission(task, context):
    """Translate 'Submit RD Applications' to specific colleges."""
    tasks = []
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    # Group UCs if present
    if context['uc_schools']:
        uc_names = ', '.join(context['uc_schools'])
        # Find UC deadline + a representative UC college to anchor the deep link.
        uc_deadline = None
        uc_anchor = None
        for college in context['colleges']:
            if college['is_uc']:
                uc_deadline = uc_deadline or college.get('deadline')
                uc_anchor = uc_anchor or college
                if uc_deadline and uc_anchor:
                    break

        if uc_deadline:
            # Check if overdue
            is_overdue = uc_deadline < current_date
            overdue_marker = "⚠️ OVERDUE - " if is_overdue else ""

            uc_task = {
                'id': 'task_submit_uc',
                'title': f"{overdue_marker}Submit UC Application ({uc_names}) - Deadline: {uc_deadline}",
                'due_date': uc_deadline,
                'type': 'deadline',
                'is_overdue': is_overdue
            }
            uc_ref = _college_artifact_ref(uc_anchor)
            if uc_ref:
                # Override the label so the badge reads "Open UCs" rather than
                # the anchor school's full name.
                uc_ref = {**uc_ref, 'label': f'Open {uc_names}'}
                uc_task['artifact_ref'] = uc_ref
            tasks.append(uc_task)

    # Individual non-UC colleges
    for college in context['colleges']:
        if not college['is_uc']:
            deadline = college.get('deadline', '')
            is_overdue = deadline and deadline < current_date
            overdue_marker = "⚠️ OVERDUE - " if is_overdue else ""

            college_task = {
                'id': f"task_submit_{college['id']}",
                'title': f"{overdue_marker}Submit {college['name']} - Deadline: {deadline}",
                'due_date': deadline,
                'type': 'deadline',
                'is_overdue': is_overdue
            }
            ref = _college_artifact_ref(college)
            if ref:
                college_task['artifact_ref'] = ref
            tasks.append(college_task)

    return tasks if tasks else [task]  # Fallback to generic if no colleges



def translate_essay_tasks(task, context):
    """Translate 'Complete Essays/Supplements' to specific prompts."""
    tasks = []

    # UC PIQs: tab-level link only — UCs share 8 prompts and the user picks 4,
    # so there isn't a single canonical essay row to resolve against.
    if context['uc_schools']:
        uc_names = ', '.join(context['uc_schools'])
        tasks.append({
            'id': 'task_uc_piqs',
            'title': f"Complete 4 of 8 UC PIQs ({uc_names})",
            'type': 'core',
            'artifact_ref': _tab_artifact_ref('essays', 'Open Essays'),
        })

    # Other colleges' supplements: link to that school's row in the Colleges
    # tab. Resolving to the specific essay_tracker row is a future PR — for
    # now the per-school landing is enough to make the task actionable.
    for college in context['colleges']:
        if not college['is_uc']:
            college_task = {
                'id': f"task_essays_{college['id']}",
                'title': f"Complete {college['name']} supplemental essays",
                'type': 'core'
            }
            ref = _college_artifact_ref(college)
            if ref:
                college_task['artifact_ref'] = ref
            tasks.append(college_task)

    return tasks if tasks else [task]


def translate_verification(task, context):
    """Translate 'Verify Materials' to specific colleges."""
    if not context['colleges']:
        return [task]

    college_names = ', '.join([c['name'] for c in context['colleges'][:5]])  # Max 5 for readability
    count = len(context['colleges'])

    return [{
        'id': 'task_verify_materials',
        'title': f"Verify all materials received by {college_names}{' and more' if count > 5 else ''} ({count} colleges)",
        'type': 'core',
        # Verification is a multi-school task; route to the Colleges tab landing
        # so the user sees per-school cards and can confirm each in turn.
        'artifact_ref': _tab_artifact_ref('colleges', 'Open Colleges'),
    }]


def translate_task(generic_task, college_context):
    """
    Main translation dispatcher - converts generic tasks to college-specific ones.
    
    Returns: List of specific tasks (may be 1 or multiple)
    """
    title = generic_task.get('title', '')
    
    # Translation rules - check if generic title contains these patterns
    if 'Submit' in title and ('Regular Decision' in title or 'RD Applications' in title or 'Applications' in title):
        return translate_rd_submission(generic_task, college_context)
    
    elif 'Essay' in title or 'Supplement' in title:
        return translate_essay_tasks(generic_task, college_context)
    
    elif 'Verify' in title and 'Materials' in title:
        return translate_verification(generic_task, college_context)
    
    # No match → return generic task unchanged
    return [generic_task]


def generate_roadmap(request):
    """
    Generate or retrieve a student roadmap.
    Payload: {
        "user_email":   "student@example.com",     # required for personalization
        "grade_level":  "12th Grade",              # optional caller hint
        "semester":     "fall" | "spring" | "summer"  # optional caller hint
    }
    Caller-provided (grade_level, semester) win when BOTH are present and
    resolve to a known template; otherwise the resolver falls back to
    profile.graduation_year + the current month's semester.
    Returns: dict (not Response object)
    """
    try:
        data = request.get_json() or {}
        user_email = data.get('user_email')
        caller_grade_level = data.get('grade_level')
        caller_semester = data.get('semester')

        profile = get_student_profile(user_email) if user_email else None

        template_key, resolution_source = resolve_template_key(
            grade_level=caller_grade_level,
            semester=caller_semester,
            profile=profile,
        )
        logger.info(
            f"[ROADMAP] Resolved template_key={template_key} source={resolution_source} "
            f"(caller_grade={caller_grade_level!r}, caller_semester={caller_semester!r}, "
            f"profile_grad_year={(profile or {}).get('graduation_year')!r})"
        )

        # Get base template — DEEP-copy because we mutate phase['tasks'] below
        # when translating template tasks to college-specific ones. A shallow
        # .copy() would let the mutation leak into the global TEMPLATES dict
        # and corrupt subsequent /roadmap requests for any user (every user
        # would see the previous user's translated tasks).
        import copy as _copy
        template = _copy.deepcopy(TEMPLATES.get(template_key, TEMPLATES['senior_fall']))
        
        # Get college context and translate tasks to be college-specific
        college_context = None
        if user_email:
            college_context = get_college_context(user_email)
            logger.info(f"[ROADMAP] Got college context: {len(college_context.get('colleges', []))} colleges, UC schools: {college_context.get('uc_schools', [])}")
        
        # Translate each task in each phase
        if college_context and college_context.get('colleges'):
            for phase in template['phases']:
                translated_tasks = []
                
                for generic_task in phase['tasks']:
                    # Translate → may return 1 or multiple tasks
                    specific_tasks = translate_task(generic_task, college_context)
                    translated_tasks.extend(specific_tasks)
                
                phase['tasks'] = translated_tasks
            
            logger.info(f"[ROADMAP] Translated template tasks to college-specific tasks")
        else:
            logger.info(f"[ROADMAP] No college list - using generic template tasks")
        
        # Surface the resolved grade/semester so the client can render labels
        # consistently with what the server actually used (and so debug logs
        # can be cross-referenced quickly).
        resolved_grade, _, resolved_semester = template_key.partition('_')
        return {
            'success': True,
            'roadmap': template,
            'metadata': {
                'template_used': template_key,
                'grade_used': resolved_grade,
                'semester_used': resolved_semester,
                'resolution_source': resolution_source,
                'colleges_count': len(college_context.get('colleges', [])) if college_context else 0,
                'personalized': bool(college_context and college_context.get('colleges')),
                'last_updated': datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating roadmap: {e}")
        # Return dict with error, main.py deals with status code if success=False check needed
        # But for now, returning simple dict, main.py defaults to 200 unless we return tuple
        return {'success': False, 'error': str(e)}


def generate_personalized_tasks(user_email):
    """
    Generate personalized roadmap tasks based on user's college list.
    Creates tasks for:
    - Essay drafts (2 weeks before deadline)
    - Essay final review (1 week before deadline)
    - Application submission (3 days before deadline)
    - Financial aid (FAFSA, CSS Profile)
    
    Returns list of tasks to be saved to Firestore.
    """
    try:
        from counselor_tools import get_college_list, get_targeted_university_context
        from datetime import datetime, timedelta
        
        college_list = get_college_list(user_email)
        university_context = get_targeted_university_context(user_email)
        
        tasks = []
        current_date = datetime.now()
        
        # Track FAFSA/CSS to avoid duplicates
        fafsa_added = False
        css_added = False
        
        for college in college_list:
            uni_id = college.get('university_id')
            uni_name = college.get('university_name', uni_id)
            status = college.get('status', 'Planning')
            
            # Skip if already applied/admitted/enrolled
            if status in ['Applied', 'Admitted', 'Enrolled', 'Rejected', 'Deferred']:
                continue
            
            uni_data = university_context.get(uni_id, {})
            deadlines = uni_data.get('deadlines', [])
            scholarships = uni_data.get('scholarships', [])
            
            # Process each deadline
            for deadline in deadlines:
                deadline_date_str = deadline.get('date')
                deadline_type = deadline.get('plan_type', deadline.get('type', 'Regular'))
                
                # Skip non-date values or past deadlines
                if not deadline_date_str or len(deadline_date_str) < 10:
                    continue
                    
                try:
                    deadline_date = datetime.strptime(deadline_date_str[:10], '%Y-%m-%d')
                except ValueError:
                    continue
                
                # Skip past deadlines
                if deadline_date < current_date:
                    continue
                
                # Calculate lead times
                draft_date = deadline_date - timedelta(days=14)
                review_date = deadline_date - timedelta(days=7)
                submit_date = deadline_date - timedelta(days=3)
                
                # Only create tasks for future dates
                if draft_date > current_date:
                    tasks.append({
                        'task_id': f"essay_draft_{uni_id}_{deadline_type.lower().replace(' ', '_')}",
                        'university_id': uni_id,
                        'university_name': uni_name,
                        'task_type': 'essay',
                        'title': f"Draft {deadline_type} Essays for {uni_name}",
                        'description': f"Write first drafts of supplemental essays for {uni_name}'s {deadline_type} application.",
                        'due_date': draft_date.strftime('%Y-%m-%d'),
                        'deadline_source': f"{deadline_type}: {deadline_date_str}",
                        'status': 'pending',
                        'priority': 'high' if (draft_date - current_date).days < 14 else 'medium'
                    })
                
                if review_date > current_date:
                    tasks.append({
                        'task_id': f"essay_review_{uni_id}_{deadline_type.lower().replace(' ', '_')}",
                        'university_id': uni_id,
                        'university_name': uni_name,
                        'task_type': 'essay_review',
                        'title': f"Review & Finalize Essays for {uni_name}",
                        'description': f"Final review and polish of essays for {uni_name}'s {deadline_type} application.",
                        'due_date': review_date.strftime('%Y-%m-%d'),
                        'deadline_source': f"{deadline_type}: {deadline_date_str}",
                        'status': 'pending',
                        'priority': 'high' if (review_date - current_date).days < 7 else 'medium'
                    })
                
                if submit_date > current_date:
                    tasks.append({
                        'task_id': f"submit_{uni_id}_{deadline_type.lower().replace(' ', '_')}",
                        'university_id': uni_id,
                        'university_name': uni_name,
                        'task_type': 'submission',
                        'title': f"Submit {deadline_type} Application to {uni_name}",
                        'description': f"Final check and submit {deadline_type} application to {uni_name}.",
                        'due_date': submit_date.strftime('%Y-%m-%d'),
                        'deadline_source': f"{deadline_type}: {deadline_date_str}",
                        'status': 'pending',
                        'priority': 'critical' if (submit_date - current_date).days < 5 else 'high'
                    })
            
            # Add scholarship tasks for schools with separate applications
            for scholarship in scholarships:
                if scholarship.get('application_method') and 'separate' in scholarship.get('application_method', '').lower():
                    scholarship_deadline = scholarship.get('deadline')
                    if scholarship_deadline and scholarship_deadline not in ['Automatic', 'Auto', 'N/A']:
                        tasks.append({
                            'task_id': f"scholarship_{uni_id}_{scholarship.get('name', 'general').lower().replace(' ', '_')}",
                            'university_id': uni_id,
                            'university_name': uni_name,
                            'task_type': 'scholarship',
                            'title': f"Apply for {scholarship.get('name')} at {uni_name}",
                            'description': f"{scholarship.get('name')}: {scholarship.get('amount', 'Varies')}. {scholarship.get('benefits', '')}",
                            'due_date': scholarship_deadline,
                            'status': 'pending',
                            'priority': 'medium'
                        })
        
        # Add universal financial aid tasks
        # FAFSA opens Oct 1
        fafsa_deadline = datetime(current_date.year if current_date.month >= 10 else current_date.year, 10, 15)
        if fafsa_deadline > current_date and not fafsa_added:
            tasks.append({
                'task_id': 'fafsa_submission',
                'university_id': None,
                'university_name': 'All Schools',
                'task_type': 'financial_aid',
                'title': 'Submit FAFSA',
                'description': 'File Free Application for Federal Student Aid (opens Oct 1). Required for all federal financial aid.',
                'due_date': fafsa_deadline.strftime('%Y-%m-%d'),
                'deadline_source': 'FAFSA',
                'status': 'pending',
                'priority': 'high'
            })
            fafsa_added = True
        
        # CSS Profile - typically Nov 1 for EA/ED, varies for RD
        css_deadline = datetime(current_date.year if current_date.month >= 10 else current_date.year, 11, 1)
        if css_deadline > current_date and not css_added:
            tasks.append({
                'task_id': 'css_profile',
                'university_id': None,
                'university_name': 'Private Schools',
                'task_type': 'financial_aid',
                'title': 'Submit CSS Profile',
                'description': 'Submit CSS Profile for private universities that require it (check each school\'s requirements).',
                'due_date': css_deadline.strftime('%Y-%m-%d'),
                'deadline_source': 'CSS Profile',
                'status': 'pending',
                'priority': 'high'
            })
            css_added = True
        
        # Sort by due_date
        tasks.sort(key=lambda x: x.get('due_date', '9999-99-99'))
        
        logger.info(f"[PLANNER] Generated {len(tasks)} personalized tasks for {user_email}")
        
        return {
            'success': True,
            'tasks': tasks,
            'count': len(tasks)
        }
        
    except Exception as e:
        logger.error(f"Error generating personalized tasks: {e}")
        return {'success': False, 'error': str(e)}


def save_personalized_tasks(user_email, tasks):
    """
    Save generated tasks to Firestore via Profile Manager.
    """
    import requests
    import os
    
    PROFILE_MANAGER_URL = os.getenv('PROFILE_MANAGER_URL', 'http://localhost:8080')
    
    saved_count = 0
    for task in tasks:
        try:
            response = requests.post(
                f"{PROFILE_MANAGER_URL}/save-roadmap-task",
                json={
                    'user_email': user_email,
                    'task_id': task['task_id'],
                    'task_data': task
                },
                timeout=10
            )
            if response.status_code == 200:
                saved_count += 1
        except Exception as e:
            logger.error(f"Failed to save task {task['task_id']}: {e}")
    
    logger.info(f"[PLANNER] Saved {saved_count}/{len(tasks)} tasks for {user_email}")
    return {
        'success': True,
        'saved_count': saved_count,
        'total_count': len(tasks)
    }
