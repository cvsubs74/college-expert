# College Expert Hybrid - Modular Evaluation Suite

## Overview

This directory contains the **LLM-as-Judge** evaluation suite for the `college_expert_hybrid` agent, organized into modular, category-specific test files.

## Directory Structure

```
tests/
├── run_tests.py          # Main CLI test runner
├── README.md             # This file
├── core/
│   ├── __init__.py       # Core infrastructure (EvalCase, judge, agent runner)
│   └── report.py         # Markdown report generator
├── categories/
│   ├── __init__.py       # Category registry
│   ├── test_basic.py     # Basic interaction tests (2 tests)
│   ├── test_university_info.py  # University info tests (6 tests)
│   ├── test_search.py    # Search & comparison tests (5 tests)
│   ├── test_fit_analysis.py  # Fit analysis tests (6 tests)
│   ├── test_recommendations.py  # Strategic recommendations (5 tests)
│   ├── test_error_handling.py   # Error handling tests (6 tests)
│   └── test_conversations.py    # Multi-turn conversations (5 convos, 21 turns)
└── reports/              # Generated markdown reports
```

## Usage

```bash
# Set API key first
export GEMINI_API_KEY=$(gcloud secrets versions access latest \
  --secret="gemini-api-key" --project=college-counselling-478115)

# Navigate to agents directory
cd agents/college_counselor/agents

# Run all tests
python college_expert_hybrid/tests/run_tests.py

# Run specific category
python college_expert_hybrid/tests/run_tests.py --category basic
python college_expert_hybrid/tests/run_tests.py --category fit_analysis
python college_expert_hybrid/tests/run_tests.py --category conversations

# List available categories
python college_expert_hybrid/tests/run_tests.py --list

# Quiet mode (less output)
python college_expert_hybrid/tests/run_tests.py --category all --quiet

# Skip report generation
python college_expert_hybrid/tests/run_tests.py --no-report
```

## Available Categories

| Category | Tests | Description |
|----------|-------|-------------|
| `basic` | 2 | Greetings, capabilities |
| `university_info` | 6 | Programs, requirements, acceptance rates |
| `search` | 5 | University search, comparisons |
| `fit_analysis` | 6 | Personalized fit analysis |
| `recommendations` | 5 | Safety schools, balanced lists |
| `error_handling` | 6 | Unknown schools, edge cases |
| `conversations` | 5 (21 turns) | Multi-turn context retention |
| `all` | 35 total | Run everything |

## Reports

After running tests, markdown reports are generated in `reports/`:
- `latest_{category}.md` - Always points to the most recent run
- `report_{category}_{timestamp}.md` - Historical reports

## Adding New Tests

1. Create a new file in `categories/` or add to an existing file
2. Define tests using `EvalCase` dataclass:
   ```python
   from ..core import EvalCase
   
   TESTS = [
       EvalCase(
           eval_id="my_test",
           category="My Category",
           user_query="What is...",
           expected_intent="Explain...",
           criteria=[
               "Mentions X",
               "Provides Y",
           ]
       ),
   ]
   ```
3. Register in `categories/__init__.py`
