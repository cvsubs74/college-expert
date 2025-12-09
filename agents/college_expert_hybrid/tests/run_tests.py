#!/usr/bin/env python3
"""
Test Runner for College Expert Hybrid Agent Evaluation Suite.

Usage:
    # Run all tests
    python run_tests.py
    
    # Run specific category
    python run_tests.py --category basic
    python run_tests.py --category fit_analysis
    python run_tests.py --category conversations
    
    # List available categories
    python run_tests.py --list
    
    # Generate report only (no tests)
    python run_tests.py --report-only
"""
import os
import sys
import argparse
import asyncio
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from college_expert_hybrid.tests.core import (
    EvalCase, EvalResult, MultiTurnConversation,
    run_agent, judge_response, judge_conversation_turn,
    BASE_URL, APP_NAME, DEFAULT_USER_EMAIL, set_local_mode
)
from college_expert_hybrid.tests.core.report import generate_markdown_report, print_summary
from college_expert_hybrid.tests.categories import (
    CATEGORY_MAP, ALL_SINGLE_TURN_TESTS, ALL_CONVERSATIONS
)

# Store conversation details for reports
CONVERSATION_DETAILS: List[Dict[str, Any]] = []


async def run_single_turn_tests(tests: list[EvalCase], verbose: bool = True) -> list[EvalResult]:
    """Run single-turn tests and capture full responses."""
    results = []
    
    for case in tests:
        if verbose:
            print(f"📝 [{case.category}] {case.eval_id}")
            print(f"   Query: {case.user_query[:50]}...")
        
        try:
            actual_response = await run_agent(case.user_query)
            if verbose:
                print(f"   Response: {actual_response[:60]}...")
            
            result = judge_response(case, actual_response)
            
            # Add full response and query to result
            result.full_response = actual_response
            result.query = case.user_query
            
            results.append(result)
            
            status = "✅ PASS" if result.passed else "❌ FAIL"
            if verbose:
                print(f"   {status} (Score: {result.score:.2f})")
        except Exception as e:
            if verbose:
                print(f"   ❌ ERROR: {e}")
            results.append(EvalResult(
                eval_id=case.eval_id,
                category=case.category,
                passed=False,
                score=0.0,
                reasoning=str(e),
                query=case.user_query,
                full_response=f"Error: {str(e)}"
            ))
        
        if verbose:
            print()
    
    return results


