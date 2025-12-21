"""
ProfileBuilder - Aggregates research outputs into UniversityProfile JSON.

Updated to handle output from parallel micro-agents.
"""
from google.adk.agents import LlmAgent
from .shared_logging import (
    agent_logging_before, agent_logging_after,
    tool_logging_before, tool_logging_after
)

MODEL_NAME = "gemini-2.5-flash-lite"

profile_builder_agent = LlmAgent(
    name="ProfileBuilder",
    model=MODEL_NAME,
    description="Aggregates all research outputs into a structured UniversityProfile JSON.",
    instruction="""CRITICAL: You MUST aggregate ALL research outputs into a complete UniversityProfile.
DO NOT summarize, truncate, or omit ANY data from the sub-agent outputs.

=== INPUT DATA (from session state) ===

The research phase uses parallel micro-agents. Read ALL these state variables:

--- ADMISSIONS MICRO-AGENTS (6 outputs) ---
- current_rates → overall_acceptance_rate, is_test_optional, test_policy_details, admits_class_size, transfer_acceptance_rate
- early_admission_stats → array of early decision/action statistics
- longitudinal_trends → 5 years of historical admissions data
- waitlist_stats → waitlist statistics per year (merge into longitudinal_trends)
- gpa_profile → weighted/unweighted GPA middle 50%, averages
- testing_profile → SAT/ACT middle 50% ranges, submission rates

--- DEMOGRAPHICS MICRO-AGENTS (4 outputs) ---
- first_gen_legacy → first_gen_percentage, legacy_percentage
- geographic_breakdown → array of regions with percentages
- gender_breakdown → men/women/non_binary stats
- racial_breakdown → IPEDS racial/ethnic breakdown

--- FINANCIALS MICRO-AGENTS (3 outputs) ---
- tuition_coa → tuition_model, academic_year, in_state, out_of_state costs
- financial_aid → aid_philosophy, average_need_based_aid, average_merit_aid
- scholarships → array of scholarship objects

--- OUTCOMES MICRO-AGENTS (3 outputs) ---
- earnings → median_earnings_10yr, employment_rate_2yr
- top_employers → array of company names
- retention → freshman_retention_rate, graduation rates, grad_school_rate

--- EXISTING AGENTS (still used) ---
- strategy_output → metadata, strategic_profile
- colleges_output → academic_structure, colleges list
- majors_output → majors for each college
- application_output → application_process
- strategy_tactics_output → application_strategy
- credit_policies_output → credit_policies
- student_insights_output → student_insights

=== AGGREGATION RULES ===

1. BUILD admissions_data:
   {
     "current_status": {
       ...current_rates,
       "early_admission_stats": early_admission_stats
     },
     "longitudinal_trends": [merge longitudinal_trends with waitlist_stats by year],
     "admitted_student_profile": {
       "gpa": gpa_profile,
       "testing": testing_profile,
       "demographics": {
         ...first_gen_legacy,
         "geographic_breakdown": geographic_breakdown,
         "gender_breakdown": gender_breakdown,
         "racial_breakdown": racial_breakdown
       }
     }
   }

2. BUILD financials:
   {
     "tuition_model": tuition_coa.tuition_model,
     "cost_of_attendance_breakdown": {...from tuition_coa},
     ...financial_aid,
     "scholarships": scholarships
   }

3. BUILD outcomes:
   {
     ...earnings,
     "top_employers": top_employers,
     ...retention (grad_school_rate, loan_default_rate)
   }

4. BUILD student_retention:
   {
     "freshman_retention_rate": retention.freshman_retention_rate,
     "graduation_rate_4_year": retention.graduation_rate_4_year,
     "graduation_rate_6_year": retention.graduation_rate_6_year
   }

=== OUTPUT STRUCTURE ===
{
  "_id": "<snake_case of university_name>",
  "metadata": <from strategy_output>,
  "strategic_profile": <from strategy_output>,
  "admissions_data": <AGGREGATED as above>,
  "academic_structure": <from colleges_output WITH majors merged>,
  "application_process": <from application_output>,
  "application_strategy": <from strategy_tactics_output>,
  "financials": <AGGREGATED as above>,
  "credit_policies": <from credit_policies_output>,
  "student_insights": <from student_insights_output>,
  "outcomes": <AGGREGATED as above>,
  "student_retention": <from retention>
}

=== CRITICAL RULES ===
1. PRESERVE ALL DATA - do not truncate or summarize
2. Include ALL array items from micro-agents
3. Merge waitlist_stats into corresponding year in longitudinal_trends
4. If micro-agent data is JSON string, parse it first
5. Use null for genuinely missing data
6. Set last_updated to today's date
7. _id should be snake_case of university name
""",
    output_key="university_profile",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)
