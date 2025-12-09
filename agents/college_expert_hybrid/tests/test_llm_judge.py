"""
Comprehensive LLM-as-Judge Evaluation Suite for college_expert_hybrid agent.

This module implements semantic evaluation using Gemini as a judge to assess
whether the agent's responses are functionally correct. Covers all major
use cases extracted from comprehensive shell test scripts.

CATEGORIES:
1. Basic Interaction (greeting, help)
2. General University Information (programs, requirements)
3. University Search & Comparison
4. Personalized Fit Analysis (with profile)
5. Strategic Recommendations
6. Complex Multi-Faceted Queries
7. Multi-Turn Conversations
8. Error Handling & Edge Cases

Usage:
    # Run all tests
    python tests/test_llm_judge.py
    
    # Run with pytest
    pytest tests/test_llm_judge.py -v
"""
import os
import json
import asyncio
import uuid
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import google.generativeai as genai

# Configure Gemini
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# Use a strong model for judging
JUDGE_MODEL = genai.GenerativeModel("gemini-2.0-flash")


@dataclass
class EvalCase:
    """A single evaluation case."""
    eval_id: str
    category: str
    user_query: str
    expected_intent: str
    criteria: list[str]
    requires_profile: bool = False


@dataclass
class EvalResult:
    """Result of an LLM-as-judge evaluation."""
    eval_id: str
    category: str
    passed: bool
    score: float
    reasoning: str
    criteria_met: dict[str, bool] = field(default_factory=dict)


# ============================================================================
# COMPREHENSIVE EVALUATION CASES
# ============================================================================

