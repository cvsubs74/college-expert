"""
Personalized Fit Analysis Tests - Profile-based fit analysis.
"""
from ..core import EvalCase

CATEGORY = "Personalized Analysis"

TESTS = [
    EvalCase(
        eval_id="fit_berkeley",
        category=CATEGORY,
        user_query="Analyze my fit for UC Berkeley",
        expected_intent="Provide personalized fit analysis for Berkeley",
        criteria=[
            "Mentions UC Berkeley",
            "Provides a fit category (SAFETY, TARGET, REACH, or SUPER_REACH)",
            "References the student's profile or academic information",
            "Gives actionable advice",
        ],
        requires_profile=True
    ),
    EvalCase(
        eval_id="fit_ucla",
        category=CATEGORY,
        user_query="What are my chances at UCLA?",
        expected_intent="Analyze chances at UCLA",
        criteria=[
            "Mentions UCLA",
            "Provides fit assessment or chances",
            "Uses profile data for personalization",
        ],
        requires_profile=True
    ),
    EvalCase(
        eval_id="fit_harvard",
        category=CATEGORY,
        user_query="Analyze my fit for Harvard",
        expected_intent="Provide fit analysis recognizing Harvard's selectivity",
        criteria=[
            "Mentions Harvard University",
            "Categorizes as REACH or SUPER_REACH (not TARGET or SAFETY)",
            "Mentions low acceptance rate or high selectivity",
            "Provides advice for improving chances",
        ],
        requires_profile=True
    ),
    EvalCase(
        eval_id="fit_nyu_stern",
        category=CATEGORY,
        user_query="What are my chances at NYU Stern?",
        expected_intent="Analyze chances at NYU Stern (correct ID resolution)",
        criteria=[
            "Mentions NYU or New York University",
            "References Stern School of Business",
            "Provides fit category or chances assessment",
            "Does NOT fail due to invalid university ID",
        ],
        requires_profile=True
    ),
    EvalCase(
        eval_id="fit_mit_eecs",
        category=CATEGORY,
        user_query="Based on my profile, what are my chances at MIT for EECS?",
        expected_intent="Analyze chances at MIT EECS",
        criteria=[
            "Mentions MIT",
            "Discusses EECS or computer science/engineering",
            "Uses profile data for assessment",
            "Provides fit category",
        ],
        requires_profile=True
    ),
    EvalCase(
        eval_id="multi_school_chances",
        category=CATEGORY,
        user_query="Analyze my chances at UC Berkeley and USC",
        expected_intent="Analyze chances at multiple schools",
        criteria=[
            "Discusses both Berkeley and USC",
            "Provides fit assessment for each",
            "May compare the two schools",
        ],
        requires_profile=True
    ),
]
