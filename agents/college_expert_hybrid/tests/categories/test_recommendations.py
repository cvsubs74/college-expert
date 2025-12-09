"""
Strategic Recommendations Tests - Safety schools, balanced lists, improvement advice.
"""
from ..core import EvalCase

CATEGORY = "Strategic Recommendations"

TESTS = [
    EvalCase(
        eval_id="safety_schools",
        category=CATEGORY,
        user_query="Based on my profile, which universities should I consider as safety schools?",
        expected_intent="Recommend safety schools based on profile",
        criteria=[
            "Recommends specific universities as safety options",
            "Bases recommendations on student's profile",
            "Provides reasoning for safety designation",
        ],
        requires_profile=True
    ),
    EvalCase(
        eval_id="improve_for_ucsd",
        category=CATEGORY,
        user_query="What aspects of my profile would strengthen my application to UC San Diego?",
        expected_intent="Provide improvement recommendations",
        criteria=[
            "Mentions UCSD or UC San Diego",
            "Identifies specific areas for improvement",
            "Provides actionable advice",
        ],
        requires_profile=True
    ),
    EvalCase(
        eval_id="balanced_list_business",
        category=CATEGORY,
        user_query="Help me build a balanced college list for Business majors in California",
        expected_intent="Create balanced reach/target/safety list",
        criteria=[
            "Suggests universities across different categories (reach, target, safety)",
            "Focuses on business programs",
            "Covers California-based options",
        ],
        requires_profile=True
    ),
    EvalCase(
        eval_id="interdisciplinary_marketing_psychology",
        category=CATEGORY,
        user_query="I want to study Marketing and Psychology - which universities have programs that combine both?",
        expected_intent="Find interdisciplinary programs",
        criteria=[
            "Addresses both marketing and psychology",
            "Suggests relevant universities or programs",
            "Provides helpful guidance",
        ]
    ),
    EvalCase(
        eval_id="emphasize_in_application",
        category=CATEGORY,
        user_query="What should I emphasize in my MIT application?",
        expected_intent="Provide application strategy advice",
        criteria=[
            "Mentions MIT",
            "Suggests specific elements to emphasize",
            "Provides strategic advice",
        ],
        requires_profile=True
    ),
]