EVAL_CASES = [
    # =========================================================================
    # CATEGORY 1: BASIC INTERACTION
    # =========================================================================
    EvalCase(
        eval_id="basic_greeting",
        category="Basic Interaction",
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
        category="Basic Interaction",
        user_query="What can you help me with?",
        expected_intent="Explain the agent's capabilities",
        criteria=[
            "Lists key capabilities (university search, fit analysis, recommendations)",
            "Mentions personalized advice based on student profile",
            "Response is helpful and informative",
        ]
    ),
    
    # =========================================================================
    # CATEGORY 2: GENERAL UNIVERSITY INFORMATION
    # =========================================================================
    EvalCase(
        eval_id="business_programs",
        category="General University Info",
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
        category="General University Info",
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
        category="General University Info",
        user_query="What are the admission requirements for MIT?",
        expected_intent="Describe MIT admission requirements",
        criteria=[
            "Mentions MIT or Massachusetts Institute of Technology",
            "Discusses admission requirements (GPA, SAT/ACT, essays, etc.)",
            "Response is factual and informative",
        ]
    ),
    EvalCase(
        eval_id="mit_acceptance_rate",
        category="General University Info",
        user_query="What is the acceptance rate at MIT?",
        expected_intent="Provide MIT's acceptance rate",
        criteria=[
            "Mentions MIT's acceptance rate (around 3-4%)",
            "Provides context about selectivity",
            "May mention application statistics",
        ]
    ),
    EvalCase(
        eval_id="ucla_requirements",
        category="General University Info",
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
        category="General University Info",
        user_query="What are the popular majors at Stanford?",
        expected_intent="List popular majors at Stanford",
        criteria=[
            "Mentions Stanford University",
            "Lists specific majors (CS, engineering, economics, etc.)",
            "Response is helpful and informative",
        ]
    ),
    
    # =========================================================================
    # CATEGORY 3: UNIVERSITY SEARCH & COMPARISON
    # =========================================================================
    EvalCase(
        eval_id="search_california_engineering",
        category="Search & Comparison",
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
        category="Search & Comparison",
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
        category="Search & Comparison",
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
        category="Search & Comparison",
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
        category="Search & Comparison",
        user_query="Compare the application strategies for UC Berkeley vs USC - what does each school prioritize?",
        expected_intent="Compare application strategies",
        criteria=[
            "Discusses Berkeley's priorities",
            "Discusses USC's priorities",
            "Highlights differences in what each school values",
        ]
    ),
    
    # =========================================================================
    # CATEGORY 4: PERSONALIZED FIT ANALYSIS
    # =========================================================================
    EvalCase(
        eval_id="fit_berkeley",
        category="Personalized Analysis",
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
        category="Personalized Analysis",
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
        category="Personalized Analysis",
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
        category="Personalized Analysis",
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
        category="Personalized Analysis",
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
        category="Personalized Analysis",
        user_query="Analyze my chances at UC Berkeley and USC",
        expected_intent="Analyze chances at multiple schools",
        criteria=[
            "Discusses both Berkeley and USC",
            "Provides fit assessment for each",
            "May compare the two schools",
        ],
        requires_profile=True
    ),
    
    # =========================================================================
    # CATEGORY 5: STRATEGIC RECOMMENDATIONS
    # =========================================================================
    EvalCase(
        eval_id="safety_schools",
        category="Strategic Recommendations",
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
        category="Strategic Recommendations",
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
        category="Strategic Recommendations",
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
        category="Strategic Recommendations",
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
        category="Strategic Recommendations",
        user_query="What should I emphasize in my MIT application?",
        expected_intent="Provide application strategy advice",
        criteria=[
            "Mentions MIT",
            "Suggests specific elements to emphasize",
            "Provides strategic advice",
        ],
        requires_profile=True
    ),
    
    # =========================================================================
    # CATEGORY 6: COLLEGE LIST MANAGEMENT
    # =========================================================================
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
    
    # =========================================================================
    # CATEGORY 7: ERROR HANDLING & EDGE CASES
    # =========================================================================
    EvalCase(
        eval_id="unknown_university",
        category="Error Handling",
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
        category="Error Handling",
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
        category="Error Handling",
        user_query="What do you think?",
        expected_intent="Handle vague/unclear query",
        criteria=[
            "Asks for clarification",
            "Offers to help with specific topics",
            "Does not produce irrelevant response",
        ]
    ),
    
    # =========================================================================
    # CATEGORY 8: MULTI-TURN CONVERSATIONS
    # =========================================================================
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


def create_judge_prompt(case: EvalCase, actual_response: str) -> str:
    """Create a prompt for the LLM judge."""
    criteria_list = "\n".join([f"  {i+1}. {c}" for i, c in enumerate(case.criteria)])
    
    return f"""You are an expert evaluator assessing an AI college counseling agent's response quality.

## Evaluation Context
- **Category**: {case.category}
- **Requires Profile**: {case.requires_profile}

## User Query
"{case.user_query}"

## Expected Intent
{case.expected_intent}

## Criteria to Evaluate
{criteria_list}

## Agent's Actual Response
{actual_response}

## Evaluation Instructions
1. Evaluate whether the agent's response meets each criterion semantically (not exact text match)
2. Consider partial credit - if a criterion is mostly met, mark it as MET
3. If the response is generally helpful and on-topic, be generous
4. A response that makes progress toward the intent should pass

## Required Output Format
Respond ONLY with this JSON (no markdown, no explanation outside JSON):
{{
    "overall_pass": true,
    "overall_score": 0.85,
    "reasoning": "Brief explanation",
    "criteria_results": {{
        "1": {{"met": true, "note": "criterion 1 note"}},
        "2": {{"met": true, "note": "criterion 2 note"}},
        "3": {{"met": false, "note": "criterion 3 note"}}
    }}
}}
"""


async def run_agent(user_query: str, user_email: str = "cvsubs@gmail.com") -> str:
    """Run the agent via HTTP API and get its response."""
    import aiohttp
    
    BASE_URL = "https://college-expert-hybrid-agent-808989169388.us-east1.run.app"
    app_name = "college_expert_hybrid"
    user_id = "eval_user"
    session_id = f"eval_{uuid.uuid4().hex[:8]}"
    
    try:
        async with aiohttp.ClientSession() as session:
            # Create session
            create_url = f"{BASE_URL}/apps/{app_name}/users/{user_id}/sessions/{session_id}"
            async with session.post(
                create_url,
                json={"state": {"user_email": user_email}},
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                pass  # Session created
            
            # Run agent
            run_url = f"{BASE_URL}/run"
            run_payload = {
                "app_name": app_name,
                "user_id": user_id,
                "session_id": session_id,
                "new_message": {"role": "user", "parts": [{"text": user_query}]},
                "streaming": False
            }
            
            async with session.post(
                run_url,
                json=run_payload,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=120)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    # Extract from list of events
                    if isinstance(result, list):
                        for event in reversed(result):
                            if isinstance(event, dict) and event.get("content"):
                                content = event["content"]
                                if content.get("role") == "model" and content.get("parts"):
                                    for part in content["parts"]:
                                        if "text" in part and part["text"]:
                                            return part["text"]
                    
                    # Extract from dict
                    if isinstance(result, dict):
                        if "result" in result:
                            return result["result"]
                        if "content" in result and result["content"]:
                            parts = result["content"].get("parts", [])
                            if parts:
                                return parts[0].get("text", str(result))
                    
                    return str(result)[:500]
                else:
                    return f"Error: {response.status} - {await response.text()}"
    except Exception as e:
        return f"Request failed: {str(e)}"


def judge_response(case: EvalCase, actual_response: str) -> EvalResult:
    """Use LLM to judge the response."""
    prompt = create_judge_prompt(case, actual_response)
    
    try:
        response = JUDGE_MODEL.generate_content(prompt)
        result_text = response.text.strip()
        
        # Extract JSON
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0]
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0]
        
        result_json = json.loads(result_text.strip())
        
        criteria_met = {}
        for i, criterion in enumerate(case.criteria):
            key = str(i + 1)
            if key in result_json.get("criteria_results", {}):
                criteria_met[criterion] = result_json["criteria_results"][key].get("met", False)
        
        return EvalResult(
            eval_id=case.eval_id,
            category=case.category,
            passed=result_json.get("overall_pass", False),
            score=result_json.get("overall_score", 0.0),
            reasoning=result_json.get("reasoning", "No reasoning"),
            criteria_met=criteria_met
        )
    except Exception as e:
        return EvalResult(
            eval_id=case.eval_id,
            category=case.category,
            passed=False,
            score=0.0,
            reasoning=f"Judge error: {e}",
            criteria_met={}
        )


