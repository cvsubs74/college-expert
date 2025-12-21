"""
Sub-agents for University Profile Collector.
Each agent is in its own file for modularity.
"""
# Core agents
from .state_initializer import state_initializer
from .university_name_extractor import university_name_extractor

# LLM research agents (using google_search)
from .strategy_agent import strategy_agent
from .admissions_current_agent import admissions_current_agent
from .admissions_trends_agent import admissions_trends_agent
from .admitted_profile_agent import admitted_profile_agent
from .colleges_agent import colleges_agent
from .majors_agent import majors_agent
from .application_agent import application_agent
from .strategy_tactics_agent import strategy_tactics_agent
from .financials_agent import financials_agent
from .scholarships_agent import scholarships_agent
from .credit_policies_agent import credit_policies_agent
from .student_insights_agent import student_insights_agent

# API-backed LLM agents (using API tools)
from .api_admissions_agent import api_admissions_agent
from .api_financials_agent import api_financials_agent
from .api_outcomes_agent import api_outcomes_agent
from .api_demographics_agent import api_demographics_agent

# Builder agents
from .profile_builder import profile_builder_agent
from .file_saver import file_saver_agent
from .json_corrector_agent import json_corrector_agent

__all__ = [
    # Core
    'state_initializer',
    'university_name_extractor',
    # LLM Research (google_search)
    'strategy_agent',
    'admissions_current_agent',
    'admissions_trends_agent',
    'admitted_profile_agent',
    'colleges_agent',
    'majors_agent',
    'application_agent',
    'strategy_tactics_agent',
    'financials_agent',
    'scholarships_agent',
    'credit_policies_agent',
    'student_insights_agent',
    # API-backed LLM agents
    'api_admissions_agent',
    'api_financials_agent',
    'api_outcomes_agent',
    'api_demographics_agent',
    # Builders
    'profile_builder_agent',
    'file_saver_agent',
    'json_corrector_agent',
]
