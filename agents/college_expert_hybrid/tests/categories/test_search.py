"""
Search and Comparison Tests - University search and comparison queries.
"""
from ..core import EvalCase

CATEGORY = "Search & Comparison"

TESTS = [
    EvalCase(
        eval_id="search_california_engineering",
        category=CATEGORY,
        user_query="Find top engineering universities in California",
        expected_intent="Search and return California engineering schools",
        criteria=[
            "Returns at least 3 California engineering schools",
            "Includes well-known schools (Stanford, Berkeley, Caltech, UCLA)",
            "Provides relevant university information",
        ]
    ),
    EvalCase(
        eval_id="compare_berkeley_ucla_cs",
        category=CATEGORY,
        user_query="Compare UC Berkeley and UCLA for computer science - which has better career outcomes?",
        expected_intent="Compare two universities for CS",
        criteria=[
            "Discusses both UC Berkeley and UCLA",
            "Addresses computer science programs",
            "Provides comparison points (rankings, outcomes, strengths)",
        ]
    ),
    EvalCase(
        eval_id="acceptance_rates_california",
        category=CATEGORY,
        user_query="What are the acceptance rates for all universities in California?",
        expected_intent="Provide acceptance rates for California schools",
        criteria=[
            "Lists acceptance rates for multiple CA universities",
            "Provides specific percentage numbers",
            "Response covers multiple schools",
        ]
    ),
    EvalCase(
        eval_id="highest_earnings",
        category=CATEGORY,
        user_query="Which universities have the highest median earnings for graduates?",
        expected_intent="List universities with best earning outcomes",
        criteria=[
            "Mentions universities with high graduate earnings",
            "May provide specific salary figures",
            "Response is data-driven",
        ]
    ),
    EvalCase(
        eval_id="compare_strategy_berkeley_usc",
        category=CATEGORY,
        user_query="Compare the application strategies for UC Berkeley vs USC - what does each school prioritize?",
        expected_intent="Compare application strategies",
        criteria=[
            "Discusses Berkeley's priorities",
            "Discusses USC's priorities",
            "Highlights differences in what each school values",
        ]
    ),
]