async def run_all_evals():
    """Run all evaluations and print summary."""
    print("\n" + "="*80)
    print("  COMPREHENSIVE LLM-AS-JUDGE EVALUATION SUITE")
    print("  Agent: college_expert_hybrid")
    print("="*80 + "\n")
    
    results = []
    categories = {}
    
    for case in EVAL_CASES:
        print(f"📝 [{case.category}] {case.eval_id}")
        print(f"   Query: {case.user_query[:60]}...")
        
        try:
            actual_response = await run_agent(case.user_query)
            print(f"   Response: {actual_response[:80]}...")
            
            result = judge_response(case, actual_response)
            results.append(result)
            
            # Track by category
            if case.category not in categories:
                categories[case.category] = {"passed": 0, "total": 0}
            categories[case.category]["total"] += 1
            if result.passed:
                categories[case.category]["passed"] += 1
            
            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"   {status} (Score: {result.score:.2f})")
            
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            results.append(EvalResult(
                eval_id=case.eval_id,
                category=case.category,
                passed=False,
                score=0.0,
                reasoning=str(e)
            ))
        print()
    
    # Print summary
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    avg_score = sum(r.score for r in results) / total if total > 0 else 0
    
    print("\n" + "="*80)
    print("  EVALUATION SUMMARY")
    print("="*80)
    print(f"\n  Overall: {passed}/{total} tests passed ({100*passed/total:.0f}%)")
    print(f"  Average Score: {avg_score:.2f}\n")
    
    print("  By Category:")
    for cat, data in categories.items():
        pct = 100 * data["passed"] / data["total"] if data["total"] > 0 else 0
        print(f"    • {cat}: {data['passed']}/{data['total']} ({pct:.0f}%)")
    
    print("\n  Detailed Results:")
    for r in results:
        status = "✅" if r.passed else "❌"
        print(f"    {status} {r.eval_id}: {r.score:.2f}")
    
    print("\n" + "="*80)
    return results


if __name__ == "__main__":
    asyncio.run(run_all_evals())