async def run_conversation_tests(conversations: list[MultiTurnConversation], verbose: bool = True) -> list[EvalResult]:
    """Run multi-turn conversation tests and capture all details."""
    import aiohttp
    
    global CONVERSATION_DETAILS
    results = []
    
    for conv in conversations:
        if verbose:
            print(f"\n🔄 [{conv.conv_id}] {conv.description}")
            print(f"   Turns: {len(conv.turns)}")
        
        session_id = f"conv_{uuid.uuid4().hex[:8]}"
        user_id = "eval_user"
        
        all_turns_passed = True
        turn_scores = []
        turn_details = []
        
        # Collect conversation details for report
        conv_detail = {
            "conv_id": conv.conv_id,
            "description": conv.description,
            "turns": [],
            "passed": False,
            "score": 0.0
        }
        
        try:
            async with aiohttp.ClientSession() as http_session:
                # Create session
                create_url = f"{BASE_URL}/apps/{APP_NAME}/users/{user_id}/sessions/{session_id}"
                async with http_session.post(
                    create_url,
                    json={"state": {"user_email": DEFAULT_USER_EMAIL}},
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    pass
                
                for i, turn in enumerate(conv.turns):
                    if verbose:
                        print(f"   Turn {i+1}: {turn.description}")
                        print(f"      User: {turn.user_message[:40]}...")
                    
                    # For first turn of profile-required conversations, prepend email context
                    message_text = turn.user_message
                    if i == 0 and conv.requires_profile:
                        message_text = f"My email is {DEFAULT_USER_EMAIL}. {turn.user_message}"
                    
                    # Send message
                    run_url = f"{BASE_URL}/run"
                    run_payload = {
                        "app_name": APP_NAME,
                        "user_id": user_id,
                        "session_id": session_id,
                        "new_message": {"role": "user", "parts": [{"text": message_text}]},
                        "streaming": False
                    }
                    
                    agent_response = ""
                    try:
                        async with http_session.post(
                            run_url,
                            json=run_payload,
                            headers={"Content-Type": "application/json"},
                            timeout=aiohttp.ClientTimeout(total=120)
                        ) as response:
                            if response.status == 200:
                                result = await response.json()
                                agent_response = extract_response(result)
                                
                                if verbose:
                                    print(f"      Agent: {agent_response[:50]}...")
                                
                                turn_result = judge_conversation_turn(turn, agent_response, i + 1)
                                turn_scores.append(turn_result.get("score", 0.0))
                                
                                # Store turn details
                                turn_detail = {
                                    "user_message": turn.user_message,
                                    "agent_response": agent_response,
                                    "description": turn.description,
                                    "passed": turn_result.get("passed", False),
                                    "score": turn_result.get("score", 0.0),
                                    "reasoning": turn_result.get("reasoning", ""),
                                    "context_maintained": turn_result.get("context_maintained", True)
                                }
                                turn_details.append(turn_detail)
                                conv_detail["turns"].append(turn_detail)
                                
                                if not turn_result.get("passed", False):
                                    all_turns_passed = False
                                    if verbose:
                                        print(f"      ❌ Turn failed")
                                else:
                                    if verbose:
                                        print(f"      ✅ Turn passed (Score: {turn_result.get('score', 0):.2f})")
                            else:
                                error_text = await response.text()
                                all_turns_passed = False
                                turn_scores.append(0.0)
                                turn_details.append({
                                    "user_message": turn.user_message,
                                    "agent_response": f"Error: {error_text[:200]}",
                                    "passed": False,
                                    "score": 0.0,
                                    "reasoning": f"API Error: {response.status}"
                                })
                    except Exception as e:
                        all_turns_passed = False
                        turn_scores.append(0.0)
                        turn_details.append({
                            "user_message": turn.user_message,
                            "agent_response": f"Exception: {str(e)}",
                            "passed": False,
                            "score": 0.0,
                            "reasoning": str(e)
                        })
                    
                    await asyncio.sleep(0.3)
        
        except Exception as e:
            if verbose:
                print(f"   ❌ Error: {e}")
            all_turns_passed = False
            turn_scores = [0.0]
        
        avg_score = sum(turn_scores) / len(turn_scores) if turn_scores else 0.0
        # Pass if average score is 60% or higher (allows some failed turns)
        conv_passed = avg_score >= 0.6
        
        conv_detail["passed"] = conv_passed
        conv_detail["score"] = avg_score
        CONVERSATION_DETAILS.append(conv_detail)
        
        if verbose:
            status = "✅ PASS" if conv_passed else "❌ FAIL"
            print(f"   {status} Overall Score: {avg_score:.2f}")
        
        results.append(EvalResult(
            eval_id=conv.conv_id,
            category="Multi-Turn Conversations",
            passed=conv_passed,
            score=avg_score,
            reasoning=f"{sum(1 for t in turn_details if t.get('passed'))}/{len(conv.turns)} turns passed",
            criteria_met={f"Turn {i+1}": t.get("passed", False) for i, t in enumerate(turn_details)}
        ))
    
    return results


def extract_response(result) -> str:
    """Extract text from agent response."""
    if isinstance(result, list):
        for event in reversed(result):
            if isinstance(event, dict) and event.get("content"):
                content = event["content"]
                if content.get("role") == "model" and content.get("parts"):
                    for part in content["parts"]:
                        if "text" in part and part["text"]:
                            return part["text"]
    if isinstance(result, dict):
        if "result" in result:
            return result["result"]
    return str(result)[:500]


async def main():
    global CONVERSATION_DETAILS
    CONVERSATION_DETAILS = []  # Reset for each run
    
    parser = argparse.ArgumentParser(description="Run LLM-as-Judge evaluation tests")
    parser.add_argument("--category", "-c", type=str, default="all",
                        help="Category to run (basic, university_info, search, fit_analysis, recommendations, error_handling, conversations, all)")
    parser.add_argument("--test", "-t", type=str, default=None,
                        help="Run specific test by ID (e.g., --test mit_acceptance_rate)")
    parser.add_argument("--list", "-l", action="store_true",
                        help="List available categories")
    parser.add_argument("--list-tests", action="store_true",
                        help="List all available test IDs")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Quiet mode (less output)")
    parser.add_argument("--no-report", action="store_true",
                        help="Skip report generation")
    parser.add_argument("--local", action="store_true",
                        help="Test against local ADK server (localhost:8000) instead of Cloud Run")
    
    args = parser.parse_args()
    
    if args.list:
        print("\nAvailable categories:")
        for cat in CATEGORY_MAP.keys():
            print(f"  • {cat}")
        print("  • all (run everything)")
        return
    
    if args.list_tests:
        print("\n📋 Available Test IDs:\n")
        print("SINGLE-TURN TESTS:")
        for test in ALL_SINGLE_TURN_TESTS:
            print(f"  • {test.eval_id} ({test.category})")
        print("\nMULTI-TURN CONVERSATIONS:")
        for conv in ALL_CONVERSATIONS:
            print(f"  • {conv.conv_id} ({len(conv.turns)} turns)")
        return
    
    # Switch to local mode if --local flag is set
    if args.local:
        base_url = set_local_mode(True)
        print(f"🏠 Using LOCAL server: {base_url}")
    else:
        from college_expert_hybrid.tests.core import CLOUD_URL
        print(f"☁️  Using CLOUD server: {CLOUD_URL}")
    
    verbose = not args.quiet
    
    # Handle specific test ID
    if args.test:
        print(f"\n🔍 Running specific test: {args.test}\n")
        
        # Check single-turn tests
        matching_test = next((t for t in ALL_SINGLE_TURN_TESTS if t.eval_id == args.test), None)
        if matching_test:
            results = await run_single_turn_tests([matching_test], verbose)
            print_summary(results)
            return
        
        # Check conversations
        matching_conv = next((c for c in ALL_CONVERSATIONS if c.conv_id == args.test), None)
        if matching_conv:
            results = await run_conversation_tests([matching_conv], verbose)
            print_summary(results)
            return
        
        print(f"❌ Test ID '{args.test}' not found. Use --list-tests to see available tests.")
        return
    
    print("\n" + "=" * 70)
    print("  LLM-AS-JUDGE EVALUATION SUITE")
    print("  Agent: college_expert_hybrid")
    print(f"  Category: {args.category}")
    print("=" * 70 + "\n")
    
    results = []
    
    if args.category == "all":
        # Run all single-turn tests
        if verbose:
            print("=" * 50)
            print("  SINGLE-TURN TESTS")
            print("=" * 50 + "\n")
        results.extend(await run_single_turn_tests(ALL_SINGLE_TURN_TESTS, verbose))
        
        # Run all conversations
        if verbose:
            print("\n" + "=" * 50)
            print("  MULTI-TURN CONVERSATION TESTS")
            print("=" * 50)
        results.extend(await run_conversation_tests(ALL_CONVERSATIONS, verbose))
    
    elif args.category == "conversations":
        results.extend(await run_conversation_tests(ALL_CONVERSATIONS, verbose))
    
    elif args.category in CATEGORY_MAP:
        module = CATEGORY_MAP[args.category]
        tests = module.TESTS
        results.extend(await run_single_turn_tests(tests, verbose))
    
    else:
        print(f"Unknown category: {args.category}")
        print("Use --list to see available categories")
        return
    
    # Print summary
    print_summary(results)
    
    # Generate report with conversation details
    if not args.no_report:
        report_path = generate_markdown_report(
            results, 
            args.category,
            conversation_details=CONVERSATION_DETAILS if CONVERSATION_DETAILS else None
        )
        print(f"\n📄 Report saved to: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
