"""
Test Categories Package - Import all test modules.
"""
from . import test_basic
from . import test_university_info
from . import test_search
from . import test_fit_analysis
from . import test_recommendations
from . import test_error_handling
from . import test_conversations

# Map of category names to test modules
CATEGORY_MAP = {
    "basic": test_basic,
    "university_info": test_university_info,
    "search": test_search,
    "fit_analysis": test_fit_analysis,
    "recommendations": test_recommendations,
    "error_handling": test_error_handling,
    "conversations": test_conversations,
}

# All single-turn tests
ALL_SINGLE_TURN_TESTS = (
    test_basic.TESTS +
    test_university_info.TESTS +
    test_search.TESTS +
    test_fit_analysis.TESTS +
    test_recommendations.TESTS +
    test_error_handling.TESTS +
    test_error_handling.COLLEGE_LIST_TESTS +
    test_error_handling.FOLLOWUP_TESTS
)

# All multi-turn conversations
ALL_CONVERSATIONS = test_conversations.TESTS
