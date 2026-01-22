
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
from counselor_tools import fetch_aggregated_deadlines, get_student_profile

def generate_roadmap(request):
    """
    Generate or retrieve a student roadmap.
    Payload: { "grade_level": "12th Grade", "user_email": "student@example.com" }
    Returns: dict (not Response object)
    """
    try:
        data = request.get_json()
        user_email = data.get('user_email')
        
        # Determine grade level from profile graduation_year if available
        template_key = 'senior_fall'  # Default
        
        if user_email:
            profile = get_student_profile(user_email)
            
            if profile and profile.get('graduation_year'):
                from datetime import datetime
                current_year = datetime.now().year
                current_month = datetime.now().month
                grad_year = int(profile.get('graduation_year'))
                
                # Calculate current grade based on graduation year
                # School year: Aug-May, with graduation typically in May/June
                # Determine current semester: Fall (Aug-Dec), Spring (Jan-May), Summer (Jun-Jul)
                years_until_grad = grad_year - current_year
                is_fall = current_month >= 8  # Aug-Dec
                is_spring = 1 <= current_month <= 5  # Jan-May
                
                # Map years to grade level and semester
                if years_until_grad == 0:
                    # Graduating this year - Senior Spring (Jan-May) or post-graduation
                    if is_spring:
                        template_key = 'senior_spring'
                        logger.info(f"[ROADMAP] Student graduating {grad_year} = Senior Spring (current: {current_year}-{current_month:02d})")
                    else:
                        # June onwards after graduation - default to spring
                        template_key = 'senior_spring'
                        logger.info(f"[ROADMAP] Student graduated {grad_year}, showing Senior Spring timeline (current: {current_year}-{current_month:02d})")
                        
                elif years_until_grad == 1:
                    # Graduating next year - Senior Fall, Junior Summer, or Junior Spring
                    is_summer = 6 <= current_month <= 7  # June-July = Summer
                    
                    if is_fall:
                        template_key = 'senior_fall'
                        logger.info(f"[ROADMAP] Student graduating {grad_year} = Senior Fall (current: {current_year}-{current_month:02d})")
                    elif is_summer:
                        # Rising senior in summer - CRITICAL TIME for essay prep
                        template_key = 'junior_summer'
                        logger.info(f"[ROADMAP] Student graduating {grad_year} = Junior Summer (current: {current_year}-{current_month:02d})")
                    else:
                        template_key = 'junior_spring'
                        logger.info(f"[ROADMAP] Student graduating {grad_year} = Junior Spring (current: {current_year}-{current_month:02d})")
                        
                elif years_until_grad == 2:
                    # Graduating in 2 years - Junior or Sophomore
                    if is_fall:
                        template_key = 'junior_fall'
                        logger.info(f"[ROADMAP] Student graduating {grad_year} = Junior Fall (current: {current_year}-{current_month:02d})")
                    else:
                        template_key = 'sophomore_spring'
                        logger.info(f"[ROADMAP] Student graduating {grad_year} = Sophomore Spring (current: {current_year}-{current_month:02d})")
                        
                elif years_until_grad == 3:
                    # Graduating in 3 years - Sophomore or Freshman
                    if is_fall:
                        template_key = 'sophomore_fall'
                        logger.info(f"[ROADMAP] Student graduating {grad_year} = Sophomore Fall (current: {current_year}-{current_month:02d})")
                    else:
                        template_key = 'freshman_spring'
                        logger.info(f"[ROADMAP] Student graduating {grad_year} = Freshman Spring (current: {current_year}-{current_month:02d})")
                        
                elif years_until_grad >= 4:
                    # Graduating in 4+ years - Freshman or earlier
                    if is_fall:
                        template_key = 'freshman_fall'
                        logger.info(f"[ROADMAP] Student graduating {grad_year} = Freshman Fall (current: {current_year}-{current_month:02d})")
                    else:
                        template_key = 'freshman_spring'
                        logger.info(f"[ROADMAP] Student graduating {grad_year} = Freshman Spring (current: {current_year}-{current_month:02d})")
                        
                else:
                    # Negative years_until_grad - already graduated, default to senior spring
                    template_key = 'senior_spring'
                    logger.warning(f"[ROADMAP] Student already graduated ({grad_year}), defaulting to Senior Spring (current: {current_year}-{current_month:02d})")
            else:
                # Fallback to grade_level parameter if provided
                current_grade = data.get('grade_level', '12th Grade')
                if '11' in current_grade or 'Junior' in current_grade:
                    template_key = 'junior_spring'
                logger.info(f"[ROADMAP] No graduation_year found, using grade_level={current_grade}")
        
        # Get base template
        template = TEMPLATES.get(template_key, TEMPLATES['senior_fall']).copy()
        
        # If user_email provided, fetch real deadlines and inject
        deadline_tasks = []
        if user_email:
            deadlines = fetch_aggregated_deadlines(user_email)
            for d in deadlines:
                task = {
                    'id': f"task_deadline_{d['university_id']}",
                    'title': f"Submit {d['deadline_type']} to {d['university_name']}",
                    'due_date': d['date'],
                    'type': 'deadline',
                    'university_id': d['university_id']
                }
                deadline_tasks.append(task)
                
        # Inject deadlines into "Applications" phase if it exists
        # This is a simple injection strategy; a more robust one would date-sort
        for phase in template['phases']:
            if phase['id'] == 'phase_applications':
                # Add deadlines at the top of tasks
                phase['tasks'] = deadline_tasks + phase['tasks']
        
        return {
            'success': True,
            'roadmap': template,
            'metadata': {
                'template_used': template_key,
                'deadlines_found': len(deadline_tasks),
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
