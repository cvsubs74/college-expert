"""
Basic Interaction Tests - Greetings and capability questions.
"""
from ..core import EvalCase

CATEGORY = "Basic Interaction"

TESTS = [
    EvalCase(
        eval_id="basic_greeting",
        category=CATEGORY,
        user_query="Hi, I need help with college applications",
        expected_intent="Provide a helpful greeting and offer assistance",
        criteria=[
            "Acknowledges the user's request for help",
            "Mentions available capabilities (search, fit analysis, advice)",
            "Invites further interaction or asks clarifying question",
        ]
    ),
    EvalCase(
        eval_id="what_can_you_do",
        category=CATEGORY,
        user_query="What can you help me with?",
        expected_intent="Explain the agent's capabilities",
        criteria=[
            "Lists key capabilities (university search, fit analysis, recommendations)",
            "Mentions personalized advice based on student profile",
            "Response is helpful and informative",
        ]
    ),
]
