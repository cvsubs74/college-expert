"""
Error Handling Tests - Unknown schools, vague queries, edge cases.
"""
from ..core import EvalCase

CATEGORY = "Error Handling"

TESTS = [
    EvalCase(
        eval_id="unknown_university",
        category=CATEGORY,
        user_query="Tell me about Fake University that does not exist",
        expected_intent="Handle unknown university gracefully",
        criteria=[
            "Does not make up information",
            "Indicates the university is not found or not in knowledge base",
            "Offers alternative help or suggestions",
        ]
    ),
    EvalCase(
        eval_id="stanford_not_in_kb",
        category=CATEGORY,
        user_query="Should I apply to Stanford?",
        expected_intent="Handle school that may not be in KB",
        criteria=[
            "Addresses Stanford",
            "Either provides info or explains limitations",
            "Offers helpful guidance",
        ],
        requires_profile=True
    ),
    EvalCase(
        eval_id="vague_query",
        category=CATEGORY,
        user_query="What do you think?",
        expected_intent="Handle vague/unclear query",
        criteria=[
            "Asks for clarification",
            "Offers to help with specific topics",
            "Does not produce irrelevant response",
        ]
    ),
]


# Additional tests for college list management
COLLEGE_LIST_TESTS = [
    EvalCase(
        eval_id="show_college_list",
        category="College List",
        user_query="Show me my college list",
        expected_intent="Display user's saved college list",
        criteria=[
            "Attempts to retrieve or display college list",
            "If list exists, shows universities",
            "If list is empty, offers to help build one",
        ],
        requires_profile=True
    ),
]


# Follow-up / single-turn multi-turn tests
FOLLOWUP_TESTS = [
    EvalCase(
        eval_id="research_opportunities",
        category="Multi-Turn / Follow-up",
        user_query="What research opportunities are available at MIT?",
        expected_intent="Describe research programs",
        criteria=[
            "Mentions MIT research programs (UROP, labs, etc.)",
            "Provides specific examples or programs",
            "Response is informative",
        ]
    ),
    EvalCase(
        eval_id="financial_aid",
        category="Multi-Turn / Follow-up",
        user_query="What about financial aid at MIT?",
        expected_intent="Provide financial aid information",
        criteria=[
            "Discusses MIT financial aid",
            "May mention need-blind policy",
            "Provides helpful information",
        ]
    ),
]
