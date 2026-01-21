
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
    'senior_fall': {
        'title': 'Senior Fall: Execution Mode',
        'phases': [
            {
                'id': 'phase_essays',
                'name': 'Essays & Narrative',
                'date_range': 'Aug - Oct',
                'tasks': [
                    {'id': 'task_common_app_draft', 'title': 'Draft Common App Personal Statement', 'type': 'core'},
                    {'id': 'task_uc_piq_draft', 'title': 'Draft UC PIQs (if applying to UCs)', 'type': 'core'},
                    {'id': 'task_essay_review_1', 'title': 'Get Feedback on Core Essays', 'type': 'core'}
                ]
            },
            {
                'id': 'phase_applications',
                'name': 'Applications',
                'date_range': 'Oct - Jan',
                'tasks': [
                    {'id': 'task_common_app_fill', 'title': 'Fill out Common App Profile', 'type': 'core'},
                    {'id': 'task_finalize_list', 'title': 'Finalize College List (Balanced)', 'type': 'core'},
                    {'id': 'task_supplementals', 'title': 'Write Supplemental Essays', 'type': 'core'}
                ]
            },
            {
                'id': 'phase_financials',
                'name': 'Financial Aid',
                'date_range': 'Oct - Feb',
                'tasks': [
                    {'id': 'task_fafsa', 'title': 'Submit FAFSA', 'type': 'core'},
                    {'id': 'task_css_profile', 'title': 'Submit CSS Profile (if applicable)', 'type': 'core'}
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
                    # Graduating next year - Senior or Junior
                    if is_fall:
                        template_key = 'senior_fall'
                        logger.info(f"[ROADMAP] Student graduating {grad_year} = Senior Fall (current: {current_year}-{current_month:02d})")
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

