# College Expert Hybrid - Evaluation Suite

## Overview

This directory contains the **LLM-as-Judge** evaluation suite for the `college_expert_hybrid` agent. 
Instead of exact text matching, Gemini evaluates responses semantically against criteria.

## Test Categories (30 tests)

| Category | Tests | Description |
|----------|-------|-------------|
| Basic Interaction | 2 | Greetings, capability questions |
| General University Info | 6 | Programs, requirements, acceptance rates |
| Search & Comparison | 5 | University search, comparisons |
| Personalized Analysis | 6 | Fit analysis with profile data |
| Strategic Recommendations | 5 | Safety schools, balanced lists, improvement advice |
| College List | 1 | College list management |
| Error Handling | 3 | Unknown schools, vague queries |
| Multi-Turn | 2 | Follow-up questions, context |

## Usage

```bash
# Set API key
export GEMINI_API_KEY=$(gcloud secrets versions access latest \
  --secret="gemini-api-key" --project=college-counselling-478115)

# Run all tests
cd agents/college_counselor/agents
python college_expert_hybrid/tests/test_llm_judge.py
```

## How It Works

1. **Agent Invocation**: Each test creates a session and sends a query to the deployed agent
2. **Response Extraction**: Extracts the final text response from agent events
3. **LLM Judging**: Gemini evaluates if the response meets semantic criteria
4. **Scoring**: Pass/fail with 0.0-1.0 score per test case

## Example Criteria

```python
EvalCase(
    eval_id="fit_harvard",
    criteria=[
        "Mentions Harvard University",
        "Categorizes as REACH or SUPER_REACH",
        "Mentions low acceptance rate or selectivity",
        "Provides advice for improving chances",
    ]
)
```

## Files

- `test_llm_judge.py` - Comprehensive LLM-as-judge evaluation suite
- `README.md` - This documentation
