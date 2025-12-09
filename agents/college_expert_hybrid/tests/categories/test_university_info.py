"""
General University Information Tests - Programs, requirements, acceptance rates.
"""
from ..core import EvalCase

CATEGORY = "General University Info"

TESTS = [
    EvalCase(
        eval_id="business_programs",
        category=CATEGORY,
        user_query="What universities in the knowledge base offer business undergraduate programs?",
        expected_intent="Search and return universities with business programs",
        criteria=[
            "Searches for universities with business programs",
            "Returns at least 2-3 university names",
            "Provides relevant information about business/marketing programs",
        ]
    ),
    EvalCase(
        eval_id="uc_engineering",
        category=CATEGORY,
        user_query="Tell me about engineering programs at UC schools",
        expected_intent="Provide information about UC engineering programs",
        criteria=[
            "Mentions UC Berkeley, UCLA, or other UC schools",
            "Discusses engineering programs or departments",
            "Provides specific details about programs",
        ]
    ),
    EvalCase(
        eval_id="mit_admission_requirements",
        category=CATEGORY,
        user_query="What are the admission requirements for MIT?",
        expected_intent="Attempt to answer about MIT admission or gracefully indicate MIT not in KB",
        criteria=[
            "Mentions MIT or Massachusetts Institute of Technology",
            "Either provides admission info OR states MIT not in knowledge base",
            "Response is helpful (offers alternatives if can't find data)",
        ]
    ),
    EvalCase(
        eval_id="mit_acceptance_rate",
        category=CATEGORY,
        user_query="What is the acceptance rate at MIT?",
        expected_intent="Attempt to answer about MIT acceptance rate or gracefully indicate MIT not in KB",
        criteria=[
            "Mentions MIT",
            "Either provides acceptance rate OR clearly states MIT not in knowledge base",
            "Response is helpful (not just an error message)",
        ]
    ),
    EvalCase(
        eval_id="ucla_requirements",
        category=CATEGORY,
        user_query="Tell me about UCLA's application requirements and deadlines",
        expected_intent="Describe UCLA application process",
        criteria=[
            "Mentions UCLA",
            "Discusses application requirements or deadlines",
            "Provides actionable information",
        ]
    ),
    EvalCase(
        eval_id="popular_majors",
        category=CATEGORY,
        user_query="What are the popular majors at Stanford?",
        expected_intent="List popular majors at Stanford",
        criteria=[
            "Mentions Stanford University",
            "Lists specific majors (CS, engineering, economics, etc.)",
            "Response is helpful and informative",
        ]
    ),
]
